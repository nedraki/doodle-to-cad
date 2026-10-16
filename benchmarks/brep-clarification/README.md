# Opening clarification fixtures

Synthetic engineering drawings for issue #25. Generated with `python -m scripts.draw_clarification_cases`.

The ambiguous drawing gives a 40 × 30 × 12 mm body and a centred Ø8 opening. It does not establish whether that opening has a floor. The clear drawing includes a section and an explicit through label.

Expected demonstrations: ask for the ambiguous opening; generate a through-hole after that answer; generate a 5 mm recess with a 7 mm floor after that answer; do not ask for the clear through-hole; cancel without publishing a completed result.

Independent checks are applied only after generation: sections at Z = 1, 6, 8 and 11 mm; boundary tolerance 0.25 mm; outer-dimension tolerance 0.25 mm; mesh-volume tolerance 10 mm³. The through volume is 40×30×12 − π×4²×12. The recess volume is 40×30×12 − π×4²×5. Mesh volume is approximate because the circle is tessellated.

The model receives the drawing and normal app controls. No reference recipe or expected-volume result enters its request. These examples do not establish robustness for all hand-drawn inputs.
