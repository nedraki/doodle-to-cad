# Task 13 — Keep an edited part and recover it after reload

Issue #30. Branch `codex/brep-13-revisions`, based on `efb21a8` (PR #51). Target `brep-integration`; main stays unchanged.

## User example

Generate a tray with 2 mm walls. Preview 3 mm walls, then keep that version. Change its height and keep the second edit. Reload: the second edit, its parameter values and its downloads return together. Discard a later preview: the last kept version returns. A failed edit must not replace any valid version.

## Proposed implementation

1. Add one shared revision store per result. A revision contains its ID, parent ID, recipe/source, parameters, build checks and files. The original result is the root. Old results acquire the store lazily and keep their original files. Keep preview creation separate from selection.
2. Add explicit preview and keep endpoints. Preview takes the displayed revision ID and parameter changes. It builds from that revision, saves a candidate and does not change the selected version. Keep requires the selection version last read by the client. Reject a conflicting selection with HTTP 409. Use an atomic file replacement and a per-result filesystem lock for updates.
3. Get-result and latest-result return the selected saved version, with matching files and checks. Get-parameters accepts an explicit displayed revision. Preserve original generation evidence separately; an edit has drawing status unverified until checked again.
4. Add Keep and Discard controls for BRep edits. Each next preview starts from the displayed candidate. Discard restores the selected version. Existing browser request and mesh guards must reject delayed responses. Clear or disable candidate controls during a pending build.
5. Reuse the revision data contract for future targeted repair (#16/#32). Do not implement the repair workflow here. Keep the existing OpenSCAD parameter endpoint compatible and test it.

## Required checks

- Two edits inherit from the currently displayed revision; keep and reload match recipe, parameters, mesh, native export and URLs.
- Discard restores the kept version. Failed builds and delayed responses cannot replace it.
- Conflicting clients cannot silently overwrite a newer selection.
- Old result folders open without migration errors.
- Relevant OpenSCAD tests still pass.
- Actual app screenshots and native files for a feature example; agreed wheel, bookend, knob, cable holder plus a seeded random drawing. Preserve every failure and clarification.

Implementation and validation are complete; see README.md, tests.txt and product-final/. PR review and merge are the remaining steps.
