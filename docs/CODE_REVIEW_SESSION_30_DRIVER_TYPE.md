# Session 30 — Actual OEM Driver Type regression

## Root cause found in the supplied OEM PDF

The supplied API 610 datasheet represents each radio button as multiple small,
filled vector contours. The selected option contains a third, tiny closed filled
path for the black centre. The previous detector treated all `fill=True`
contours as separate selected markers, causing an apparent multi-selection and
therefore returning no deterministic driver value.

A second issue was field anchoring. `Driver Type` was being anchored to an
unrelated earlier `DRIVERS`/`MOTOR DRIVER` occurrence because the anchor logic
allowed single-word substring matches. That prevented the correct checkbox row
from being considered.

## Fix

- Treat the nested small closed contour as the selected marker.
- Do not treat the two unselected radio contours as selections.
- Match a full field label on a visual text line rather than any generic word
  substring.
- Keep AcroForm, glyph, and raster fallbacks.
- Add the supplied OEM PDF as a test-only regression fixture.

## Verified source evidence

On page 1 of the supplied PDF, the `DRIVER TYPE` row visibly has the filled
circle next to `INDUCTION MOTOR`. The parsed PDF text separately contains the
three option labels, so selection state must come from the page graphics.
