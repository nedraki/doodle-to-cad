"""One cancellable recipe job. Launched with the app Python, never generated code."""
import json
import math
import os
from pathlib import Path
import sys

from .brep import build_recipe


def main():
    out = Path(sys.argv[1])
    def stage(value):
        pending = out / 'stage.pending'
        pending.write_text(value)
        pending.replace(out / 'stage.txt')
    try:
        context = out / 'generation.json'
        if context.exists():
            maximum = float(json.loads(context.read_text()).get('maximum_dimension_mm', 256))
            if not math.isfinite(maximum) or not 1 <= maximum <= 256:
                raise ValueError('Invalid generation maximum dimension')
            # Confined to this child process and its kernel subprocess.
            os.environ['DOODLE_BREP_MAX_DIMENSION'] = str(maximum)
        result = build_recipe(out, json.loads((out / 'input.recipe.json').read_text()), on_stage=stage)
        (out / 'built.json').write_text(json.dumps(result))
    except Exception as exc:
        (out / 'error.json').write_text(json.dumps({'message': str(exc), 'code': getattr(exc, 'code', 'build_failed')}))
        raise


if __name__ == '__main__':
    main()
