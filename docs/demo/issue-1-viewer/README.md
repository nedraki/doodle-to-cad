# Viewer orientation and framing — issue #1

Captured from the running app at localhost:8080 using the existing accepted
bookend run `ba02a7a12ca1`. These are browser captures of the real STL, not
new generations. `orbit.gif` uses a faster orbit speed for the short recording.

- `drawing.png`: initial orientation from the saved primary drawing view.
- `top.png` and `right.png`: canonical camera directions.
- `isometric.png`: Z-up model with the grid in the XY build plane.
- `orbit.gif`: automatic orbit with the complete part kept in frame.

The viewer now starts stationary so the drawing orientation remains visible.
Use **orbit** to rotate automatically, or drag directly. **Drawing view**
returns to the run's recorded view; **Fit** centers and frames the part.
Standard views refit when the available viewport changes. After a manual
camera adjustment, resizing preserves the user's framing; Fit restores
automatic framing. Replacing the mesh during parameter edits preserves the camera.

## Reproduce

With a local server and Playwright Chromium installed:

```sh
.venv/bin/python scripts/check_viewer.py --base-url http://127.0.0.1:8080 \
  --run-id ba02a7a12ca1 --output docs/demo/issue-1-viewer
```

Omit `--run-id` to use the latest local result, or supply another existing run.
Use `--browser /absolute/path/to/chromium` for an existing browser installation.
The script reads existing results and intercepts fixture requests in its own
browser; it does not generate CAD or modify server results.

Checks cover saved drawing directions, screen handedness, the build-grid plane,
wide/tall translated geometry at 1024×768, 1440×1000, and 1920×1080, sidebar
resizing, camera preservation on mesh replacement, and browser errors.
