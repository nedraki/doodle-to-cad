#!/usr/bin/env bash
# Fixed 3/4 orbit-style render of the accepted multiview bookend.
# Usage: scripts/render_orbit.sh [scad-file] [out.png]
set -euo pipefail
SCAD="${1:-docs/demo/multiview_model.scad}"
OUT="${2:-docs/demo/28_mv_orbit_isometric.png}"
DIR=$(dirname "$SCAD"); BASE=$(basename "$SCAD")
# camera = focus-point(tx,ty,tz) rot(rx,ry,rz) zoom — focus on part centre (36.5,23.9,50)
docker run --rm --entrypoint bash \
  -v "$PWD/$DIR":/work -w /work openscad/openscad:latest \
  -c "xvfb-run -a openscad -o $(basename "$OUT") --imgsize 1200,900 \
      --camera=36.5,23.9,50,55,0,35,520 --preview --projection=p '$BASE' \
      && chown $(id -u):$(id -g) $(basename "$OUT")"
echo "rendered $DIR/$(basename "$OUT")"
