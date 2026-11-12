# SurveyGuard promo page: design brief (Impeccable `shape`, simulated)

Status: draft, waiting for approval. No code yet. Content source: `promo/CONTENT.md` (approved).

## 1. Design intent

**One sentence:** a calm, precise research tool page that looks like it was made by someone who reads methods sections, not by a SaaS template.

**Feeling:** trustworthy, transparent, quietly confident. The page should feel like a well-typeset paper with one striking figure, not like a startup landing page.

**The signature idea:** the page's main visual *is* the method. The hero shows a small grid of survey answers (respondents as rows, items as cells, colour = answer value). Most rows are varied and colourful, and one row is a single flat colour, outlined in signal red with the label "straightliner". A visitor understands what SurveyGuard catches before reading a word.

## 2. Audience lens

- **Primary:** social science students and researchers. They trust clarity, citations, and numbers, and distrust hype.
- **Secondary:** a teacher grading the page and a stranger arriving from GitHub. Both should understand "what, who, how" within 10 seconds of scrolling.

## 3. Colour

Colour carries meaning, as it does in the app: red means suspicious, blue means fine. Everything else stays neutral, so red never loses its signal value.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F7F5F0` warm paper | `#14171B` | page background |
| `--surface` | `#FFFFFF` | `#1C2026` | code blocks, figure panel |
| `--ink` | `#1B1F24` | `#E8E6E1` | body text, headings |
| `--muted` | `#5B6470` | `#9AA3AE` | captions, secondary text |
| `--rule` | `#DAD6CC` | `#2C323A` | hairlines, borders |
| `--ok` | `#2F5D8A` steel blue | `#6C9BD2` | "fine" data, links |
| `--flag` | `#C0392B` signal red | `#E5675A` | suspicious only: straightliner row, outlier dots, threshold line |
| heatmap scale | 5 steps from `#DCE6F0` to `#2F5D8A` | lifted for dark | answer values in the hero grid |

Rules:
- Red is used **only** for the "suspicious" meaning, never for buttons or decoration.
- All text meets WCAG AA (4.5:1 for body text, 3:1 for large text) in both themes.
- No gradients on surfaces, no purple, no neon.

## 4. Typography

- **Headings:** *Source Serif 4* (Google Fonts), semibold, tight leading. It gives an academic feel without looking old.
- **Body and UI:** *IBM Plex Sans*, 17 to 18 px, line height 1.6, maximum 68 characters per line.
- **Code and numbers:** *IBM Plex Mono* for commands; tabular numerals for the proof strip so the figures align.
- **Scale:** about 1.25 ratio; hero headline `clamp(2.2rem, 5vw, 3.6rem)`.
- Not used: Inter, all-caps headlines, letter-spaced eyebrow labels on every section.

## 5. Layout

One column with a 1,080 px maximum width and generous vertical rhythm (96 px between sections on desktop, 56 px on mobile). There is no card grid and no nested cards; sections are separated by whitespace and a single hairline.

1. **Header:** wordmark "SurveyGuard" on the left; on the right, "How to try it" and a GitHub link. Thin and not sticky.
2. **Hero, two columns on desktop and stacked on mobile:**
   - Left: the headline, the subline, a primary button ("Try it in 3 commands", which scrolls to the section) and a secondary text link ("View on GitHub").
   - Right: the **signature answer grid** figure (about 8 rows × 6 items), with one red-outlined straightliner row and a small caption, "Each row is a respondent. Spot the one who didn't read."
3. **Proof strip:** four large figures in a row (2×2 on mobile), each with a one-line label: 1,498 / 10 (0.67%) / 8.4 s / ESS 1–11. The "8.4 s" label also shows "397 s before" with a strikethrough.
4. **What it is for:** a short problem paragraph, then the three detectors as a **numbered list** with a small inline glyph for each (a flat bar, ≠, a dot far from a cluster). The list is not three identical icon cards.
5. **See it, don't just trust it:** the four visual features as a two-column list of text, each with a small schematic thumbnail built from simple shapes (heatmap cells, scatter dots with one red diamond, histogram bars with a dashed line). These are not fake screenshots.
6. **Who it is for:** three short audience rows, each with a bold lead-in phrase and one sentence, plus the "No code needed" note.
7. **How to try it:** three numbered steps; steps 1 and 2 are code blocks with a copy button, and step 3 is text. The CLI alternative sits in a collapsible `<details>` element below.
8. **Footer:** the course credit, the GitHub link, and the privacy line "Your data stays on your machine".

## 6. Components and details

- **Buttons:** the primary button has an `--ink` background with `--bg` text and a 6 px radius; the secondary is a text link with an underline offset. Each has a visible 2 px `--ok` focus ring.
- **Code blocks:** `--surface` background, a 1 px `--rule` border, horizontal scroll inside the block only (never page-level), and a copy button that shows "Copied" for 2 s.
- **Figure:** pure HTML/CSS grid cells (no images); the figure has an accessible text description (`role="img"` with `aria-label`).
- **Motion:** only one moment. On load, the grid rows fade in one after another and the red outline draws around the straightliner (about 600 ms in total). With `prefers-reduced-motion`, everything is shown immediately.

## 7. Responsive and theme

- Breakpoints: 720 px (the hero stacks and the proof strip becomes 2×2) and 1,024 px.
- 16 px side padding at phone width; no horizontal page scroll at 360 px.
- Light and dark themes follow `prefers-color-scheme`; all colours are `:root` tokens.

## 8. Anti-goals (Impeccable "don'ts")

- No stock photos, no 3D blobs, no "AI-powered" badge (SurveyGuard deliberately uses no ML).
- No testimonials, logos, or numbers that are not real.
- No three identical feature cards in a row.
- No glassmorphism, gradient text, or emoji bullets.

## 9. Variants planned for `generate`

Both variants share the content and the colour meaning (red = suspicious) and differ in mood:

- **A. "Paper":** the brief above as written: light warm paper, serif headlines, editorial and calm. Dark mode is supported.
- **B. "Console":** dark first, an analyst-tool feel: Plex Sans headings instead of serif, the answer grid larger and full-bleed behind the hero text, the proof strip styled like a run summary ("Processed 1,498 · Suspicious 10 · 8.4 s"), denser spacing. Light mode is supported.
