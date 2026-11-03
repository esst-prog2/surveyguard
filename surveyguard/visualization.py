"""Figures and tables for the web interface's visual analytics.

Only the Streamlit app imports this module; the command-line tool never loads it or Plotly.
Every function works on a finished run and never changes scores, flags, or reasons.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .config import RulesConfig, ScaleConfig
from .io import resolve_rules
from .scoring import _normalise_questions


# Reference palette of the dataviz skill (light surface).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_ON_DARK = "#ffffff"
MUTED = "#898781"
BAR_BLUE = "#2a78d6"
CRITICAL_RED = "#d03b3b"
GRID = "#e6e5e1"
# One-hue blue ramp, steps 150 to 650, light to dark.
BLUE_RAMP = (
    "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
    "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281",
)

HISTOGRAM_BIN_WIDTH = 5
HISTOGRAM_HEADROOM = 1.15
# Log axis: starts below 1 so a single respondent is a visible bar; x3 leaves room for the label.
HISTOGRAM_LOG_FLOOR = 0.5
HISTOGRAM_LOG_HEADROOM = 3
HEATMAP_COLORBAR_PIXELS = 150
HEATMAP_MIN_HEIGHT = 300
# Axis numbers and titles must never be clipped: automargin plus at least this much room.
MIN_MARGIN_LEFT = 60
MIN_MARGIN_BOTTOM = 50
TITLE_STANDOFF = 12
OUTLIER_TRACE = "Outlier on this scale"
NORMAL_TRACE = "Not an outlier on this scale"
# Drawn points move at most this share of the axis' standard deviation; the seed makes it repeatable.
JITTER_SHARE = 0.02
JITTER_SEED = 0
PCA_CAPTION = (
    "The map shows the two directions in which the answers vary most. The Mahalanobis distance also "
    "measures directions of small variance, so an outlier on this scale can lie near the centre of the "
    "map. Because many respondents give identical answers, the points are drawn with a small offset; "
    "the exact component values and distances are in the tooltip, and the counts in the scale-results table."
)

STRAIGHTLINING_PREFIX = "Straightlining_"
CONTRADICTION_PREFIX = "Contradiction:"
MAHALANOBIS_PREFIX = "Mahalanobis_"


@dataclass(frozen=True)
class Chart:
    """A figure, or the message that explains why no figure is shown."""

    figure: go.Figure | None = None
    message: str | None = None


def flagged_legend_name(min_scales: int) -> str:
    return f"Mahalanobis-flagged respondent (≥ {min_scales} scales)"


def analysis_frame(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    """The validated values the detectors use: missing codes and out-of-range answers become NaN."""
    active = resolve_rules(rules, frame.columns).rules
    return _normalise_questions(frame, active).reset_index(drop=True)


def flagged_positions(scored: pd.DataFrame) -> list[int]:
    """Row positions of the flagged respondents, in the order of `reporting.flagged_respondents`."""
    flagged = scored.reset_index(drop=True)
    flagged = flagged.loc[flagged["suspicious"].fillna(False) | flagged["flag_reasons"].fillna("").ne("")]
    order = pd.DataFrame({
        "score": pd.to_numeric(flagged["quality_score"], errors="coerce"),
        "order": range(len(flagged)),
    }, index=flagged.index)
    order = order.sort_values(["score", "order"], ascending=[True, True], na_position="last", kind="stable")
    return [int(position) for position in order.index]


def respondent_label(scored: pd.DataFrame, position: int, id_column: str | None) -> str:
    """The identifier shown for a respondent: the id column value, or the 1-based row number."""
    if id_column and id_column in scored.columns:
        return str(scored[id_column].iloc[position])
    return str(position + 1)


def _reasons(scored: pd.DataFrame, position: int) -> list[str]:
    value = scored["flag_reasons"].iloc[position]
    if not isinstance(value, str) or not value:
        return []
    return value.split(";")


# --- Score distribution -------------------------------------------------------------------------


def unscored_count(scored: pd.DataFrame) -> int:
    return int(pd.to_numeric(scored["quality_score"], errors="coerce").isna().sum())


def histogram_bar_colors(edges: np.ndarray, flag_threshold: float) -> list[str]:
    """Red for bins that lie entirely below the flag threshold (every score in them is suspicious)."""
    return [CRITICAL_RED if upper <= flag_threshold else BAR_BLUE for upper in edges[1:]]


def histogram_caption(scored: pd.DataFrame) -> str:
    """Names the two bar colours and gives the suspicious count and share of the processed respondents."""
    suspicious = int(scored["suspicious"].fillna(False).sum())
    share = 100 * suspicious / len(scored) if len(scored) else 0.0
    noun = "respondent" if suspicious == 1 else "respondents"
    return (
        "Red bars: bins entirely below the flag threshold (suspicious scores); blue bars: the other bins. "
        f"{suspicious} suspicious {noun} ({share:.2f}%)."
    )


def _log_ticks(upper: float) -> tuple[list[int], list[str]]:
    """Powers of ten up to the axis top, written as plain integers (1, 10, 100, 1000)."""
    values = [10 ** power for power in range(int(np.floor(np.log10(upper))) + 1)]
    return values, [str(value) for value in values]


def score_histogram(scored: pd.DataFrame, flag_threshold: float, log_scale: bool = False) -> Chart:
    """Histogram of the quality scores with fixed 5-point bins and a dashed line at the flag threshold.

    On the log scale the axis starts below 1, so a bin of a single respondent is still a visible bar,
    and empty bins get no bar.
    """
    scores = pd.to_numeric(scored["quality_score"], errors="coerce").dropna().to_numpy(dtype=float)
    if scores.size == 0:
        return Chart(message="There are no quality scores to show: no respondent could be scored.")
    edges = np.arange(0, 100 + HISTOGRAM_BIN_WIDTH, HISTOGRAM_BIN_WIDTH, dtype=float)
    # numpy closes the last bin, so a score of 100 falls in 95-100.
    counts, _ = np.histogram(scores, bins=edges)
    heights = [int(count) if count or not log_scale else None for count in counts]
    figure = go.Figure(go.Bar(
        x=edges[:-1] + HISTOGRAM_BIN_WIDTH / 2,
        y=heights,
        width=HISTOGRAM_BIN_WIDTH,
        customdata=np.column_stack([edges[:-1], edges[1:]]),
        marker={"color": histogram_bar_colors(edges, flag_threshold), "line": {"color": SURFACE, "width": 2}},
        # A count above every non-empty bar keeps a bar of 4 visible next to one of 1500.
        text=[str(count) if count else "" for count in counts],
        textposition="outside",
        cliponaxis=False,
        textfont={"color": INK},
        hovertemplate="Score %{customdata[0]:g}–%{customdata[1]:g}<br>%{y} respondents<extra></extra>",
        name="Respondents",
    ))
    figure.add_vline(
        x=flag_threshold,
        line={"color": CRITICAL_RED, "dash": "dash", "width": 2},
        annotation={"text": f"Flag threshold ({flag_threshold:g})", "font": {"color": INK}},
        annotation_position="top",
    )
    tallest = max(1, int(counts.max()))
    if log_scale:
        top = tallest * HISTOGRAM_LOG_HEADROOM
        tick_values, tick_text = _log_ticks(top)
        yaxis = {
            "title": "Respondents (log scale)",
            "type": "log",
            "range": [np.log10(HISTOGRAM_LOG_FLOOR), np.log10(top)],
            "tickmode": "array",
            "tickvals": tick_values,
            "ticktext": tick_text,
        }
    else:
        # Headroom above the tallest bar for its count label.
        yaxis = {"title": "Respondents", "range": [0, tallest * HISTOGRAM_HEADROOM]}
    figure.update_layout(
        barcornerradius=4,
        showlegend=False,
        xaxis={"title": "Quality score", "range": [0, 100], "dtick": 10},
        yaxis=yaxis,
        **_layout(),
    )
    return figure_chart(figure)


# --- Mahalanobis PCA map ------------------------------------------------------------------------


def mahalanobis_scales(rules: RulesConfig) -> list[str]:
    return [name for name, scale in rules.scales.items() if scale.runs_mahalanobis]


def pca_projection(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """First two principal components of the centred rows, and their share of the variance.

    Each component's sign is chosen so that its largest absolute loading is positive, so the
    picture does not depend on the sign the SVD routine happens to return.
    """
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] < 2:
        raise ValueError("PCA needs at least two rows and two columns")
    centred = matrix - matrix.mean(axis=0)
    u, singular, vt = np.linalg.svd(centred, full_matrices=False)
    for component in range(vt.shape[0]):
        if vt[component, np.argmax(np.abs(vt[component]))] < 0:
            vt[component] *= -1
            u[:, component] *= -1
    variance = singular ** 2
    total = variance.sum()
    ratios = variance[:2] / total if total > 0 else np.zeros(2)
    return u[:, :2] * singular[:2], ratios


def jittered(projection: np.ndarray) -> np.ndarray:
    """Drawn coordinates: the projection plus a small, repeatable offset so identical answers do not stack.

    Each point moves at most JITTER_SHARE of the axis' standard deviation; the projection itself,
    the distances, and the flags are not changed.
    """
    spread = projection.std(axis=0)
    offsets = np.random.default_rng(JITTER_SEED).uniform(-1.0, 1.0, size=projection.shape)
    return projection + offsets * spread * JITTER_SHARE


def pca_map(
    analysis: pd.DataFrame,
    scored: pd.DataFrame,
    scale: ScaleConfig,
    min_scales: int,
    id_column: str | None,
) -> Chart:
    """Scatter of the first two principal components of one Mahalanobis scale's items."""
    if len(scale.columns) < 2:
        return Chart(message=f"No PCA map for {scale.name}: the scale has only one item.")
    distances = pd.to_numeric(scored[f"mahalanobis_distance_{scale.name}"], errors="coerce").to_numpy(dtype=float)
    rows = np.flatnonzero(~np.isnan(distances))
    if rows.size < 2:
        valid = int(analysis[list(scale.columns)].notna().all(axis=1).sum())
        return Chart(message=(
            f"No PCA map for {scale.name}: {valid} valid rows, "
            f"the Mahalanobis detector needs {scale.mahalanobis_min_rows}."
        ))
    projection, ratios = pca_projection(analysis[list(scale.columns)].to_numpy(dtype=float)[rows])
    threshold = float(scale.mahalanobis_threshold)
    outlier = distances[rows] > threshold
    flagged = scored["mahalanobis_outlier_triggered"].fillna(False).to_numpy(dtype=bool)[rows]
    # Built column-wise: a per-row pandas lookup costs more than the whole SVD on ESS-sized data.
    if id_column and id_column in scored.columns:
        labels = scored[id_column].astype(str).to_numpy()[rows]
    else:
        labels = (rows + 1).astype(str)
    yes_no = np.array(["no", "yes"], dtype=object)
    customdata = np.empty((rows.size, 8), dtype=object)
    customdata[:, 0] = labels
    customdata[:, 1] = distances[rows]
    customdata[:, 2] = threshold
    customdata[:, 3] = yes_no[outlier.astype(int)]
    customdata[:, 4] = yes_no[flagged.astype(int)]
    customdata[:, 5] = rows
    customdata[:, 6] = projection[:, 0]
    customdata[:, 7] = projection[:, 1]
    drawn = jittered(projection)
    hovertemplate = (
        "Respondent %{customdata[0]}<br>"
        "PC1 %{customdata[6]:.2f}, PC2 %{customdata[7]:.2f}<br>"
        "Distance %{customdata[1]:.2f} (threshold %{customdata[2]:.2f})<br>"
        "Outlier on this scale: %{customdata[3]}<br>"
        "Mahalanobis-flagged: %{customdata[4]}<extra></extra>"
    )
    figure = go.Figure()
    for name, color, mask in ((NORMAL_TRACE, MUTED, ~outlier), (OUTLIER_TRACE, CRITICAL_RED, outlier)):
        figure.add_trace(go.Scattergl(
            x=drawn[mask, 0],
            y=drawn[mask, 1],
            mode="markers",
            name=name,
            # Plotly would draw the legend icon in the first point's shape (a diamond if that
            # respondent is flagged), so the colour entries come from the legend-only traces below.
            showlegend=False,
            customdata=customdata[mask],
            hovertemplate=hovertemplate,
            marker={
                "color": color,
                "size": 9,
                "opacity": 0.85,
                "symbol": np.where(flagged[mask], "diamond", "circle").tolist(),
                "line": {"color": INK, "width": np.where(flagged[mask], 2, 0).tolist()},
            },
        ))
    for name, color in ((NORMAL_TRACE, MUTED), (OUTLIER_TRACE, CRITICAL_RED)):
        figure.add_trace(go.Scattergl(
            x=[None],
            y=[None],
            mode="markers",
            name=name,
            marker={"color": color, "size": 9, "symbol": "circle"},
            hoverinfo="skip",
        ))
    figure.add_trace(go.Scattergl(
        x=[None],
        y=[None],
        mode="markers",
        name=flagged_legend_name(min_scales),
        marker={"color": "rgba(0,0,0,0)", "size": 9, "symbol": "diamond", "line": {"color": INK, "width": 2}},
        hoverinfo="skip",
    ))
    figure.update_layout(
        xaxis={"title": f"PC1 ({ratios[0]:.1%} of variance)", "zeroline": False},
        yaxis={"title": f"PC2 ({ratios[1]:.1%} of variance)", "zeroline": False},
        legend={"orientation": "h", "x": 0, "y": 1.02, "yanchor": "bottom"},
        **_layout(),
    )
    return figure_chart(figure)


