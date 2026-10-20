"""Local demo server for the issue #82 capability matrix.

  uv run python docs/brep/bench-capabilities/demo_server.py   (port 8123)

Serves one page per case: initial build and edited build as two auto-rotating
orbitable viewers, captioned with the published measurements from
results.json. Read-only; binds 127.0.0.1; serves only files under evidence/.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent
RESULTS = json.loads((HERE / "results.json").read_text())
EVID = HERE / "evidence"
PORT = 8123

JS = """
async function mount(el, url){
  const T = await import('https://unpkg.com/three@0.160.0/build/three.module.js');
  const {STLLoader} = await import('https://unpkg.com/three@0.160.0/examples/jsm/loaders/STLLoader.js');
  const geo = await new STLLoader().loadAsync(url);
  const scene = new T.Scene();
  const cam = new T.PerspectiveCamera(45, 1, 0.1, 5000);
  const renderer = new T.WebGLRenderer({antialias:true, alpha:true});
  el.appendChild(renderer.domElement);
  function fit(){ const w=el.clientWidth, h=el.clientHeight;
    renderer.setSize(w,h); cam.aspect=w/h; cam.updateProjectionMatrix(); }
  fit(); addEventListener('resize', fit);
  const box = new T.Box3().setFromBufferAttribute(geo.attributes.position);
  const c = box.getCenter(new T.Vector3()), s = box.getSize(new T.Vector3());
  const mesh = new T.Mesh(geo, new T.MeshStandardMaterial({color:0x7aa2f7, metalness:.1, roughness:.6}));
  scene.add(mesh);
  scene.add(new T.HemisphereLight(0xffffff, 0x444444, 1.6));
  const dir = new T.Vector3(1,-0.85,1).normalize();
  const dist = 2.6*Math.max(s.x,s.y,s.z);
  let ang = {t: Math.PI/5, p: Math.PI/3.5};
  function draw(){ const r=dist;
    cam.position.set(c.x + r*Math.sin(ang.p)*Math.cos(ang.t),
                     c.y + r*Math.cos(ang.p), c.z + r*Math.sin(ang.p)*Math.sin(ang.t));
    cam.lookAt(c); renderer.render(scene,cam); }
  let drag=null, orbit=true;
  el.addEventListener('pointerdown', e=>{drag=[e.clientX,e.clientY,ang.t,ang.p]; orbit=false;});
  addEventListener('pointermove', e=>{ if(drag){ ang.t=drag[2]+(e.clientX-drag[0])*0.01;
    ang.p=Math.min(Math.PI-0.05,Math.max(0.05,drag[3]-(e.clientY-drag[1])*0.01)); }});
  addEventListener('pointerup', ()=>drag=null);
  (function loop(){ if(orbit && !drag) ang.t+=0.005; draw(); requestAnimationFrame(loop); })();
}
document.querySelectorAll('[data-stl]').forEach(el=>mount(el, el.dataset.stl));
"""

PAGE = """<!doctype html><meta charset=utf-8><title>#{cid} {cap}</title>
<style>
 body{{font-family:ui-sans-serif,system-ui;background:#111418;color:#d9e0ea;margin:0;padding:16px}}
 h1{{font-size:17px}} .row{{display:flex;gap:14px}}
 .pane{{flex:1}} .v{{height:340px;border:1px solid #30363d;border-radius:8px;background:#0d1013}}
 .cap{{font-size:12px;color:#9aa7b4;margin:6px 0 14px;white-space:pre-wrap}}
 table{{font-size:12px;border-collapse:collapse}} td,th{{border:1px solid #30363d;padding:3px 8px;text-align:left}}
</style>
<h1>#{cid} — {cap}</h1>
<div class=row>
 <div class=pane><div class=v data-stl="/stl?c={cid}&t=initial"></div>
  <div class=cap>INITIAL — {ic}</div></div>
 <div class=pane><div class=v data-stl="/stl?c={cid}&t=edited"></div>
  <div class=cap>EDITED — {ec}</div></div>
</div>
<h1 style="font-size:14px">measurements</h1>{table}
<script type="importmap">{{"imports":{{"three":"https://unpkg.com/three@0.160.0/build/three.module.js"}}}}</script>
<script type=module>{js}</script>
"""


def fmt(entry):
    def caps(rec):
        if not rec:
            return "n/a"
        m = rec.get("measure") or {}
        p = rec.get("param_changed")
        head = (f"param {list(p)[0]} -> {list(p.values())[0]}" if p else "trusted recipe")
        chk = "; ".join(f"{c['check']}={'ok' if c['pass'] else 'FAIL'} ({c['got']})"
                        for c in rec.get("checks", []) if c["check"] != "volume")[:180]
        vol = m.get("mesh_volume_mm3")
        return f"{head} | status={rec.get('status')} | vol={vol} mm3\n{chk}"
    rows = ["<table><tr><th>cell</th><th>extents</th><th>genus</th><th>wt</th><th>vol mm3</th></tr>"]
    for cell, rec in (("initial", entry.get("initial")), ("edited", entry.get("edit"))):
        m = rec.get("measure") or {} if rec else {}
        rows.append(f"<tr><td>{cell}</td><td>{m.get('extents')}</td><td>{m.get('genus')}</td>"
                    f"<td>{m.get('watertight')}</td><td>{m.get('mesh_volume_mm3')}</td></tr>")
    rows.append("</table>")
    return caps(entry.get("initial")), caps(entry.get("edit")), "".join(rows)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            lis = "".join(
                f"<li><a href=/case?c={c['id']}>{c['id']}</a> — {c['capability']} "
                f"[{c['initial']['status']}{'' if 'edit' not in c else ' / edit ' + c['edit']['status']}]</li>"
                for c in RESULTS["cases"])
            self._send(200, f"<meta charset=utf-8><h1>#82 capability matrix</h1><ul>{lis}</ul>".encode(),
                       "text/html; charset=utf-8")
            return
        if u.path == "/case":
            cid = q["c"][0]
            entry = next((c for c in RESULTS["cases"] if c["id"] == cid), None)
            if not entry:
                self._send(404, b"no case", "text/plain")
                return
            ic, ec, table = fmt(entry)
            html = PAGE.format(cid=cid, cap=entry["capability"], ic=ic, ec=ec, table=table, js=JS)
            self._send(200, html.encode(), "text/html; charset=utf-8")
            return
        if u.path == "/stl":
            cid, t = q["c"][0], q["t"][0]
            if t not in ("initial", "edited") or any(x in cid for x in ("/", "..")):
                self._send(403, b"denied", "text/plain")
                return
            p = (EVID / cid / t / "model.stl").resolve()
            if not str(p).startswith(str(EVID.resolve())) or not p.exists():
                self._send(404, b"missing", "text/plain")
                return
            self._send(200, p.read_bytes(), "model/stl")
            return
        self._send(404, b"nope", "text/plain")


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
