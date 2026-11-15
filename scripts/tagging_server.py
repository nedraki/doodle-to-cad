"""Blind A/B + single-build grading app for the doodle-to-CAD human-review.

The app owns BOTH the display and the recording: it serves drawings and
blinded renders from disk and writes each verdict to verdicts.json
server-side, joining the sealed branch/trial mapping and the machine-judge
verdict at save time. No chat transcription, no drift.

Modes:
  /?mode=pair    run2: drawing + A vs B, grade both, pick winner (7 cases)
  /?mode=grade   run3: drawing + one build, single grade (41 builds, shuffled)

  uv run python scripts/tagging_server.py [--port 8765]
"""
from __future__ import annotations
import argparse, json, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs" / "quality-evidence" / "human-review"
RUNS = {
    "pair": {"run": REVIEW / "run2", "cases": ROOT / "scripts" / "tagging" / "cases.json"},
    "grade": {"run": REVIEW / "run3", "cases": ROOT / "scripts" / "tagging" / "cases-grade.json"},
}
MAPPING = {mode: json.loads((cfg["run"] / "mapping.json").read_text()) for mode, cfg in RUNS.items()}
GRADES = ["FLYING STARS", "PASS", "ALMOST", "GETTING THERE", "FAIL"]

PAGE = """<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Doodle review</title><style>
:root{color-scheme:dark} body{font-family:system-ui;background:#111318;color:#e8e9ee;margin:0;padding:18px}
h1{font-size:17px;margin:0 0 2px} .sub{color:#8b8fa3;font-size:12.5px;margin-bottom:14px}
.row{display:flex;gap:14px;flex-wrap:wrap} figure{margin:0;text-align:center}
figure img{width:230px;height:230px;object-fit:contain;background:#f4f1ea;border-radius:10px;border:1px solid #2a2d38}
figcaption{font-size:13px;margin-top:5px;color:#c8cad4;font-weight:600}
.side{margin-top:10px;display:flex;gap:6px;justify-content:center;flex-wrap:wrap}
.side button{font:inherit;font-size:11.5px;padding:5px 9px;border-radius:999px;border:1px solid #3a3e4d;background:#1a1d26;color:#dfe1ea;cursor:pointer}
.side button[aria-pressed=true]{background:#3f6df6;border-color:#3f6df6;color:#fff}
.card{background:#171a21;border:1px solid #262a36;border-radius:14px;padding:14px;margin-bottom:14px}
.win{display:flex;gap:8px;margin-top:12px;align-items:center;flex-wrap:wrap}
.win button{font:inherit;font-size:12px;padding:6px 12px;border-radius:8px;border:1px solid #3a3e4d;background:#1a1d26;color:#dfe1ea;cursor:pointer}
.win button[aria-pressed=true]{background:#2fa06b;border-color:#2fa06b;color:#fff}
#save{margin-left:auto;font-size:13px;font-weight:700;padding:8px 18px;border-radius:8px;border:none;background:#3f6df6;color:#fff;cursor:pointer}
#save:disabled{opacity:.35;cursor:default}
.done{color:#2fa06b;font-weight:700}
.bar{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
.bar span{font-size:11.5px;padding:4px 10px;border-radius:999px;border:1px solid #2a2d38;background:#151821;color:#8b8fa3;cursor:pointer}
.bar span.cur{border-color:#3f6df6;color:#fff;background:#22314f}
.bar span.ok{color:#2fa06b;border-color:#2fa06b}
.bar span.warn{color:#e0a63f;border-color:#e0a63f}
.note{font-size:11.5px;color:#8b8fa3;margin-top:10px}
.why{margin-top:8px} .why textarea{width:100%;box-sizing:border-box;min-height:44px;background:#12141b;color:#dfe1ea;border:1px solid #3a3e4d;border-radius:8px;font:inherit;font-size:12.5px;padding:7px;resize:vertical}
.why button{margin-top:6px;font:inherit;font-size:12px;padding:5px 12px;border-radius:8px;border:1px solid #e0a63f;background:#2a2313;color:#e0a63f;cursor:pointer}
.saved-note{font-size:12.5px;color:#c8cad4;background:#12141b;border:1px solid #2a2d38;border-radius:8px;padding:7px;margin-top:8px}
.links{margin-bottom:10px;font-size:12px} .links a{color:#7ea0ff;margin-right:12px}
</style></head><body>
<h1 id=title></h1>
<div class=sub id=sub></div>
<div class=links><a href=/?mode=pair>pair mode (A/B, 7 cases)</a><a href=/?mode=grade>grade mode (41 builds)</a></div>
<div class=bar id=bar></div>
<div id=body></div>
<script>
const MODE=new URLSearchParams(location.search).get('mode')||'pair';
let CASES=[],IDX=0,VER={},cur={A:null,B:null,W:null,G:null};
const G=["FLYING STARS","PASS","ALMOST","GETTING THERE","FAIL"];
document.getElementById('title').textContent=MODE=='pair'?'Blind A/B review — quality vs main':'Blind grading — every build';
document.getElementById('sub').textContent=MODE=='pair'
 ?'One case at a time. Grade A, grade B, pick the winner, hit Save. A/B order randomized per case; identities sealed until saved.'
 :'One build at a time, shuffled. Grade the build against the drawing. Branch/trial sealed until you save.';
function gradeBtns(side){return G.map(g=>`<button data-s=${side} data-g="${g}">${g}</button>`).join('')}
function disputed(v){if(!v)return false;const good=v.human?['FLYING STARS','PASS'].includes(v.human):(v.human_A&&v.human_A!=='FAIL'&&v.human_B!=='FAIL');const mc=v.human?v.machine==='accept':(v.A_machine==='accept'||v.B_machine==='accept');return good!==mc}
function render(){
 const c=CASES[IDX];const v=VER[c.id];
 document.getElementById('bar').innerHTML=CASES.map((x,i)=>{const sv=VER[x.id];const cls=(i==IDX?'cur ':'')+(sv&&sv.note?'ok':sv&&disputed(sv)?'warn':sv?'ok':'');return `<span class="${cls}" onclick="IDX=${i};render()">${i+1}. ${x.name}</span>`}).join('');
 if(v){
   const reveal=MODE=='pair'
     ?`branch=${v.A_branch} t${v.A_trial} machine=${v.A_machine} vs branch=${v.B_branch} t${v.B_trial} machine=${v.B_machine}`
     :`branch=${v.branch} t${v.trial} machine=${v.machine} (score ${v.score})`;
   const got=MODE=='pair'?`A: ${v.human_A} · B: ${v.human_B} · winner: ${v.winner}`:`${v.human}`;
   const flag=disputed(v)&&!v.note?'<div class=note style="color:#e0a63f">⚠ you and the machine disagree here — a one-line WHY helps most:</div>':'';
   const noteHtml=v.note?`<div class=saved-note>“${v.note}”</div>`:'';
   const figs=MODE=='pair'
     ?`<figure><img src="${c.dir}/drawing.png"><figcaption>your drawing</figcaption></figure>
       <figure><img src="${c.dir}/A.png"><figcaption>A</figcaption></figure>
       <figure><img src="${c.dir}/B.png"><figcaption>B</figcaption></figure>`
     :`<figure><img src="${c.dir}/drawing.png"><figcaption>your drawing</figcaption></figure>
       <figure><img src="${c.dir}/build.png"><figcaption>build</figcaption></figure>`;
   document.getElementById('body').innerHTML=`<div class=card><div class=row>${figs}</div>
    <div class=done style="margin-top:10px">✓ saved: ${c.name} — ${got}</div><div class=note>(revealed: ${reveal})</div>${flag}${noteHtml}
    <div class=why><textarea id=whyText placeholder="why this grade? e.g. 'handle is floating', 'missing the fins'">${v.note||''}</textarea><br><button onclick=note("${c.id}")>Save note</button></div></div>`;return}
 cur={A:null,B:null,W:null,G:null};
 if(MODE=='pair'){
  document.getElementById('body').innerHTML=`<div class=card><div class=row>
   <figure><img src="${c.dir}/drawing.png"><figcaption>your drawing</figcaption></figure>
   <figure><img src="${c.dir}/A.png"><figcaption>Result A</figcaption><div class=side>${gradeBtns('A')}</div></figure>
   <figure><img src="${c.dir}/B.png"><figcaption>Result B</figcaption><div class=side>${gradeBtns('B')}</div></figure></div>
   <div class=win>Winner: <button data-w=A>A</button><button data-w=B>B</button><button data-w=tie>tie</button><button data-w=both-fail>both fail</button>
   <button id=save disabled onclick=save()>Save verdict</button></div></div>`;
 } else {
  document.getElementById('body').innerHTML=`<div class=card><div class=row>
   <figure><img src="${c.dir}/drawing.png"><figcaption>your drawing</figcaption></figure>
   <figure><img src="${c.dir}/build.png"><figcaption>build</figcaption><div class=side>${gradeBtns('G')}</div></figure></div>
   <div class=win><button id=save disabled onclick=save()>Save grade</button></div></div>`;
 }
 document.querySelectorAll('[data-s],[data-w]').forEach(b=>b.onclick=()=>{
  if(b.dataset.s){cur[b.dataset.s]=b.dataset.g;b.parentNode.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed','false'))}
  else{cur.W=b.dataset.w;document.querySelectorAll('[data-w]').forEach(x=>x.setAttribute('aria-pressed','false'))}
  b.setAttribute('aria-pressed','true');
  document.getElementById('save').disabled=MODE=='pair'?!(cur.A&&cur.B&&cur.W):!cur.G;});
}
async function save(){
 const c=CASES[IDX];
 const payload=MODE=='pair'?{id:c.id,A:cur.A,B:cur.B,winner:cur.W}:{id:c.id,grade:cur.G};
 const r=await fetch('/api/verdict?mode='+MODE,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});
 VER[c.id]=await r.json(); render();
}
async function note(id){
 const t=document.getElementById('whyText').value.trim();
 const r=await fetch('/api/note?mode='+MODE,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id,note:t})});
 VER[id]=await r.json(); render();
}
(async()=>{CASES=await(await fetch('/api/cases?mode='+MODE)).json();VER=await(await fetch('/api/verdicts?mode='+MODE)).json();render();})();
</script></body></html>"""