# --- Straightlining heatmap ---------------------------------------------------------------------


def straightlining_scales(rules: RulesConfig, scored: pd.DataFrame, position: int) -> list[str]:
    reasons = set(_reasons(scored, position))
    return [name for name in rules.scales if f"{STRAIGHTLINING_PREFIX}{name}" in reasons]


def _ramp(count: int) -> list[str]:
    if count == 1:
        return [BLUE_RAMP[5]]
    return [BLUE_RAMP[round(index * (len(BLUE_RAMP) - 1) / (count - 1))] for index in range(count)]


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _text_ink(fill: str) -> str:
    """The ink, black or white, with the higher contrast on the fill."""
    fill_l = _luminance(fill)
    on_black = (fill_l + 0.05) / (_luminance(INK) + 0.05)
    on_white = (1.05) / (fill_l + 0.05)
    return INK if on_black >= on_white else INK_ON_DARK


def straightlining_heatmap(
    analysis: pd.DataFrame,
    scored: pd.DataFrame,
    rules: RulesConfig,
    position: int,
) -> Chart:
    """One row per scale the respondent straightlined, one cell per item; equal values share a colour."""
    names = straightlining_scales(rules, scored, position)
    if not names:
        return Chart(message="This respondent was not flagged for straightlining.")
    scales = [rules.scales[name] for name in names]
    width = max(len(scale.columns) for scale in scales)
    z = np.full((len(scales), width), np.nan)
    columns = [["" for _ in range(width)] for _ in scales]
    for row, scale in enumerate(scales):
        values = analysis[list(scale.columns)].iloc[position].to_numpy(dtype=float)
        z[row, :len(values)] = values
        columns[row][:len(values)] = list(scale.columns)
    present = sorted({float(value) for value in z[~np.isnan(z)]})
    low = int(np.floor(min(scale.valid_min for scale in scales)))
    high = int(np.ceil(max(scale.valid_max for scale in scales)))
    count = high - low + 1
    if count <= len(BLUE_RAMP):
        # A stepped scale: each whole answer value gets its own band, so equal values share a colour.
        colors = _ramp(count)
        colorscale = []
        for index, color in enumerate(colors):
            colorscale += [[index / count, color], [(index + 1) / count, color]]
        zmin, zmax = low - 0.5, high + 0.5
    else:
        colorscale = [[index / (len(BLUE_RAMP) - 1), color] for index, color in enumerate(BLUE_RAMP)]
        zmin, zmax = float(low), float(high)
    figure = go.Figure(go.Heatmap(
        z=z,
        x=[f"Item {index + 1}" for index in range(width)],
        y=names,
        text=columns,
        zmin=zmin,
        zmax=zmax,
        colorscale=colorscale,
        xgap=2,
        ygap=2,
        hovertemplate="%{y}<br>%{text}: %{z:g}<extra></extra>",
        # A fixed pixel length, independent of the number of rows, and ticks only at the answers
        # that occur, so the labels of a one- or two-row heatmap do not overlap.
        colorbar={
            "title": "Answer",
            "lenmode": "pixels",
            "len": HEATMAP_COLORBAR_PIXELS,
            "tickmode": "array",
            "tickvals": present,
            "ticktext": [f"{value:g}" for value in present],
        },
    ))
    for row in range(len(scales)):
        for column in range(width):
            value = z[row, column]
            if np.isnan(value):
                continue
            band = min(max((value - zmin) / (zmax - zmin), 0.0), 1.0)
            fill = _color_at(colorscale, band)
            figure.add_annotation(
                x=f"Item {column + 1}",
                y=names[row],
                text=f"{value:g}",
                showarrow=False,
                font={"color": _text_ink(fill)},
            )
    figure.update_layout(
        yaxis={"autorange": "reversed", "title": None},
        xaxis={"title": None, "side": "top"},
        # Tall enough for the fixed-length colour bar even with a single row.
        height=max(HEATMAP_MIN_HEIGHT, 120 + 60 * len(scales)),
        **_layout(),
    )
    return figure_chart(figure)


