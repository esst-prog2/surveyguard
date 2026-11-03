import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import run_surveyguard, selected_position
from surveyguard import visualization as viz
from surveyguard.config import load_rules
from surveyguard.io import load_input, resolve_rules
from surveyguard.reporting import flagged_respondents, scale_results
from surveyguard.scoring import score_run


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_RULES = ROOT / "config" / "scale_logic.json"
FIXTURE_CSV = ROOT / "tests" / "fixtures" / "ess_mock.csv"
APP_PATH = ROOT / "app.py"
FLAGGED_IDS = ["1026", "1027", "1032", "1005", "1021", "1022", "1023", "1024", "1033"]
SUSPICIOUS_IDS = ["1026", "1027", "1032"]


@pytest.fixture(scope="module")
def fixture_run():
    rules = load_rules(FIXTURE_RULES)
    frame = load_input(FIXTURE_CSV, rules)
    run = score_run(frame, rules)
    active = resolve_rules(rules, frame.columns).rules
    return {
        "run": run,
        "scored": run.scored,
        "rules": active,
        "analysis": viz.analysis_frame(frame, rules),
    }


def _position(scored: pd.DataFrame, idno: str) -> int:
    return int(np.flatnonzero(scored["idno"].astype(str).to_numpy() == idno)[0])


def _write_rules(tmp_path: Path, rules: dict) -> Path:
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(rules), encoding="utf-8")
    return path


# --- Data preparation ---------------------------------------------------------------------------


@pytest.mark.parametrize("id_column", ["idno", None])
def test_flagged_positions_follow_the_report_order(fixture_run, id_column):
    scored = fixture_run["scored"]
    labels = [viz.respondent_label(scored, position, id_column) for position in viz.flagged_positions(scored)]
    expected = [str(value) for value in flagged_respondents(scored, id_column)["Respondent"]]
    assert labels == expected
    if id_column:
        assert labels == FLAGGED_IDS


def test_analysis_frame_masks_missing_codes_and_out_of_range_values(tmp_path):
    rules = load_rules(_write_rules(tmp_path, {
        "scales": {"Trust": {
            "columns": ["a", "b", "c"], "valid_min": 0, "valid_max": 10, "missing_codes": [77],
            "irv_threshold": 0, "mahalanobis_threshold": 11.3,
        }},
    }))
    frame = pd.DataFrame({"a": [1, 77, 4], "b": [2, 11, 5], "c": [3, 6, -1], "other": ["x", "y", "z"]})

    analysis = viz.analysis_frame(frame, rules)

    assert analysis["a"].tolist()[0::2] == [1, 4] and np.isnan(analysis["a"].iloc[1])
    assert analysis["b"].tolist()[0::2] == [2, 5] and np.isnan(analysis["b"].iloc[1])
    assert analysis["c"].tolist()[:2] == [3, 6] and np.isnan(analysis["c"].iloc[2])
    assert analysis["other"].tolist() == ["x", "y", "z"]


# --- Score distribution -------------------------------------------------------------------------


