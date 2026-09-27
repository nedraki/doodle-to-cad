# Parameter and feature metadata (version 1)

Generated SCAD carries a `/* doodle-meta { ... } */` JSON comment. Its
`parameters` object maps actual numeric top-level variable names to `label`,
`description` (the editing effect), `unit` (`mm`, `°`, `count`, `unitless`), and
an optional `feature` ID. This is an allowlist: internal constants stay hidden.
Unknown names and invalid entries are ignored. Absent, malformed, or unsupported
metadata uses the legacy parameter controls, without feature associations.

`features` maps IDs to explicitly authored CAD-world geometry:

- `{"kind":"dimension","axis":"x","label":"Overall width"}` measures the
  displayed mesh bounds on X (or Y/Z).
- `{"kind":"region","label":"Upper opening","min":[0,0,0],"max":[{"parameter":"width","scale":0.5,"offset":1},5,10]}`
  describes an axis-aligned feature bounding region in millimetres.

Coordinates may be finite numbers or affine references to literal numeric
parameters. Expressions are never evaluated. All editable placement/size
dependencies must be represented by references; unsupported geometry should
omit its overlay. Regions indicate authored bounds, not inferred STL face IDs
or independently verified geometry. Invalid references or inverted bounds
suppress the overlay. Edited responses resolve coordinates against the edited
source, while the original source remains recoverable.