def _color_at(colorscale: list[list], fraction: float) -> str:
    """The colour a stepped or linear colour scale gives at a fraction (nearest stop at or below it)."""
    chosen = colorscale[0][1]
    for stop, color in colorscale:
        if stop <= fraction:
            chosen = color
    return chosen


# --- Drill-down ---------------------------------------------------------------------------------


def drilldown_label(scored: pd.DataFrame, position: int, id_column: str | None) -> str:
    score = pd.to_numeric(scored["quality_score"], errors="coerce").iloc[position]
    score_text = "N/A" if pd.isna(score) else f"{score:.2f}"
    suspicious = bool(scored["suspicious"].fillna(False).iloc[position])
    mark = ", suspicious" if suspicious else ""
    return f"{respondent_label(scored, position, id_column)} (score {score_text}{mark})"


def drilldown_index(options: list[int], chosen: int | None) -> int | None:
    """Index of the chosen respondent among the options; the first one when it is no longer offered."""
    if not options:
        return None
    if chosen in options:
        return options.index(chosen)
    return 0


def grouped_reasons(scored: pd.DataFrame, position: int) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"Straightlining": [], "Contradiction": [], "Mahalanobis": []}
    for reason in _reasons(scored, position):
        if reason.startswith(STRAIGHTLINING_PREFIX):
            groups["Straightlining"].append(reason)
        elif reason.startswith(CONTRADICTION_PREFIX):
            groups["Contradiction"].append(reason)
        elif reason.startswith(MAHALANOBIS_PREFIX):
            groups["Mahalanobis"].append(reason)
    return groups


