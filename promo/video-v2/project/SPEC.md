# SPEC: "The night before the deadline" (idea 1, picked by the user)

GOAL:    a viewer who never heard of SurveyGuard sees a person use it: careless answers found, the reason shown, a cleaned file out. They know where to try it.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps, silent (no music source on this machine; the film must work without sound anyway).
TIME:    30 s = 900 frames.
LOOK:    two worlds. ROOM: night study, wall #26324A, window with moon, wood desk #6E5440, lamp pool of warm light (#F6D9A0 at 35%), laptop (bezel #1B1F24, body #C9CDD3); the student seen over the shoulder (hair #2B1E1A, skin #D9A27E, sweater #2F5D8A).
         APP: the real SurveyGuard Streamlit screens (captured from the running app on the synthetic sample tests/fixtures/ess2_mock.csv, config/ess2.json), shown at 0.8x to 1.6x, never redrawn.
         Captions: paper band #F7F5F0 at the bottom of app shots, Source Serif 4 600 at 54 px, ink #1B1F24; in the room, captions sit on the wall in paper colour. Red #C0392B only where the app itself shows it.
OBJECTS: the student (back view: head with bun, shoulders, two arms, a hand on the touchpad), laptop, desk lamp, desk clock "23:40" then "23:44", window, a spreadsheet of numbers on the laptop; a large drawn cursor (64 px) inside the app.
MOTION:  enter expo.out 0.5 s; camera power2.inOut 0.7 s; zoom through the laptop power3.in 0.9 s; exits power3.in 0.2 s; character parts offset 0.08-0.15 s, never in unison.
SHOTS:
  1 room-open   0.0-6.4   frame 0: room, laptop sheet scrolling, "Thesis chapter due tomorrow." (0.2-2.6); "284 answers. Did everyone read?" (2.8-5.0);
                          2.9 s left hand goes to her head; 4.4 s laptop switches to SurveyGuard; 5.4-6.4 camera zooms through the laptop screen.
  2 app-run     6.4-13.0  real s1 -> cursor to Upload, click -> s2 (file + config/ess2.json) -> cursor to Run SurveyGuard, click -> s3 "Analysis complete!";
                          punch-in on "Suspicious respondents 8". Captions "She uploads her file and clicks Run." / "8 of 284 flagged as suspicious."
  3 app-why     13.0-21.4 s3b: click respondent 5020 -> straightlining heatmap appears (ten answers of 1) -> s4 drill-down, the contradiction rows.
                          Captions "Respondent 5020 gave the same answer ten times." / "And two answers that contradict each other."
  4 app-done    21.4-24.6 s4: click "Download cleaned data (CSV)"; "removed 8 suspicious respondents, kept 276". Caption "8 removed, 276 kept. Report included."
  5 room-close  24.6-27.0 zoom out of the laptop to the room; she leans back and stretches; clock 23:44. Caption "Ready for the methods section."
  6 endcard     27.0-30.0 SurveyGuard wordmark wipes in, "Try it in 4 steps", esst-prog2.github.io/surveyguard.
  Disclosure, on every app shot: "Real SurveyGuard screens, synthetic sample".
BANNED:  invented UI (every app pixel is a capture), invented numbers, glow, particles, a dark void with floating UI, three cards, docked logo,
         every element fading up, text moving while read, red outside the app's own red.
QA:      0 s (room readable), 3.5 s (hand at head), 6.3 s (screen fills frame), 8 s (upload done), 10.5 s (8 suspicious), 15 s (heatmap), 19 s (contradiction rows),
         23 s (removed 8 kept 276), 26 s (stretch), 29.5 s (end card).
