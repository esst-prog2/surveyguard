# Homework 9 process log

| # | Step | What the tool did | What I decided |
|---|------|-------------------|----------------|
| 1 | Rule: commit and log after each step | Claude acknowledged the rule; from now on every step ends with a row here and a commit on `hw9-promo-page` | I set the rule: after each step, commit and add a row to PROCESS.md |
| 2 | Content (office-hours) | `/office-hours` is not installed in this session, so Claude played the role directly; it wrote the English page text (what it is for, who it is for, how to try it) into `promo/CONTENT.md` from the README facts (1,498 respondents, 10 suspicious, 8.4 s vs. 397 s, ESS 1 to 11 rules, heatmap and PCA map) | I asked for content only, no code; approval of the text pending |
| 3 | Content approval | Claude recorded the approval; `promo/CONTENT.md` is now the final page text | I approved the content draft as written ("Megfelel, mehet"), including 8.4 s instead of 5 s |
| 4 | Install Impeccable from impeccable.style (simulated) | Nothing was downloaded or installed; Claude played Impeccable's role by hand for the `shape`, `generate`, and `critique` steps, following its known design rules (no generic AI look, no Inter font, no purple gradients, no glassmorphism, no nested cards, real contrast) | I asked for the install to be simulated, not run |
| 5 | Design brief (Impeccable `shape`, simulated) | Claude wrote `promo/DESIGN_BRIEF.md`: warm paper palette with red reserved for "suspicious" and blue for "fine", Source Serif 4 + IBM Plex Sans/Mono, one-column layout, a signature hero figure (answer grid with one red-outlined straightliner row), section order, responsive and dark-mode rules, anti-goals, and two planned variants (A "Paper", B "Console"); no code | Approval of the brief pending |
