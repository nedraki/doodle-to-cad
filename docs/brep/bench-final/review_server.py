"""Local human-review page for every published bench-final cell (issue #80).

Why: the bench publishes headline numbers, but a human must be able to judge
what the machine cannot: does the printed part actually match the drawing?
This server renders ALL cells from the frozen plan — completed, failed,
errored, unverified and superseded — never a success-only view (a filtered
gallery is how weak results hide).

Per cell: input drawing, clarification Q&A count, four fixed views, an
orbitable 3D viewer for the archived STL, the recorded reference (or an
explicit 'no reference'), every recorded check with its true/false/null
state, and downloads whose bytes are verified against MANIFEST.json before
they are served (a review must judge the SAME bytes the audit sealed).

Reviewer decisions (accepted / needs-changes / rejected) persist to
review/decisions.json, keyed by cell and bound to the archived mesh sha256,
so a decision can never silently point at different bytes than the one made
about. Decisions are human input only — no metric is derived from them here.

Isolation (plan #78): binds 127.0.0.1 only; port via BENCH_REVIEW_PORT
(default 8120, in the evidence 81xx range, never the product's 8080); the
decisions file lives under this bench dir unless BENCH_REVIEW_DECISIONS
overrides it. The product results directory is never read or written.

Run from repo root:
  python3 docs/brep/bench-final/review_server.py
"""
import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metrics  # noqa: E402  (single metric source; status vocabulary)

PORT = int(os.environ.get("BENCH_REVIEW_PORT", "8120"))
DECISIONS = Path(os.environ.get("BENCH_REVIEW_DECISIONS",
                                HERE / "review" / "decisions.json"))
CHECK_KEYS = ("build_success", "extents_pass", "genus_pass", "volume_pass",
              "fidelity_pass", "overall_pass")
DECISION_KINDS = ("accepted", "needs-changes", "rejected")

CSS = """
:root{color-scheme:dark} body{font:14px/1.45 system-ui,sans-serif;background:#101418;color:#e6edf3;margin:0;padding:18px}
h1{font-size:20px} .sub{color:#8b949e;margin-bottom:14px}
.filters{position:sticky;top:0;background:#101418;padding:8px 0;z-index:5;border-bottom:1px solid #30363d}
.filters label{margin-right:14px;color:#8b949e}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:14px}
.card{border:1px solid #30363d;border-radius:10px;padding:10px;background:#161b22}
.card h3{margin:0 0 6px;font-size:15px}
.chip{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;margin-left:6px}
.done{background:#1a3a24;color:#7ee2a1}.error{background:#3a1a1a;color:#f4907e}
.unverified{background:#3a321a;color:#e2c97e}.excluded{background:#262c33;color:#8b949e}
.views{display:flex;gap:5px;margin:8px 0}.views img{width:25%;border:1px solid #30363d;border-radius:6px}
img.input{height:120px;border:1px solid #30363d;border-radius:6px}
.checks{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0}
.ck{font-size:11px;padding:1px 7px;border-radius:6px;border:1px solid #30363d}
.ck.t{color:#7ee2a1;border-color:#1a3a24}.ck.f{color:#f4907e;border-color:#3a1a1a}.ck.n{color:#8b949e}
.meta{color:#8b949e;font-size:12px}.ref{font-size:12px;margin:6px 0;padding:6px;border-left:3px solid #30363d}
.err{color:#f4907e;font-size:12px;white-space:pre-wrap;background:#201213;padding:6px;border-radius:6px}
.dl a{font-size:12px;color:#58a6ff;text-decoration:none;margin-right:12px}
.dec{display:flex;gap:6px;align-items:center;margin-top:8px;flex-wrap:wrap}
.dec button{cursor:pointer;border:1px solid #30363d;border-radius:6px;background:#21262d;color:#e6edf3;padding:3px 10px}
.dec button.on{outline:2px solid #58a6ff}
.dec input[type=text]{flex:1;min-width:140px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#e6edf3;padding:3px 6px}
.rec{font-size:11px;color:#8b949e}
#modal{position:fixed;inset:0;background:rgba(0,0,0,.75);display:none;align-items:center;justify-content:center;z-index:9}
#modal .box{width:min(720px,92vw);height:min(560px,80vh);background:#0d1117;border:1px solid #30363d;border-radius:10px;position:relative}
#modal canvas{width:100%;height:100%}
#modal .x{position:absolute;top:6px;right:10px;cursor:pointer;color:#e6edf3;font-size:20px}
#modal .hint{position:absolute;bottom:6px;left:10px;color:#8b949e;font-size:12px}
"""