def contradiction_details(
    analysis: pd.DataFrame,
    rules: RulesConfig,
    scored: pd.DataFrame,
    position: int,
) -> pd.DataFrame:
    """One row per condition of every contradiction rule the respondent triggered."""
    triggered = set(grouped_reasons(scored, position)["Contradiction"])
    rows = []
    for rule in rules.contradictions:
        if rule.label not in triggered:
            continue
        for condition in rule.conditions:
            value = analysis[condition.column].iloc[position]
            rows.append({
                "Rule": rule.label,
                "Column": condition.column,
                "Value": f"{value:g}",
                # The whole expression: a cell starting with ">" would render as a Markdown quote in st.table.
                "Condition": f"{condition.column} {condition.op} {condition.value:g}",
            })
    return pd.DataFrame(rows, columns=["Rule", "Column", "Value", "Condition"])


def highlight_contradictions(details: pd.DataFrame):
    """The contradiction table with every row highlighted in a light critical red."""
    return details.style.set_properties(**{"background-color": "#f6d6d6", "color": INK}).hide(axis="index")


# --- Shared -------------------------------------------------------------------------------------


def _layout() -> dict:
    return {
        "plot_bgcolor": SURFACE,
        "paper_bgcolor": SURFACE,
        "font": {"color": INK},
        # automargin (set in figure_chart) grows these when the tick labels need more room.
        "margin": {"l": MIN_MARGIN_LEFT, "r": 20, "t": 50, "b": MIN_MARGIN_BOTTOM},
    }


def figure_chart(figure: go.Figure) -> Chart:
    axis_style = {
        "gridcolor": GRID,
        "linecolor": MUTED,
        "automargin": True,
        "title_standoff": TITLE_STANDOFF,
    }
    figure.update_xaxes(**axis_style)
    figure.update_yaxes(**axis_style)
    return Chart(figure=figure)
