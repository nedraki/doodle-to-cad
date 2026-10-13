"""One cancellable recipe job. Launched with the app Python, never generated code."""
import json
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
        result = build_recipe(out, json.loads((out / 'input.recipe.json').read_text()), on_stage=stage)
        (out / 'built.json').write_text(json.dumps(result))
    except Exception as exc:
        (out / 'error.json').write_text(json.dumps({'message': str(exc), 'code': getattr(exc, 'code', 'build_failed')}))
        raise


if __name__ == '__main__':
    main()
