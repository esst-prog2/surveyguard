# SPEC: SurveyGuard, "Spot the one who didn't read" (storyline A)

GOAL:    the viewer remembers "it found the people who didn't read, and told me why", and knows where to try it.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    30 s x 30 fps = 900 frames. No music (no music source on this machine: no HeyGen sign-in, no local model), delivered silent and said so.
LOOK:    the promo page's own world (brand, so it overrides the cream-paper ban):
         ground #F7F5F0 flat paper, no texture; ink #1B1F24; muted #5B6470; rule #DAD6CC;
         answer cells blue scale #DCE6F0 #B5CAE0 #8AABCD #5E86B2 #2F5D8A;
         accent red #C0392B ONLY for the straightliner row, "suspicious", the 33.3 row; reveal flood blue #2F5D8A.
         display Source Serif 4 600, titles 96-150 px, tracking -1%; body IBM Plex Sans 400/600, 34-40 px.
         medium: printed survey sheet: cells are flat rounded rectangles (radius 6 px), no shadows, no glow, no grain.
         real product output only: the four chart screenshots from docs/img (score histogram, heatmap, drill-down, PCA map), framed with a 2 px rule border on white.
OBJECTS: the answer grid (rows = respondents, 6 columns = trust items with their names), one flat row with a red outline,
         the 1,498-row field, the three real charts, the 66.7 / 33.3 ledger with three detector markers, the wordmark.
MOTION:  enter expo.out 0.5-0.7 s; move/camera power2.inOut 0.6 s; exit power3.in 0.25 s (~45% of enter);
         rows stagger 0.09 s; words 0.08 s; titles land then hold dead still.
SHOTS:   (s = seconds)
  s1  0.0-3.6   hook. Grid (8x6, cells 118x78) on the right 55%, three rows already on screen at frame 0; rows drop in 0.09 s apart;
                at 1.4 s row 1044 lands as one colour; 1.7-2.2 s its red outline draws left to right; "straightliner" label 2.2 s.
                Left: "Each row is a respondent." (0.2 s) then "Spot the one who didn't read." (1.0 s). Hand-off: the grid shrinks.
  s2  3.6-6.6   tension. The field of 1,498 rows (24 x 63 strips) zooms out from 3x to 1x in 1.2 s, power2.inOut; ten strips carry red outlines.
                "1,498 respondents." (0.6 s) "Which ones didn't read?" (1.5 s). Hand-off: colour flood to blue.
  s3  6.6-8.6   reveal. Ground floods #2F5D8A in 0.4 s; "SurveyGuard" per-letter 0.04 s apart, 150 px paper colour; under it "finds them, and says why." 0.9 s.
  s4  8.6-12.2  proof 1 "Flat." Real heatmap wipes in left to right (clip-path, 0.6 s); text left: "Flat." + "The same answer to every item: zero variability."
  s5  12.2-15.8 proof 2 "Contradicts." Real drill-down whips in from the right with a 12 px horizontal blur; "Answers that cannot both be true, by rules you write."
  s6  15.8-19.4 proof 3 "Stands out." Real PCA map arrives blurred 10 px and sharpens; "A pattern far from everyone else, on at least three scales."
  s7  19.4-25.6 payoff. "1,498" (180 px) -> "10 suspicious" in red (1.2 s); source line "Real Hungarian ESS round 2 data · 8.4 s from upload to result".
                At 2.8 s the ledger builds: heading "One flag is a warning, not a verdict", row "1 of 3 detectors 66.7 stays in", row "2 of 3 detectors 33.3 suspicious" (red).
  s8  25.6-30.0 claim + end card. "Every flag says why." (0.2-1.8 s, blur out); wordmark "SurveyGuard" wipes in 1.9 s; "Try it in 4 steps" and
                "esst-prog2.github.io/surveyguard" at 2.3 s, held to the end (>= 2 s).
BANNED:  dark void, glow, particles, gradients, glass; three cards in a row; KPI grids; title over a dimmed screenshot; docked logo;
         every element fading and sliding up; text moving while read; invented UI or numbers; red used for anything not suspicious.
QA:      frame 0 (grid already partly filled, readable labels), 2.4 s (red outline complete), 5.5 s (field + both lines),
         8.0 s (wordmark on blue), 10.5 / 14 / 17.5 s (each real chart fully in, text readable >= 28 px),
         21 s (10 suspicious), 25 s (ledger complete), 29.5 s (end card complete, URL readable).