def test_score_histogram_counts_scored_respondents_in_five_point_bins(fixture_run):
    scored = fixture_run["scored"]
    chart = viz.score_histogram(scored, 50)

    bars = chart.figure.data[0]
    assert bars.width == 5
    assert bars.x.tolist() == [2.5 + 5 * index for index in range(20)]
    scores = scored["quality_score"].dropna()
    assert sum(bars.y) == len(scores)
    for score in scores:
        bin_index = min(int(score // 5), 19)
        assert bars.y[bin_index] > 0
    assert list(bars.y).count(0) == 17  # 33.33, 66.67, and 100 only


@pytest.mark.parametrize("threshold", [50, 60])
def test_score_histogram_draws_red_dashed_threshold_line(fixture_run, threshold):
    figure = viz.score_histogram(fixture_run["scored"], threshold).figure

    [line] = figure.layout.shapes
    assert line.x0 == line.x1 == threshold
    assert line.line.dash == "dash"
    assert line.line.color == viz.CRITICAL_RED
    assert figure.layout.annotations[0].text == f"Flag threshold ({threshold})"


def test_run_result_threshold_follows_the_rules():
    rules = json.loads(FIXTURE_RULES.read_text(encoding="utf-8"))
    rules["flag_threshold"] = 60
    assert run_surveyguard("ess.csv", FIXTURE_CSV.read_bytes(), json.dumps(rules).encode()).flag_threshold == 60
    del rules["flag_threshold"]
    assert run_surveyguard("ess.csv", FIXTURE_CSV.read_bytes(), json.dumps(rules).encode()).flag_threshold == 50


def test_score_histogram_labels_every_non_empty_bar(fixture_run):
    bars = viz.score_histogram(fixture_run["scored"], 50).figure.data[0]
    figure = viz.score_histogram(fixture_run["scored"], 50).figure

    for count, text in zip(bars.y, bars.text):
        assert text == (str(count) if count else "")
    assert bars.textposition == "outside"
    assert figure.layout.yaxis.range[1] >= max(bars.y) * 1.1

    # A bar of 4 next to one of 1500 still carries its count.
    tiny = viz.score_histogram(pd.DataFrame({"quality_score": [100.0] * 1500 + [33.33] * 4}), 50).figure.data[0]
    assert tiny.text[6] == "4" and tiny.text[19] == "1500"
    assert [text for text in tiny.text if text] == ["4", "1500"]


def _ess8_like_scores() -> pd.DataFrame:
    """1614 respondents: 3 suspicious in 30-35, 165 at 66.67, 1446 at 100 (the ESS8 shape)."""
    scores = [33.33] * 3 + [66.67] * 165 + [100.0] * 1446
    return pd.DataFrame({
        "quality_score": scores,
        "suspicious": pd.array([score < 50 for score in scores], dtype="boolean"),
    })


def test_score_histogram_log_scale():
    figure = viz.score_histogram(_ess8_like_scores(), 50, log_scale=True).figure
    bars, yaxis = figure.data[0], figure.layout.yaxis

    assert yaxis.type == "log"
    assert yaxis.title.text == "Respondents (log scale)"
    # The axis starts below 1, so the bar of 3 (and even a bar of 1) reaches above the axis floor.
    assert 10 ** yaxis.range[0] < 1
    assert 10 ** yaxis.range[1] >= 1446 * 2
    assert list(yaxis.tickvals) == [1, 10, 100, 1000]
    assert list(yaxis.ticktext) == ["1", "10", "100", "1000"]
    assert bars.y[6] == 3 and bars.y[19] == 1446
    empty = [index for index in range(20) if index not in (6, 13, 19)]
    assert all(bars.y[index] is None for index in empty)
    assert all(bars.text[index] == "" for index in empty)
    assert (bars.text[6], bars.text[13], bars.text[19]) == ("3", "165", "1446")


def test_score_histogram_linear_layout_is_unchanged(fixture_run):
    scored = fixture_run["scored"]
    default = viz.score_histogram(scored, 50).figure
    linear = viz.score_histogram(scored, 50, log_scale=False).figure

    assert default.to_plotly_json() == linear.to_plotly_json()
    yaxis = linear.layout.yaxis
    assert yaxis.type is None
    assert yaxis.title.text == "Respondents"
    assert list(yaxis.range) == [0, max(linear.data[0].y) * viz.HISTOGRAM_HEADROOM]
    assert list(linear.data[0].y).count(0) == 17


@pytest.mark.parametrize("threshold, red_bins", [(50, 10), (52, 10), (60, 12)])
def test_bins_entirely_below_the_threshold_are_red(threshold, red_bins):
    bars = viz.score_histogram(_ess8_like_scores(), threshold, log_scale=True).figure.data[0]
    colors = list(bars.marker.color)
    assert colors == [viz.CRITICAL_RED] * red_bins + [viz.BAR_BLUE] * (20 - red_bins)
    if threshold == 52:
        # The 50-55 bin straddles the threshold, so it stays blue.
        assert colors[10] == viz.BAR_BLUE and colors[9] == viz.CRITICAL_RED


def test_histogram_caption_names_colours_and_counts_suspicious(fixture_run):
    caption = viz.histogram_caption(_ess8_like_scores())
    assert caption.startswith("Red bars: bins entirely below the flag threshold (suspicious scores)")
    assert caption.endswith("3 suspicious respondents (0.19%).")
    scored = fixture_run["scored"]
    suspicious = int(scored["suspicious"].fillna(False).sum())
    assert viz.histogram_caption(scored).endswith(
        f"{suspicious} suspicious respondents ({100 * suspicious / len(scored):.2f}%)."
    )
    one = pd.DataFrame({"quality_score": [10.0, 90.0], "suspicious": pd.array([True, False], dtype="boolean")})
    assert viz.histogram_caption(one).endswith("1 suspicious respondent (50.00%).")


def test_score_histogram_leaves_out_unscored_respondents():
    scored = pd.DataFrame({"quality_score": [100.0, None, 33.3, None]})
    assert viz.unscored_count(scored) == 2
    assert sum(viz.score_histogram(scored, 50).figure.data[0].y) == 2

    empty = viz.score_histogram(pd.DataFrame({"quality_score": [None, None]}), 50)
    assert empty.figure is None
    assert empty.message == "There are no quality scores to show: no respondent could be scored."


# --- PCA ----------------------------------------------------------------------------------------


def test_pca_projection_on_a_hand_calculated_example():
    values = np.array([[3.0, 1.0], [-1.0, 1.0], [1.0, 2.0], [1.0, 0.0]])  # centre (1, 1)

    projection, ratios = viz.pca_projection(values)

    # Centred rows (2,0), (-2,0), (0,1), (0,-1): PC1 is the first axis, PC2 the second.
    np.testing.assert_allclose(projection, [[2, 0], [-2, 0], [0, 1], [0, -1]], atol=1e-12)
    np.testing.assert_allclose(ratios, [0.8, 0.2])


def test_pca_projection_sign_rule_is_deterministic():
    rng = np.random.default_rng(7)
    values = rng.normal(size=(40, 4)) @ rng.normal(size=(4, 4))
    order = rng.permutation(40)

    projection, ratios = viz.pca_projection(values)
    permuted, permuted_ratios = viz.pca_projection(values[order])

    np.testing.assert_allclose(permuted, projection[order], atol=1e-9)
    np.testing.assert_allclose(permuted_ratios, ratios)
    # Projections on the components equal the centred data times the loadings, whose largest entry is positive.
    centred = values - values.mean(axis=0)
    loadings = np.linalg.lstsq(centred, projection, rcond=None)[0]
    for component in loadings.T:
        assert component[np.argmax(np.abs(component))] > 0


def test_pca_projection_needs_two_rows_and_columns():
    with pytest.raises(ValueError):
        viz.pca_projection(np.ones((5, 1)))


def _pca(fixture_run, scale, id_column="idno"):
    rules = fixture_run["rules"]
    return viz.pca_map(
        fixture_run["analysis"], fixture_run["scored"], rules.scales[scale], rules.mahalanobis_min_scales, id_column
    )


def _points(figure):
    """(trace name, customdata row, symbol, outline width) of every plotted point."""
    points = []
    for trace in figure.data[:2]:
        for index, row in enumerate(trace.customdata):
            points.append((trace.name, list(row), trace.marker.symbol[index], trace.marker.line.width[index]))
    return points


@pytest.mark.parametrize("scale", ["Trust_Institutions", "Satisfaction"])
def test_pca_map_points_are_the_detector_rows(fixture_run, scale):
    scored = fixture_run["scored"]
    figure = _pca(fixture_run, scale).figure

    positions = sorted(row[5] for _, row, _, _ in _points(figure))
    expected = np.flatnonzero(scored[f"mahalanobis_distance_{scale}"].notna().to_numpy()).tolist()
    assert positions == expected
    columns = list(fixture_run["rules"].scales[scale].columns)
    assert fixture_run["analysis"][columns].iloc[expected].notna().all().all()


@pytest.mark.parametrize("scale", ["Trust_Institutions", "Satisfaction"])
def test_pca_map_colour_marks_outliers_on_the_shown_scale(fixture_run, scale):
    scored = fixture_run["scored"]
    threshold = fixture_run["rules"].scales[scale].mahalanobis_threshold
    figure = _pca(fixture_run, scale).figure

    assert [trace.name for trace in figure.data] == [
        viz.NORMAL_TRACE, viz.OUTLIER_TRACE,  # the plotted points, hidden from the legend
        viz.NORMAL_TRACE, viz.OUTLIER_TRACE, "Mahalanobis-flagged respondent (≥ 1 scales)",
    ]
    assert figure.data[0].marker.color == viz.MUTED
    assert figure.data[1].marker.color == viz.CRITICAL_RED
    red = sorted(row[5] for name, row, _, _ in _points(figure) if name == viz.OUTLIER_TRACE)
    distances = scored[f"mahalanobis_distance_{scale}"]
    assert red == np.flatnonzero((distances > threshold).to_numpy()).tolist()
    table = scale_results(fixture_run["run"]).set_index("Scale")
    assert len(red) == table.loc[scale, "Mahalanobis flags (scale-level)"]


def test_pca_map_marker_marks_respondent_level_flags(fixture_run):
    scored = fixture_run["scored"]
    figure = _pca(fixture_run, "Trust_Institutions").figure

    triggered = scored["mahalanobis_outlier_triggered"].to_numpy(dtype=bool)
    for _, row, symbol, outline in _points(figure):
        is_flagged = bool(triggered[row[5]])
        assert (symbol, outline) == (("diamond", 2) if is_flagged else ("circle", 0))
        assert row[4] == ("yes" if is_flagged else "no")
    legend = figure.data[4]
    assert legend.marker.symbol == "diamond" and legend.marker.line.color == viz.INK


def test_pca_legend_colour_entries_are_circles(fixture_run):
    figure = _pca(fixture_run, "Trust_Institutions").figure

    # The plotted points include flagged diamonds, so they must not supply the legend icons.
    assert [trace.showlegend for trace in figure.data[:2]] == [False, False]
    legend = [trace for trace in figure.data if trace.showlegend is not False]
    assert [trace.name for trace in legend] == [
        viz.NORMAL_TRACE, viz.OUTLIER_TRACE, "Mahalanobis-flagged respondent (≥ 1 scales)",
    ]
    assert [trace.marker.symbol for trace in legend] == ["circle", "circle", "diamond"]
    assert [trace.marker.color for trace in legend[:2]] == [viz.MUTED, viz.CRITICAL_RED]
    for trace in legend:
        assert list(trace.x) == [None] and trace.hoverinfo == "skip"
    # The first red point is a flagged diamond here, which is what used to set the legend icon.
    assert figure.data[1].marker.symbol[0] == "diamond"


def test_pca_map_tooltip_and_axes(fixture_run):
    scored = fixture_run["scored"]
    figure = _pca(fixture_run, "Trust_Institutions").figure
    rows = {row[0]: row for _, row, _, _ in _points(figure)}

    row = rows["1026"]
    position = _position(scored, "1026")
    assert row[1] == pytest.approx(scored["mahalanobis_distance_Trust_Institutions"].iloc[position])
    assert row[2] == pytest.approx(11.070498)
    assert row[3:5] == ["yes", "yes"]
    template = figure.data[0].hovertemplate
    for text in ("Respondent", "Distance", "threshold", "Outlier on this scale", "Mahalanobis-flagged"):
        assert text in template
    assert figure.layout.xaxis.title.text.startswith("PC1 (") and "of variance" in figure.layout.xaxis.title.text
    assert figure.layout.yaxis.title.text.startswith("PC2 (")

    without_id = _pca(fixture_run, "Trust_Institutions", id_column=None).figure
    labels = {row[0] for _, row, _, _ in _points(without_id)}
    assert str(position + 1) in labels and "1026" not in labels


def test_pca_caption_explains_the_projection():
    assert "near the centre" in viz.PCA_CAPTION
    assert "drawn with a small offset" in viz.PCA_CAPTION
    assert "exact component values and distances are in the tooltip" in viz.PCA_CAPTION
    assert "scale-results table" in viz.PCA_CAPTION


@pytest.mark.parametrize("scale", ["Trust_Institutions", "Satisfaction"])
def test_pca_map_jitter_is_small_repeatable_and_keeps_the_exact_values(fixture_run, scale):
    rules, scored, analysis = fixture_run["rules"], fixture_run["scored"], fixture_run["analysis"]
    first, second = _pca(fixture_run, scale).figure, _pca(fixture_run, scale).figure

    for trace_a, trace_b in zip(first.data[:2], second.data[:2]):
        assert list(trace_a.x) == list(trace_b.x) and list(trace_a.y) == list(trace_b.y)
    rows = np.flatnonzero(scored[f"mahalanobis_distance_{scale}"].notna().to_numpy())
    exact, _ = viz.pca_projection(analysis[list(rules.scales[scale].columns)].to_numpy(dtype=float)[rows])
    limit = exact.std(axis=0) * viz.JITTER_SHARE
    by_position = {position: index for index, position in enumerate(rows)}
    for trace in first.data[:2]:
        for x, y, row in zip(trace.x, trace.y, trace.customdata):
            index = by_position[row[5]]
            # The tooltip carries the projection without jitter.
            assert (row[6], row[7]) == pytest.approx(tuple(exact[index]))
            assert abs(x - exact[index, 0]) <= limit[0] + 1e-12
            assert abs(y - exact[index, 1]) <= limit[1] + 1e-12
    assert "PC1 %{customdata[6]:.2f}, PC2 %{customdata[7]:.2f}" in first.data[0].hovertemplate


def test_jitter_moves_identical_points_apart():
    projection = np.repeat([[1.0, 2.0], [3.0, -1.0]], 5, axis=0)
    drawn = viz.jittered(projection)
    assert len({tuple(point) for point in drawn}) == 10
    np.testing.assert_array_equal(drawn, viz.jittered(projection))


def _assert_axes_have_room(figure):
    assert figure.layout.margin.l >= viz.MIN_MARGIN_LEFT
    assert figure.layout.margin.b >= viz.MIN_MARGIN_BOTTOM
    for axis in (figure.layout.xaxis, figure.layout.yaxis):
        assert axis.automargin is True
        assert axis.title.standoff == viz.TITLE_STANDOFF


def test_axis_labels_get_room_on_every_chart(fixture_run):
    scored = fixture_run["scored"]
    _assert_axes_have_room(viz.score_histogram(scored, 50).figure)
    _assert_axes_have_room(_pca(fixture_run, "Trust_Institutions").figure)
    heatmap = viz.straightlining_heatmap(
        fixture_run["analysis"], scored, fixture_run["rules"], _position(scored, "1023")
    ).figure
    _assert_axes_have_room(heatmap)


def test_pca_map_messages_instead_of_empty_plots(fixture_run, tmp_path):
    scale = fixture_run["rules"].scales["Trust_Institutions"]
    scored = fixture_run["scored"].copy()
    scored["mahalanobis_distance_Trust_Institutions"] = np.nan
    chart = viz.pca_map(fixture_run["analysis"], scored, scale, 1, "idno")
    assert chart.figure is None
    assert chart.message == "No PCA map for Trust_Institutions: 31 valid rows, the Mahalanobis detector needs 2."

    single = load_rules(_write_rules(tmp_path, {"scales": {"One": {
        "columns": ["trstprl"], "valid_min": 0, "valid_max": 10, "irv_threshold": 0,
        "mahalanobis_threshold": 3.8, "detectors": ["mahalanobis_outlier"],
    }}}))
    chart = viz.pca_map(fixture_run["analysis"], scored, single.scales["One"], 1, "idno")
    assert chart.message == "No PCA map for One: the scale has only one item."


def test_pca_map_with_three_scale_minimum(tmp_path):
    rng = np.random.default_rng(11)
    scales = ["A", "B", "C", "D"]
    columns = {name: [f"{name.lower()}{item}" for item in range(1, 4)] for name in scales}
    data = pd.DataFrame(
        np.clip(rng.normal(5, 1.5, size=(80, 12)), 0, 10).round(1),
        columns=[column for name in scales for column in columns[name]],
    )
    data.insert(0, "id", [f"r{index}" for index in range(80)])
    extreme, typical = [10, 0, 10], [5, 5, 5]
    # Respondent "only_a" is extreme on scale A alone; "flagged" on B, C, and D but typical on A.
    rows = {"only_a": {"A": extreme, "B": typical, "C": typical, "D": typical},
            "flagged": {"A": typical, "B": extreme, "C": extreme, "D": extreme}}
    for respondent, values in rows.items():
        data.loc[len(data)] = [respondent] + [value for name in scales for value in values[name]]
    rules = load_rules(_write_rules(tmp_path, {
        "id_column": "id",
        "mahalanobis_min_scales": 3,
        "scales": {name: {
            "columns": columns[name], "valid_min": 0, "valid_max": 10, "irv_threshold": 0,
            "mahalanobis_threshold": 16.27, "detectors": ["mahalanobis_outlier"],
        } for name in scales},
    }))
    scored = score_run(data, rules).scored
    only_a, flagged = _position(scored.rename(columns={"id": "idno"}), "only_a"), _position(
        scored.rename(columns={"id": "idno"}), "flagged"
    )
    # Both cases really occur in the scored table.
    assert scored["mahalanobis_distance_A"].iloc[only_a] > 16.27
    assert not scored["mahalanobis_outlier_triggered"].iloc[only_a]
    assert scored["mahalanobis_outlier_triggered"].iloc[flagged]
    assert scored["mahalanobis_distance_A"].iloc[flagged] <= 16.27

    figure = viz.pca_map(viz.analysis_frame(data, rules), scored, rules.scales["A"], 3, "id").figure

    points = {row[0]: (name, symbol, outline) for name, row, symbol, outline in _points(figure)}
    assert points["only_a"] == (viz.OUTLIER_TRACE, "circle", 0)
    assert points["flagged"] == (viz.NORMAL_TRACE, "diamond", 2)
    assert figure.data[4].name == "Mahalanobis-flagged respondent (≥ 3 scales)"


# --- Straightlining heatmap ---------------------------------------------------------------------


def test_heatmap_rows_and_values_of_a_two_scale_straightliner(fixture_run):
    scored, rules, analysis = fixture_run["scored"], fixture_run["rules"], fixture_run["analysis"]
    position = _position(scored, "1023")

    heatmap = viz.straightlining_heatmap(analysis, scored, rules, position).figure.data[0]

    assert list(heatmap.y) == ["Trust_Institutions", "Satisfaction"]
    z = np.asarray(heatmap.z, dtype=float)
    trust = analysis[list(rules.scales["Trust_Institutions"].columns)].iloc[position].to_numpy(dtype=float)
    satisfaction = analysis[list(rules.scales["Satisfaction"].columns)].iloc[position].to_numpy(dtype=float)
    np.testing.assert_array_equal(z[0], trust)
    np.testing.assert_array_equal(z[1, :4], satisfaction)
    assert np.isnan(z[1, 4])
    assert heatmap.text[0] == list(rules.scales["Trust_Institutions"].columns)
    assert heatmap.text[1][:4] == list(rules.scales["Satisfaction"].columns)


def _fill(heatmap, value):
    return viz._color_at(list(map(list, heatmap.colorscale)), (value - heatmap.zmin) / (heatmap.zmax - heatmap.zmin))


def test_heatmap_equal_values_share_a_colour(tmp_path):
    rules = load_rules(_write_rules(tmp_path, {"scales": {
        "Short": {"columns": ["a", "b", "c"], "valid_min": 1, "valid_max": 5, "irv_threshold": 0,
                  "detectors": ["straightlining"]},
        "Long": {"columns": ["d", "e", "f", "g"], "valid_min": 1, "valid_max": 5, "irv_threshold": 0,
                 "detectors": ["straightlining"]},
    }}))
    analysis = pd.DataFrame({"a": [3.0], "b": [3.0], "c": [3.0], "d": [1.0], "e": [2.0], "f": [3.0], "g": [5.0]})
    scored = pd.DataFrame({"flag_reasons": ["Straightlining_Short;Straightlining_Long"]})

    figure = viz.straightlining_heatmap(analysis, scored, rules, 0).figure
    heatmap = figure.data[0]

    fills = {value: _fill(heatmap, value) for value in (1, 2, 3, 4, 5)}
    assert len(set(fills.values())) == 5
    for row, values in enumerate(np.asarray(heatmap.z, dtype=float)):
        for value in values[~np.isnan(values)]:
            assert _fill(heatmap, value) == fills[value]
    assert [annotation.text for annotation in figure.layout.annotations] == ["3", "3", "3", "1", "2", "3", "5"]


def test_heatmap_colour_bar_has_a_fixed_length_and_only_present_ticks(fixture_run, tmp_path):
    scored, rules, analysis = fixture_run["scored"], fixture_run["rules"], fixture_run["analysis"]
    two_rows = viz.straightlining_heatmap(analysis, scored, rules, _position(scored, "1023")).figure
    one_row = viz.straightlining_heatmap(analysis, scored, rules, _position(scored, "1021")).figure

    assert len(one_row.data[0].y) == 1 and len(two_rows.data[0].y) == 2
    for figure in (one_row, two_rows):
        colorbar = figure.data[0].colorbar
        assert colorbar.lenmode == "pixels"
        assert colorbar.len == viz.HEATMAP_COLORBAR_PIXELS
        # The plot area (height minus the margins) is tall enough for the colour bar.
        margin = figure.layout.margin
        assert figure.layout.height - margin.t - margin.b >= colorbar.len
        values = np.asarray(figure.data[0].z, dtype=float)
        present = sorted(set(values[~np.isnan(values)].tolist()))
        assert list(colorbar.tickvals) == present
        assert list(colorbar.ticktext) == [f"{value:g}" for value in present]
    assert one_row.layout.height == viz.HEATMAP_MIN_HEIGHT

    rules_15 = load_rules(_write_rules(tmp_path, {"scales": {"Short": {
        "columns": ["a", "b", "c", "d"], "valid_min": 1, "valid_max": 5, "irv_threshold": 0,
        "detectors": ["straightlining"],
    }}}))
    analysis_15 = pd.DataFrame({"a": [1.0], "b": [2.0], "c": [2.0], "d": [5.0]})
    flagged = pd.DataFrame({"flag_reasons": ["Straightlining_Short"]})
    colorbar = viz.straightlining_heatmap(analysis_15, flagged, rules_15, 0).figure.data[0].colorbar
    assert list(colorbar.tickvals) == [1, 2, 5]


def test_heatmap_message_for_respondent_without_straightlining(fixture_run):
    scored = fixture_run["scored"]
    chart = viz.straightlining_heatmap(fixture_run["analysis"], scored, fixture_run["rules"], _position(scored, "1026"))
    assert chart.figure is None
    assert chart.message == "This respondent was not flagged for straightlining."


def test_selected_position_follows_the_displayed_rows():
    positions = [25, 26, 31, 4, 20]
    assert selected_position([], positions) is None
    assert selected_position([2], positions) == 31
    assert selected_position([1], positions[:3]) == 26
    assert selected_position([7], positions) is None


# --- Drill-down ---------------------------------------------------------------------------------


def test_contradiction_details_of_respondent_1026(fixture_run):
    scored, rules, analysis = fixture_run["scored"], fixture_run["rules"], fixture_run["analysis"]
    position = _position(scored, "1026")

    details = viz.contradiction_details(analysis, rules, scored, position)

    assert details["Rule"].tolist() == ["Contradiction: trstprt>8 vs trstplt<2"] * 2
    assert details["Column"].tolist() == ["trstprt", "trstplt"]
    assert details["Condition"].tolist() == ["trstprt > 8", "trstplt < 2"]
    assert details["Value"].tolist() == [f"{analysis[column].iloc[position]:g}" for column in ("trstprt", "trstplt")]
    assert viz.grouped_reasons(scored, position) == {
        "Straightlining": [],
        "Contradiction": ["Contradiction: trstprt>8 vs trstplt<2"],
        "Mahalanobis": ["Mahalanobis_Trust_Institutions"],
    }
    assert "background-color: #f6d6d6" in viz.highlight_contradictions(details).to_html()


def test_contradiction_conditions_are_full_expressions_for_every_operator(tmp_path):
    rules = load_rules(_write_rules(tmp_path, {
        "scales": {"Items": {
            "columns": ["a", "b", "c", "d", "e"], "valid_min": 0, "valid_max": 10, "irv_threshold": 0,
            "detectors": ["straightlining"],
        }},
        "contradictions": [{"conditions": [
            {"column": "a", "op": ">", "value": 8},
            {"column": "b", "op": ">=", "value": 7},
            {"column": "c", "op": "<", "value": 2},
            {"column": "d", "op": "<=", "value": 1.5},
            {"column": "e", "op": "==", "value": 3},
        ]}],
    }))
    analysis = pd.DataFrame({"a": [9.0], "b": [7.0], "c": [1.0], "d": [1.0], "e": [3.0]})
    scored = pd.DataFrame({"flag_reasons": [rules.contradictions[0].label]})

    details = viz.contradiction_details(analysis, rules, scored, 0)

    assert details["Condition"].tolist() == ["a > 8", "b >= 7", "c < 2", "d <= 1.5", "e == 3"]
    assert details["Value"].tolist() == ["9", "7", "1", "1", "3"]
    # st.table renders cells as Markdown, where a leading ">" becomes a block quote.
    assert not any(str(cell).startswith(">") for cell in details.to_numpy().ravel())


def test_contradiction_details_empty_without_contradictions(fixture_run):
    scored = fixture_run["scored"]
    position = _position(scored, "1005")
    details = viz.contradiction_details(fixture_run["analysis"], fixture_run["rules"], scored, position)
    assert details.empty


def test_drilldown_labels(fixture_run):
    scored = fixture_run["scored"]
    labels = [viz.drilldown_label(scored, position, "idno") for position in viz.flagged_positions(scored)]
    assert labels[:4] == [
        "1026 (score 33.33, suspicious)",
        "1027 (score 33.33, suspicious)",
        "1032 (score 33.33, suspicious)",
        "1005 (score 66.67)",
    ]
    unscored = pd.DataFrame({"quality_score": [None], "suspicious": pd.array([None], dtype="boolean")})
    assert viz.drilldown_label(unscored, 0, None) == "1 (score N/A)"


def test_drilldown_index():
    assert viz.drilldown_index([25, 26, 31], 26) == 1
    assert viz.drilldown_index([25, 26, 31], 4) == 0
    assert viz.drilldown_index([25, 26, 31], None) == 0
    assert viz.drilldown_index([], 26) is None


# --- Isolation ----------------------------------------------------------------------------------


def test_command_line_does_not_load_the_visualization(tmp_path):
    script = (
        "import runpy, sys\n"
        f"sys.argv = ['detect_anomalies.py', {str(FIXTURE_CSV)!r}, '--rules', {str(FIXTURE_RULES)!r}, "
        f"'--output', {str(tmp_path / 'scored.csv')!r}]\n"
        "try:\n"
        "    runpy.run_path('detect_anomalies.py', run_name='__main__')\n"
        "except SystemExit as exc:\n"
        "    assert not exc.code, exc.code\n"
        "loaded = sorted(name for name in sys.modules if name.split('.')[0] == 'plotly' or name == 'surveyguard.visualization')\n"
        "print('LOADED', loaded)\n"
    )
    completed = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, check=True)
    assert "Processed: 33" in completed.stdout
    assert "LOADED []" in completed.stdout


# --- App ----------------------------------------------------------------------------------------


def _run_app(rules: bytes | None = None) -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.sidebar.file_uploader[0].upload("survey.csv", FIXTURE_CSV.read_bytes(), "text/csv").run()
    rules = FIXTURE_RULES.read_bytes() if rules is None else rules
    app.sidebar.file_uploader[1].upload("rules.json", rules, "application/json").run()
    app.sidebar.button[0].click().run()
    assert not app.exception
    return app


def _drilldown(app: AppTest, suspicious_only: bool):
    return app.selectbox(key=f"drilldown_{suspicious_only}")


def _drilldown_ids(app: AppTest, suspicious_only: bool) -> list[str]:
    return [option.split(" ")[0] for option in _drilldown(app, suspicious_only).options]


def test_app_shows_visual_analytics():
    app = _run_app()

    charts = app.get("plotly_chart")
    assert len(charts) == 2  # score distribution and PCA map; the heatmap waits for a selection
    assert [tab.label for tab in app.tabs] == ["Score distribution", "Mahalanobis PCA map"]
    assert "33 scored respondents; 0 left out because they were not scored." in [c.value for c in app.caption]
    assert viz.PCA_CAPTION in [caption.value for caption in app.caption]
    assert "Select a flagged respondent in the table to see the straightlining heatmap." in [
        caption.value for caption in app.caption
    ]
    pca_scale = app.selectbox(key="pca_scale")
    assert pca_scale.options == ["Trust_Institutions", "Satisfaction"]
    assert pca_scale.value == "Trust_Institutions"

    pca_scale.set_value("Satisfaction").run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["33", "3", "87.88"]
    result = app.session_state["surveyguard_run"][1]
    assert set(result.pca_cache) == {"Trust_Institutions", "Satisfaction"}

    # New inputs drop the run, and with it the cached projections.
    app.sidebar.file_uploader[1].upload("rules.json", FIXTURE_RULES.read_bytes(), "application/json").run()
    app.sidebar.button[0].click().run()
    new_result = app.session_state["surveyguard_run"][1]
    assert new_result is not result
    # The selector was not shown while the results were dropped, so it is back on the first scale.
    assert set(new_result.pca_cache) == {"Trust_Institutions"}


def test_app_histogram_scale_radio():
    app = _run_app()

    radio = app.radio(key="histogram_scale")
    assert radio.options == ["Log", "Linear"]
    assert radio.value == "Log"
    assert '"type":"log"' in app.get("plotly_chart")[0].proto.spec.replace(" ", "")
    assert "3 suspicious respondents (9.09%)." in " ".join(caption.value for caption in app.caption)

    radio.set_value("Linear").run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["33", "3", "87.88"]
    assert '"type":"log"' not in app.get("plotly_chart")[0].proto.spec.replace(" ", "")
    assert len(app.session_state["surveyguard_run"][1].flagged) == 9


def test_app_drilldown_follows_the_flagged_table_and_switch():
    app = _run_app()

    assert _drilldown_ids(app, False) == FLAGGED_IDS == app.dataframe[1].value["Respondent"].tolist()
    assert _drilldown(app, False).options[0] == "1026 (score 33.33, suspicious)"
    assert _drilldown(app, False).options[3] == "1005 (score 66.67)"
    contradiction = app.table[0].value
    assert contradiction["Column"].tolist() == ["trstprt", "trstplt"]
    assert contradiction["Condition"].tolist() == ["trstprt > 8", "trstplt < 2"]

    result = app.session_state["surveyguard_run"][1]
    position_1023 = result.flagged_positions[FLAGGED_IDS.index("1023")]
    _drilldown(app, False).set_value(position_1023).run()
    assert "This respondent has no logical contradictions." in [caption.value for caption in app.caption]
    assert len(app.table) == 0
    assert [metric.value for metric in app.metric] == ["33", "3", "87.88"]
    assert [button.label for button in app.download_button] == [
        "Download diagnostic report",
        "Download cleaned data (CSV)",
    ]

    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert _drilldown_ids(app, True) == SUSPICIOUS_IDS == app.dataframe[1].value["Respondent"].tolist()
    assert _drilldown(app, True).value == result.flagged_positions[0]
    assert app.table[0].value["Column"].tolist() == ["trstprt", "trstplt"]

    app.toggle[0].set_value(False).run()
    assert _drilldown_ids(app, False) == FLAGGED_IDS


def test_app_drilldown_without_suspicious_respondents():
    rules = json.loads(FIXTURE_RULES.read_text(encoding="utf-8"))
    rules["flag_threshold"] = 0
    app = _run_app(json.dumps(rules).encode())

    assert _drilldown_ids(app, False) == app.dataframe[1].value["Respondent"].tolist()
    assert not any("suspicious" in option for option in _drilldown(app, False).options)
    app.toggle[0].set_value(True).run()
    assert "There is no respondent to inspect." in [info.value for info in app.main.info]
    assert len(app.selectbox) == 1  # only the PCA scale choice remains