JS = """
let mod, raf;
function open3d(url){
  mod=document.getElementById('modal'); mod.style.display='flex';
  const box=mod.querySelector('.box'), cv=box.querySelector('canvas');
  import('https://unpkg.com/three@0.160.0/build/three.module.js').then(async T=>{
    const {STLLoader}=await import('https://unpkg.com/three@0.160.0/examples/jsm/loaders/STLLoader.js');
    const geoms=await new STLLoader().loadAsync(url);
    geoms.computeVertexNormals();
    const scene=new T.Scene(); scene.background=null;
    const mesh=new T.Mesh(geoms,new T.MeshStandardMaterial({color:0x7aa2c9,metalness:.1,roughness:.6,side:T.DoubleSide}));
    scene.add(mesh);
    geoms.computeBoundingBox(); const bb=geoms.boundingBox, c=bb.getCenter(new T.Vector3()), r=bb.getSize(new T.Vector3()).length();
    mesh.position.sub(c);
    const cam=new T.PerspectiveCamera(50,cv.clientWidth/cv.clientHeight,.01,r*10);
    const light=new T.DirectionalLight(0xffffff,2); light.position.set(1,1.5,1); scene.add(light,new T.AmbientLight(0xffffff,.6));
    let rx=-.6,ry=.6,drag,lx,ly,zoom=2.6;
    function place(){const d=r*zoom;cam.position.set(d*Math.sin(rx)*Math.cos(ry),d*Math.sin(ry),d*Math.cos(rx)*Math.cos(ry));cam.lookAt(0,0,0);}
    cv.onpointerdown=e=>{drag=1;lx=e.clientX;ly=e.clientY};
    cv.onpointerup=()=>drag=0;
    cv.onpointermove=e=>{if(!drag)return;ry+=.008*(e.clientX-lx);rx+=.008*(e.clientY-ly);lx=e.clientX;ly=e.clientY;};
    cv.onwheel=e=>{e.preventDefault();zoom=Math.max(.8,Math.min(6,zoom+e.deltaY*.002));};
    const ren=new T.WebGLRenderer({canvas:cv,antialias:true,alpha:true});
    function loop(){ if(!document.getElementById('modal')||mod.style.display==='none')return;
      if(!drag)ry+=.004; place(); ren.setSize(cv.clientWidth,cv.clientHeight,false); ren.render(scene,cam); raf=requestAnimationFrame(loop);}
    loop();
  }).catch(e=>{mod.querySelector('.hint').textContent='3D unavailable (offline?): '+e;});
}
function close3d(){document.getElementById('modal').style.display='none';cancelAnimationFrame(raf);}
async function decide(k,kind,note){
  const r=await fetch('/decide',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({cell:k,decision:kind,note:note||''})});
  const j=await r.json();
  const el=document.getElementById('rec-'+k.replace(/[^a-z0-9]/g,'_'));
  if(el) el.textContent=j.ok?('saved: '+j.entry.decision+' @ '+j.entry.recorded_at.slice(0,19)+'Z  mesh '+j.entry.mesh_sha256.slice(0,12)+'…'):(j.error||'failed');
  document.querySelectorAll('#dec-'+k.replace(/[^a-z0-9]/g,'_')+' button').forEach(b=>b.classList.toggle('on',b.dataset.k===kind));
}
function clearDec(k){decide(k,'','cleared');}
function filt(){
  const be=document.querySelector('#fbe').value, st=document.querySelector('#fst').value, q=document.querySelector('#fq').value.toLowerCase();
  document.querySelectorAll('.card').forEach(c=>{
    const okB=!be||c.dataset.backend===be, okS=!st||c.dataset.state===st;
    const okQ=!q||c.dataset.id.toLowerCase().includes(q);
    c.style.display=(okB&&okS&&okQ)?'':'none';});
}
"""


