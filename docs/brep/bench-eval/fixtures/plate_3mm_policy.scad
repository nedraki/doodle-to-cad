// fixture: the policy answer is the model's truth (issue #81 EV-1)
// identical layout to plate_5mm but 3 mm thick — exactly what the frozen
// clarification policy (wall/uniform thickness 3 mm) tells an honest model
// to build when thickness is absent from ink and notes.
$fn = 64;
difference() {
  cube([100, 60, 3]);
  translate([25, 45, -1]) cylinder(d = 6, h = 5);
  translate([75, 15, -1]) cylinder(d = 6, h = 5);
  translate([50, 30, -1])
    linear_extrude(height = 5)
      hull() {
        translate([-(24 - 10) / 2, 0]) circle(d = 10);
        translate([(24 - 10) / 2, 0]) circle(d = 10);
      }
}
