# Issue #3 — parameter controls

Before and after screenshots show the same saved result at 1440 × 1000,
with the same isometric camera and original parameter values. These are
screenshots of the running app, not generated mockups. The mobile capture
uses a 390 × 844 viewport.

- `before.png`: main at `8b25dfd`.
- `after.png`: larger slider targets, visible units, numeric entry, fine-step
  buttons, range hints, and accessible per-parameter resets.
- `after-mobile.png`: the same drawer on a narrow screen.

Numeric entry and visible values use at most two decimal places. Sliders move
in 0.1 increments; numeric-field arrow keys and buttons adjust by 0.01. Counts
use whole-number increments. Reset preserves the exact original model value. Invalid or empty entries show an inline message and
block pending compilation until corrected or reset. Escape restores the last
valid value when an entry is invalid. The API also rejects invalid edits.
Explicit OpenSCAD `/* [Group] */` headers become sections; ungrouped models
retain their declaration order. Previously cached metadata is refreshed.

Verification: 50 Python tests; `scripts/check_params.py` browser checks;
`scripts/check_sidebar.py` desktop/mobile layout checks. Browser control tests
intercept compilation requests and assert their payloads; they do not benchmark
OpenSCAD or model generation.

Capture the updated UI and rerun the interaction checks against a running app:

```sh
.venv/bin/python scripts/check_params.py --output docs/demo/issue-3-parameters
```

Pass `--browser /path/to/chrome` if the installed browser differs from the
Playwright default. Restart the app and refresh the browser before local
benchmarking so both backend metadata/validation and UI changes are loaded.
