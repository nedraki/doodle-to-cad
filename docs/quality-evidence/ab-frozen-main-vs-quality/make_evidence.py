"""A/B evidence figure: drawing | 3 main isos | 3 quality isos per case,
chips show the ONE-JUDGE verdict (from judged.json). Run from main-quality.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

E = Path("/home/sparkie/.hermes/profiles/doodle-to-cad/cache/scratch/ab-lamp-family")
J = E / "judge"
CASES = ["200_rocket", "201_person", "202_lamp", "203_scooter", "204_flower", "205_mug", "206_car_ink"]
OUT = Path("/home/sparkie/playground/d2c-main-quality/docs/quality-evidence/ab-frozen-main-vs-quality/ab-sheet.png")
OUT.parent.mkdir(parents=True, exist_ok=True)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
CELL, PAD, HDR = 260, 8, 56

rows = len(CASES) + 1
cols = 7
sheet = Image.new("RGB", (cols * (CELL + PAD) + PAD, rows * (CELL + PAD + 26) + HDR), (18, 18, 24))
d = ImageDraw.Draw(sheet)
d.text((PAD, 12), "A/B frozen-main vs main-quality — same judge, same rubric | chips: judge verdict (score)", font=FONT, fill=(230, 230, 235))

def paste(cell_img: Image.Image, x: int, y: int, label: str, ok: bool | None):
    img = Image.new("RGB", (CELL, CELL + 26), (26, 26, 34))
    im = cell_img.convert("RGB"); im.thumbnail((CELL - 6, CELL - 6))
    img.paste(im, (3, 3))
    dr = ImageDraw.Draw(img)
    color = (60, 200, 120) if ok else ((200, 70, 70) if ok is False else (140, 140, 150))
    dr.rounded_rectangle((4, CELL - 2, CELL - 4, CELL + 22), 6, fill=color)
    dr.text((8, CELL - 1), label, font=FONT, fill=(10, 10, 14))
    sheet.paste(img, (x, y))

hdrs = ["drawing", "main t1", "main t2", "main t3", "quality t1", "quality t2", "quality t3"]
for c, h in enumerate(hdrs):
    d.text((c * (CELL + PAD) + PAD + 6, HDR - 24), h, font=FONT, fill=(180, 180, 190))

for r, case in enumerate(CASES, start=1):
    y = HDR + (r - 1) * (CELL + PAD + 26)
    drawing = Path("/home/sparkie/playground/d2c-main-quality/benchmarks/cases") / case / "source" / "drawing.png"
    paste(Image.open(drawing), PAD, y, case, None)
    for side_i, side in enumerate(("main", "quality")):
        for t in (1, 2, 3):
            jp = E / side / case / f"trial-{t}" / "judged.json"
            ok, score = None, ""
            if jp.exists():
                j = json.loads(jp.read_text())
                ok = j.get("judge_accepted"); score = f" {j.get('judge_score') or ''}"
            view = J / f"{side}-{case}-t{t}" / "view-isometric.png"
            paste(Image.open(view) if view.exists() else Image.new("RGB", (64, 64), (60, 40, 40)),
                  (side_i * 3 + t) * (CELL + PAD) + PAD, y, f"{'M' if side=='main' else 'Q'}t{t}{score}", ok)

sheet.save(OUT)
print("saved", OUT, sheet.size)
