# Revision contract v1

Each result folder may contain `revisions.json`. Missing history means the existing `result.json` and model source are the original root. Reading a result does not rewrite the original generation.

The store fields are `version: 1`, `selected`, `selection_version`, and `revisions` (an ID-to-record object). Each record contains `id`, `parent_id`, `kind`, `source_text`, `parameters`, and `result`. The result includes matching artifact URLs and build/drawing validation. `kind` is currently `generation` or `parameter_edit`; targeted repair must use this store with its own kind, rather than a second version system.

Candidate creation appends an immutable record. It does not change `selected`. Keep compares the expected counter, selects an existing record, increments the counter and atomically replaces the file while holding the per-result lock. The counter also prevents an old save after selection changes away and back to the same ID. Missing/unknown IDs cannot be used as filesystem paths.

Build failure produces no revision record. A successful build whose selection counter became stale may leave unselected build artifacts; it cannot become current. These artifacts are retained rather than deleted during a conflicting request. Discard in the app reloads the selected result without deleting history.

The BRep preview route invokes the native recipe builder. The store itself keeps backend-neutral source and result data. A future OpenSCAD repair adapter can append its source and build result to the same record contract. The existing OpenSCAD parameter route has not been switched to this workflow.