def load_verdicts(mode: str) -> dict:
    f = RUNS[mode]["run"] / "verdicts.json"
    return json.loads(f.read_text()) if f.exists() else {}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _mode(self, query: str) -> str:
        m = parse_qs(query).get("mode", ["pair"])[0]
        return m if m in RUNS else "pair"

    def do_GET(self):  # noqa: N802
        u = urlparse(self.path)
        if u.path in {"/", "/index.html"}:
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif u.path == "/api/cases":
            cases = json.loads(RUNS[self._mode(u.query)]["cases"].read_text())
            self._send(200, json.dumps(cases).encode(), "application/json")
        elif u.path == "/api/verdicts":
            self._send(200, json.dumps(load_verdicts(self._mode(u.query))).encode(), "application/json")
        elif u.path.startswith("/run2/") or u.path.startswith("/run3/"):
            f = (REVIEW / u.path.lstrip("/")).resolve()
            roots = [cfg["run"].resolve() for cfg in RUNS.values()]
            if f.is_file() and any(str(f).startswith(str(r)) for r in roots):
                self._send(200, f.read_bytes(), "image/png")
            else:
                self._send(404, b"not found", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):  # noqa: N802
        u = urlparse(self.path)
        mode = self._mode(u.query)
        n = int(self.headers.get("content-length", 0))
        raw = self.rfile.read(n)
        if u.path == "/api/note":
            try:
                body = json.loads(raw)
                v = load_verdicts(mode)
                rec = v[body["id"]]
                rec["note"] = str(body.get("note", ""))[:2000]
                f = RUNS[mode]["run"] / "verdicts.json"
                tmp = f.with_suffix(".tmp")
                tmp.write_text(json.dumps(v, indent=1))
                tmp.replace(f)
                print(f"NOTE[{mode}] {body['id']}: {rec['note'][:80]}", flush=True)
                self._send(200, json.dumps(rec).encode(), "application/json")
            except Exception as exc:  # noqa: BLE001
                self._send(400, str(exc).encode(), "text/plain")
            return
        if u.path != "/api/verdict":
            self._send(404, b"no", "text/plain")
            return
        try:
            body = json.loads(raw)
            case = body["id"]
            m = MAPPING[mode][case]  # KeyError -> 400 = unknown id
            if mode == "pair":
                if not (body.get("A") and body.get("B") and body.get("winner")):
                    raise ValueError("missing field")
                if body["A"] not in GRADES or body["B"] not in GRADES:
                    raise ValueError("bad grade")
                record = {"human_A": body["A"], "human_B": body["B"], "winner": body["winner"],
                          "A_branch": m["A"], "B_branch": m["B"],
                          "A_trial": m["trial_" + m["A"]], "B_trial": m["trial_" + m["B"]],
                          "A_machine": m["machine_" + m["A"]], "B_machine": m["machine_" + m["B"]]}
            else:
                if body.get("grade") not in GRADES:
                    raise ValueError("bad grade")
                record = {"human": body["grade"], "branch": m["branch"],
                          "trial": m["trial"], "machine": m["machine"], "score": m.get("score")}
        except Exception as exc:  # noqa: BLE001
            self._send(400, str(exc).encode(), "text/plain")
            return
        record["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        v = load_verdicts(mode)
        v[case] = record
        f = RUNS[mode]["run"] / "verdicts.json"
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(v, indent=1))
        tmp.replace(f)
        print(f"VERDICT[{mode}] {case}: {json.dumps(record)}", flush=True)
        self._send(200, json.dumps(record).encode(), "application/json")

    def log_message(self, format, *args):  # noqa: A002
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    counts = {m: len(json.loads(cfg["cases"].read_text())) for m, cfg in RUNS.items()}
    print(f"tagging app on http://127.0.0.1:{args.port} modes={counts}; mappings sealed server-side", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