def chip(state):
    cls = {"done": "done", "error": "error", "unverified": "unverified"}.get(state, "excluded")
    return f'<span class="chip {cls}">{html.escape(state)}</span>'


def esc(x):
    return html.escape(str(x))


def sid_of(k):
    return re.sub(r"[^a-z0-9]", "_", k)


def render_cell(key, r, refs, manifest):
    d, b, t = key
    k = f"{d}|{b}|t{t}"
    sid = sid_of(k)
    prod = r.get("product") or {}
    st = r.get("job_status") or "?"
    excl = metrics.exclusion(r)
    if excl:
        state = "excluded"
    elif st == "done" and prod.get("status") == "unverified":
        state = "unverified"  # automatic checks passed, human verdict pending
    else:
        state = st
    build = r.get("build") or {}
    checks = r.get("checks") or {}
    score = prod.get("score")
    views = "".join(
        f'<img loading="lazy" src="/files/runs/{d}/{b}/trial-{t:02d}/views/{v}.png">'
        for v in ("front", "top", "right", "isometric"))
    cks = "".join(
        f'<span class="ck {"t" if checks.get(c) is True else "f" if checks.get(c) is False else "n"}">{c}:'
        f'{"pass" if checks.get(c) is True else "FAIL" if checks.get(c) is False else "n/a"}</span>'
        for c in CHECK_KEYS)
    ref = refs.get(d) or {}
    if ref.get("kind") == "no_ground_truth" or not ref:
        refblk = '<div class="ref">reference: <b>none published</b> (kind=' + esc(ref.get("kind", "absent")) + ") — dims/topo/vol are not applicable, never failures</div>"
    else:
        ext = ref.get("extents_mm") or build.get("extents_mm")
        refblk = (f'<div class="ref">reference <code>{esc(ref.get("kind"))}</code> · '
                  f'extents {esc(ext)} mm · genus {esc(ref.get("genus", "?"))} · '
                  f'vol {esc(ref.get("volume_mm3", "?"))} mm³ · built: genus {esc(build.get("genus"))}, '
                  f'vol {esc(build.get("volume_mm3"))} mm³</div>')
    err = ""
    if (r.get("error") or {}).get("message"):
        err = f'<div class="err">{esc(r["error"]["message"])[:600]}</div>'
    unsup = r.get("unsupported")
    if unsup:
        err += f'<div class="meta">unsupported: {esc(json.dumps(unsup))[:300]}</div>'
    mesh = build.get("sha256")
    dl = (f'<a href="/dl?cell={esc(k)}&f=stl/model.stl">STL ⧉{esc((mesh or "")[:10])}</a>'
          f'<a href="/dl?cell={esc(k)}&f=row.json">row.json</a>'
          f'<a href="/dl?cell={esc(k)}&f=input.png">input</a>')
    three = (f'<button onclick="open3d(\'/dl?cell={esc(k)}&f=stl/model.stl\')">3D orbit</button>'
             if mesh else "")
    dec_btns = "".join(
        f'<button data-k="{kind}" onclick="decide(\'{k}\',\'{kind}\','
        f'document.getElementById(\'n-{sid}\').value)">{kind}</button>'
        for kind in DECISION_KINDS)
    excl_note = f'<div class="meta">excluded: {esc(json.dumps(excl))}</div>' if excl else ""
    return (f'<div class="card" data-id="{esc(k)}" data-backend="{esc(b)}" data-state="{esc(state)}">'
            f'<h3>{esc(d)} · {esc(b)} · trial-{t:02d} {chip(state)}'
            f'{" <span class=chip done>score " + str(score) + "</span>" if score is not None else ""}</h3>'
            f'<div class="meta">{esc(r.get("submitted_at", ""))} · wall {esc(r.get("wall_seconds"))}s · '
            f'questions {esc(r.get("questions_asked") or 0)} · mesh {esc((mesh or "—")[:16])}</div>'
            f'<img class="input" loading="lazy" src="/files/runs/{d}/{b}/trial-{t:02d}/input.png">'
            f'<div class="views">{views}</div>'
            f'<div class="checks">{cks or "<span class=ck n>no checks recorded</span>"}</div>'
            f"{refblk}{err}{excl_note}"
            f'<div class="dl">{dl}</div>'
            f'<div class="dec" id="dec-{sid}">{three}{dec_btns}'
            f'<button data-k="" onclick="clearDec(\'{k}\')">clear</button>'
            f'<input type=text id="n-{sid}" placeholder="note (optional)"></div>'
            f'<div class="rec" id="rec-{sid}"></div></div>')


