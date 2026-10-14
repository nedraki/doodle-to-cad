# Ambiguous outline fixture

`ambiguous-outline.png` is a synthetic rectangle drawn with OpenCV: a 700 × 500
white canvas and a black rectangle from (100,100) to (600,400), stroke width 5.
It contains no inner contour, hidden line, dimension, or descriptive note.

Expected interpretation: an outlined rectangular region. Depth, wall thickness,
hollow-versus-solid construction, and any open side remain unresolved. The fixture
must not be treated as proof of an enclosure shell. This is an ambiguity test, not
a reference solid. It was added for BRep task 05, issue #22.
