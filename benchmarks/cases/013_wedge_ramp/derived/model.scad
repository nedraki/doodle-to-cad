
// Wedge ramp: base 100(X) x 60(Y); vertical face at x=0 up to z=30; sloped top
// falls to z=0 at x=100. Flat base on bed.
polyhedron(
  points=[[0,0,0],[100,0,0],[0,0,30],[0,60,0],[100,60,0],[0,60,30]],
  faces=[[0,2,1],[3,4,5],[0,1,4,3],[0,3,5,2],[1,2,5,4]]
);