def render_page(cells, refs, manifest, decisions, audit):
    cards = [render_cell(k, r, refs, manifest) for k, r in sorted(cells.items())]
    n_dec = sum(1 for v in decisions.values() if v.get("decision") in DECISION_KINDS)
    aud = (audit or {}).get("summary", {})
    return ("<!doctype html><meta charset=utf-8><title>bench-final review — all cells</title>"
            f"<style>{CSS}</style>"
            "<h1>bench-final human review — every published cell</h1>"
            f'<div class="sub">{len(cards)} cells (frozen plan; nothing filtered out) · '
            f'{n_dec} reviewed · audit: {aud.get("passed", "?")}/{aud.get("checks", "?")} PASS · '
            "downloads are hash-verified against MANIFEST.json · decisions bind to the mesh hash</div>"
            '<div class="filters">'
            'backend <select id=fbe onchange=filt()><option value="">all</option>'
            '<option>openscad</option><option>usd-brep</option></select> '
            'state <select id=fst onchange=filt()><option value="">all</option>'
            '<option>done</option><option>error</option><option>unverified</option>'
            '<option>excluded</option></select> '
            '<input id=fq placeholder="filter drawing…" oninput=filt()> '
            "<label><a href=/decisions.json style='color:#58a6ff'>decisions.json</a></label></div>"
            f'<div class="grid">{"".join(cards)}</div>'
            '<div id=modal><div class=box><span class=x onclick=close3d()>×</span>'
            '<canvas></canvas><div class=hint>drag to orbit · wheel to zoom · auto-rotates</div></div></div>'
            f"<script>{JS}</script>")


