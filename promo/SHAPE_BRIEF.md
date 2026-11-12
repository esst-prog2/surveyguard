# Shape brief: "One flag is a warning, not a verdict" (Impeccable `shape`, real run)

Status: draft, waiting for approval. No code. Inputs: `PRODUCT.md`, `promo/designs/promo-page-content.md` (approved office-hours design doc), `docs/index.html`.

## 1. Job and audience
- Surface mode: **Persuade** (a tool's landing page). The block is a local extension of an established surface, so it inherits the page's "Paper" world: warm paper ground, Source Serif 4 headings, IBM Plex Sans/Mono, red only for "suspicious", blue for "fine". No new visual identity, no concept round.
- Reader: the course teacher and classmates first, then ESS researchers. Their question at this point of the page: "why trust this, and why not an existing tool?"

## 2. Outcome and proof
- After reading the block, the reader can say in one sentence why SurveyGuard is different: a single warning sign never decides alone, and every flag says why.
- Proof is the product's own arithmetic, not a claim: with the bundled ESS rule files and all three detectors available, one triggered detector gives a score of 66.7 (stays in), two give 33.3 (suspicious, below 50). Derivation: `aggregate_score` in `surveyguard/scoring.py`, score = 100 × (1 − triggered weight / available weight), weights 1.0.

## 3. Selected direction
- **Placement:** the block replaces and absorbs the last paragraph of "What it is for" (the 0 to 100 score / threshold 50 / "no black box" paragraph), so nothing is said twice. It sits after the three detectors and their "See it in the app" folds, and before "See it, don't just trust it".
- **Structure:** a small serif subheading, one short paragraph, a two-row worked example, one closing paragraph.
- **Focal moment: the two-row example.** Each row is one respondent: three small markers for the three detectors (filled = triggered), then the score, then the outcome.
  - Row 1: one marker filled (neutral ink), score 66.7, outcome "stays in".
  - Row 2: two markers filled, score 33.3 in red, outcome "suspicious", in red.
  - The markers reuse the hero's language (small rounded cells) so the page reads as one system; red appears only on the suspicious row.
- **Draft copy (English, every claim checked):**
  - Heading: "One flag is a warning, not a verdict"
  - Lead: "The three results are combined into a 0 to 100 quality score. One detector alone can be wrong: some people really do agree with every item. So with the bundled ESS rules and all three detectors available, it takes two of them to mark someone suspicious (a score below 50)."
  - Closing: "Every flag names the rule or scale behind it, so the report can go straight into your methods section. The R package careless computes indices like these for you to combine; SurveyGuard turns them into one verdict, a cleaned file, and a report. No black box, no machine learning: same input, same output."

## 4. Scope and boundaries
- Only this block changes. The hero, proof strip, detector list and folds, "See it", "Who it is for", "How to try it", and the footer stay untouched; so does the world.
- Anti-goals: no comparison table against other tools, no claim about Laz.R, no new colour, no icons-in-cards, no claim that fewer detectors behave the same way.

## 5. States and ranges
- Static content; no data states. The example must stay legible from 360 px to 1,080 px; at 360 px the row may wrap the outcome under the score but must not scroll sideways.
- Reduced motion: no animation is needed here; if any, none under `prefers-reduced-motion`.

## 6. Interaction and layout
- Reading order: heading → lead → row 1 → row 2 → closing. The two rows align in columns (markers | score | outcome) so the difference is read in one glance.
- The example is real text, not an image, with an accessible description (each row readable by a screen reader as "1 of 3 detectors triggered, score 66.7, stays in").
- Light and dark themes follow the page's existing tokens.

## 7. Constraints and open decisions
- Static HTML/CSS in `docs/index.html`; no new dependency.
- Open for `generate`: the exact treatment of the markers and row (variants), within this brief.