def load_state():
    plan = json.loads((HERE / "TRIAL-PLAN.json").read_text())
    manifest = json.loads((HERE / "MANIFEST.json").read_text())["files"]
    refs = json.loads((HERE / "references" / "reference-measurements.json").read_text())
    audit_path = HERE / "audit-result.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    decisions = json.loads(DECISIONS.read_text()) if DECISIONS.exists() else {}
    cells = {}
    for c in plan["corpus"]:
        for b in metrics.BACKENDS:
            for t in (1, 2):
                rp = HERE / "runs" / c["id"] / b / f"trial-{t:02d}" / "row.json"
                if rp.exists():
                    cells[(c["id"], b, t)] = json.loads(rp.read_text())
    return cells, refs, manifest, decisions, audit


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        cells, refs, manifest, decisions, audit = load_state()
        if u.path == "/":
            page = render_page(cells, refs, manifest, decisions, audit)
            for k, v in decisions.items():
                if v.get("decision") in DECISION_KINDS:
                    sid = sid_of(k)
                    rec = json.dumps(v, default=str)
                    page = page.replace(f'id="rec-{sid}"></div>',
                                        f'id="rec-{sid}">recorded: {html.escape(rec[:200])}</div>')
            self._send(200, page)
        elif u.path == "/decisions.json":
            self._send(200, json.dumps(decisions, indent=1), "application/json")
        elif u.path == "/favicon.ico":
            self._send(204, b"")
        elif u.path == "/dl":
            q = parse_qs(u.query)
            cell, f = q.get("cell", [""])[0], q.get("f", [""])[0]
            try:
                d, b, t_s = cell.split("|")
                t = int(t_s.lstrip("t"))
            except ValueError:
                self._send(400, "cell must be drawing|backend|tNN")
                return
            rel = os.path.normpath(f"runs/{d}/{b}/trial-{t:02d}/{f}")
            p = HERE / rel
            if rel.startswith("..") or not p.is_file() or not str(p).startswith(str(HERE / "runs")):
                self._send(403, "download must stay inside runs/")
                return
            # the bytes handed out must equal the bytes the audit sealed, and
            # for a mesh also equal the sha the row itself recorded
            key = rel.replace("\\", "/")
            if key not in manifest:
                self._send(403, f"not sealed in MANIFEST.json: {key}")
                return
            data = p.read_bytes()
            import hashlib
            got = hashlib.sha256(data).hexdigest()
            if got != manifest[key]["sha256"]:
                self._send(403, f"BYTES DIFFER FROM SEALED HASH: {key}")
                return
            if f.endswith("model.stl"):
                rowp = HERE / f"runs/{d}/{b}/trial-{t:02d}/row.json"
                want = (json.loads(rowp.read_text()).get("build") or {}).get("sha256")
                if want and got != want:
                    self._send(403, f"MESH DIFFERS FROM ROW build.sha256: {key}")
                    return
            self._send(200, data, "application/octet-stream")
        elif u.path.startswith("/files/"):
            rel = os.path.normpath(u.path[len("/files/"):])
            p = HERE / rel
            if rel.startswith("..") or not p.is_file() or not str(p).startswith(str(HERE)):
                self._send(403, "outside the bench dir")
                return
            key = rel.replace("\\", "/")
            if key not in manifest:
                self._send(403, f"not sealed in MANIFEST.json: {key}")
                return
            import hashlib
            data = p.read_bytes()
            if hashlib.sha256(data).hexdigest() != manifest[key]["sha256"]:
                self._send(403, f"BYTES DIFFER FROM SEALED HASH: {key}")
                return
            self._send(200, data, "image/png" if rel.endswith(".png") else "application/octet-stream")
        else:
            self._send(404, "no route")

    def do_POST(self):
        if urlparse(self.path).path != "/decide":
            self._send(404, "no route")
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        key = body.get("cell", "")
        try:
            d, b, t_s = key.split("|")
            t = int(t_s.lstrip("t"))
        except ValueError:
            self._send(400, json.dumps({"error": "cell must be drawing|backend|tNN"}))
            return
        kind = body.get("decision", "")
        if kind not in DECISION_KINDS + ("",):
            self._send(400, json.dumps({"error": f"unknown decision '{kind}'"}))
            return
        rp = HERE / "runs" / d / b / f"trial-{t:02d}" / "row.json"
        if not rp.exists():
            self._send(404, json.dumps({"error": f"no such cell: {key}"}))
            return
        mesh = ((json.loads(rp.read_text()).get("build") or {}) or {}).get("sha256")
        decisions = json.loads(DECISIONS.read_text()) if DECISIONS.exists() else {}
        if kind == "":
            decisions.pop(key, None)
            entry = {"decision": None}
        else:
            entry = {"decision": kind, "note": str(body.get("note", ""))[:2000],
                     "mesh_sha256": mesh, "recorded_at": datetime.now(timezone.utc).isoformat(),
                     "reviewer": os.environ.get("USER", "unknown")}
            decisions[key] = entry
        DECISIONS.parent.mkdir(parents=True, exist_ok=True)
        tmp = DECISIONS.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(decisions, indent=1, sort_keys=True) + "\n")
        os.replace(tmp, DECISIONS)  # atomic: a crash never truncates recorded decisions
        self._send(200, json.dumps({"ok": True, "entry": entry}))


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"bench-final review server: http://127.0.0.1:{PORT}/  (decisions -> {DECISIONS})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
