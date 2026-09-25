const $=s=>document.querySelector(s),form=$('#form');let tool='pen',dirty=false,extras=[],jobId=null,jobAbort=null;
function setupCanvas(c){
  const x=c.getContext('2d');
  function resize(){
    const r=c.getBoundingClientRect(),d=devicePixelRatio||1,old=document.createElement('canvas');
    old.width=c.width; old.height=c.height;
    if(c.width&&c.height) old.getContext('2d').drawImage(c,0,0);
    c.width=Math.max(1,r.width*d); c.height=Math.max(1,r.height*d);
    x.setTransform(d,0,0,d,0,0); x.fillStyle='#fffdfa'; x.fillRect(0,0,r.width,r.height);
    if(old.width&&old.height&&r.width&&r.height) x.drawImage(old,0,0,old.width,old.height,0,0,r.width,r.height);
    x.lineCap='round'; x.lineJoin='round';
  }
  resize(); new ResizeObserver(resize).observe(c); let down=false;
  c.onpointerdown=e=>{down=true;c.setPointerCapture(e.pointerId);x.beginPath();x.moveTo(e.offsetX,e.offsetY);dirty=true};
  c.onpointermove=e=>{if(!down)return;x.strokeStyle=tool==='eraser'?'#fffdfa':'#191916';x.lineWidth=tool==='eraser'?24:4;x.lineTo(e.offsetX,e.offsetY);x.stroke()};
  c.onpointerup=()=>down=false;
  return{clear(){x.fillStyle='#fffdfa';x.fillRect(0,0,c.clientWidth,c.clientHeight)},blob:()=>new Promise(r=>c.toBlob(r,'image/png'))};
}
const primary=setupCanvas($('#canvas')),extraCanvas=setupCanvas($('#viewCanvas'));document.querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>{tool=b.dataset.tool;document.querySelectorAll('[data-tool]').forEach(x=>x.classList.toggle('active',x===b))});$('#clear').onclick=()=>{primary.clear();dirty=false};$('#image').onchange=()=>loadImage($('#image').files[0],$('#canvas'));
function loadImage(file,canvas){if(!file)return;const im=new Image;im.onload=()=>{const c=canvas.getContext('2d');c.fillStyle='#fffdfa';c.fillRect(0,0,canvas.clientWidth,canvas.clientHeight);const s=Math.min(canvas.clientWidth/im.width,canvas.clientHeight/im.height)*.88;c.drawImage(im,(canvas.clientWidth-im.width*s)/2,(canvas.clientHeight-im.height*s)/2,im.width*s,im.height*s);dirty=true};im.src=URL.createObjectURL(file)}
$('#drawView').onclick=()=>{extraCanvas.clear();$('#viewDialog').showModal()};document.querySelectorAll('.close').forEach(b=>b.onclick=()=>$('#viewDialog').close());$('#saveView').onclick=async()=>{extras.push({direction:$('#viewDirection').value,blob:await extraCanvas.blob()});$('#viewDialog').close();renderExtras()};$('#uploadView').onchange=e=>{if(e.target.files[0]){extras.push({direction:'additional',blob:e.target.files[0]});renderExtras()}e.target.value=''};
function renderExtras(){$('#viewList').innerHTML=extras.map((e,i)=>`<div class="view-item"><img src="${URL.createObjectURL(e.blob)}"><span>${e.direction}</span><button type="button" data-remove="${i}">×</button></div>`).join('');document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{extras.splice(+b.dataset.remove,1);renderExtras()})}
async function health(){try{const h=await fetch('/api/health?refresh=true').then(r=>r.json());$('#health').textContent=`model: ${h.agentic.selected_model||'unavailable'} · ${h.openscad.available?'OpenSCAD ready':'OpenSCAD missing'}`}catch{$('#health').textContent='pipeline offline'}}health();
const STAGE_LABELS={queued:'Queued…',analyzing:'Reading ink and geometry…',interpreting:'Building the object and part graph…',generating:'Authoring parametric OpenSCAD…',finalizing:'Preparing the 3D model…'};
function stageLabel(stage){if(!stage)return'Working…';const m=/^(\w+) \(attempt (\d)\)$/.exec(stage);if(m){if(m[1]==='compiling')return`Compiling STL — attempt ${m[2]} of 3…`;if(m[1]==='supervising')return`CAD supervisor reviewing attempt ${m[2]}…`}return STAGE_LABELS[stage]||'Working…'}
function showError(message,aborted){show('error');$('#error').innerHTML=`<h2>GENERATION STOPPED</h2><p>${escapeHtml(message)}</p><button type="button" id="returnToDrawing">← Return to drawing</button>`;$('#returnToDrawing').onclick=()=>{$('#inputTools').hidden=false;$('#deckTitle').textContent='BLUEPRINT DECK — FRONT & PROJECTED VIEWS';show('blueprint')};void aborted}
function escapeHtml(value){const el=document.createElement('div');el.textContent=String(value);return el.innerHTML}
function show(id){['result','working','error'].forEach(x=>$('#'+x).hidden=x!==id)}
async function pollJob(id,onStage){
  // Poll the job until the server reports it finished. Transient network
  // blips are retried; only a 404 (unknown job) or repeated hard failures
  // abort the wait. The result lives on the server, not in this connection.
  let failures=0;jobAbort=new AbortController();
  while(true){
    await new Promise(r=>setTimeout(r,2000));
    if(jobAbort.signal.aborted)return{status:'cancelled'};
    let res;
    try{res=await fetch(`/api/generate/${id}`,{signal:jobAbort.signal})}
    catch(err){if(err.name==='AbortError')return{status:'cancelled'};if(++failures>=8)throw Error('Lost contact with the server. The generation may still be finishing — reload and check the latest result.');continue}
    if(res.status===404)throw Error('The server restarted and this job was lost. Try launching the generation again.');
    if(!res.ok)throw Error(`Status check failed (HTTP ${res.status}).`);
    failures=0;
    const job=await res.json();
    onStage(job);
    if(job.status==='done')return job;
    if(job.status==='error')throw Error(job.error?.message||'Generation failed.');
    if(job.status==='cancelled')return job;
  }
}
form.onsubmit=async e=>{
  e.preventDefault();
  if(!dirty&&!$('#image').files[0])return alert('Draw or upload a primary sketch first.');
  show('working');$('#inputTools').hidden=true;$('#deckTitle').textContent='RESULT — AGENTIC CAD GENERATION';
  $('#abort').hidden=false;$('#launch').hidden=true;
  let seconds=0;const tick=setInterval(()=>$('#timer').textContent=`${++seconds}s`,1000);
  $('#workText').textContent='Queued…';
  try{
    const fd=new FormData(form),blob=await primary.blob();
    fd.append('image',blob,'primary.png');
    fd.set('strict_watertight',form.strict_watertight.checked?'true':'false');
    fd.set('view_directions',JSON.stringify(extras.map(x=>x.direction)));
    extras.forEach((x,i)=>fd.append('additional_views',x.blob,`view-${i}.png`));
    const submitted=await fetch('/api/generate',{method:'POST',body:fd});
    let submission;try{submission=await submitted.json()}catch{throw Error(`Server returned HTTP ${submitted.status} without a readable error response.`)}
    if(!submitted.ok){const detail=typeof submission.detail==='string'?submission.detail:submission.detail?.message;throw Error(detail||`Generation failed to start (HTTP ${submitted.status}).`)}
    jobId=submission.job_id;
    const job=await pollJob(jobId,j=>$('#workText').textContent=stageLabel(j.stage));
    if(job.status==='cancelled')throw Object.assign(new Error('Mission aborted.'),{name:'AbortError'});
    render(job.result,blob);
  }catch(err){showError(err.name==='AbortError'?'Mission aborted.':err.message,err.name==='AbortError')}
  finally{clearInterval(tick);$('#abort').hidden=true;$('#launch').hidden=false;jobId=null;jobAbort=null;health()}
};
$('#abort').onclick=async()=>{if(jobId){try{await fetch(`/api/generate/${jobId}/cancel`,{method:'POST'})}catch{}jobAbort?.abort()}else jobAbort?.abort()};
let currentRun=null;function render(d,input){show('result');const ev=d.evaluation||{},attempts=d.attempts||[];currentRun=d;$('#statusBadge').textContent=d.success?`✓ CAD accepted · ${ev.score??'—'}/100`:`⚠ revision needed · ${ev.score??'—'}/100`;$('#dimensionBadge').textContent=`target ${form.dimension.value} mm`;$('#inputThumb').innerHTML=`<img src="${URL.createObjectURL(input)}">YOUR INPUT`;$('#views').innerHTML=Object.entries(d.files.views||{}).map(([n,u])=>`<figure><img src="${u}?t=${Date.now()}"><figcaption>${n}</figcaption></figure>`).join('');$('#views').className='static-strip';$('#views').hidden=true;{const t=document.querySelector('[data-views-toggle]');if(t)t.classList.remove('active')}hideParamPanel();if(window.CadViewer&&d.files.stl){try{viewer=viewer||new CadViewer($('#viewerWrap'));viewer.showStl(d.files.stl)}catch(e){$('#viewerWrap').insertAdjacentHTML('beforeend','<div class="viewer-fallback">WebGL unavailable — see static renders below</div>')}}else if(!window.CadViewer){$('#viewerWrap').hidden=true}$('#resultTitle').textContent=d.success?'DONE — CAD SUPERVISOR ACCEPTED':'MISSION NEEDS REVISION';const failures=(ev.failures||[]).join(' · ');$('#resultText').textContent=d.success?`${d.spec.object||'Design'} · best of ${attempts.length||1} attempt(s) · generated by ${d.model} in ${d.duration_seconds}s.`:`${failures||'The candidate did not reach the configured acceptance score.'} Best candidate: attempt ${d.selected_attempt||1}.`;const report=$('#attemptReport');if(report)report.innerHTML=attempts.map(a=>`<article class="attempt ${a.attempt===d.selected_attempt?'selected':''}"><b>#${a.attempt} · ${a.action||'generate'} · ${a.evaluation.score}/100</b><span>${Object.entries(a.evaluation.scores||{}).map(([k,v])=>`${k} ${v}`).join(' · ')}</span><p>${(a.evaluation.failures||[]).join(' · ')||'No deterministic failures.'}</p>${a.supervisor?`<p>Supervisor: ${a.supervisor.action} — ${a.supervisor.instructions||''}</p>`:''}</article>`).join('');$('#scad').href=d.files.scad;$('#stl').href=d.files.stl||'#';$('#stl').hidden=!d.files.stl}
$('#modify').onclick=async()=>{if(!currentRun){return $('#modifyDialog').showModal()}await openParamPanel()};$('#modifyDimension').oninput=e=>$('#modifyOut').value=e.target.value;document.querySelectorAll('.close-mod').forEach(b=>b.onclick=()=>$('#modifyDialog').close());$('#confirmModify').onclick=()=>{form.dimension.value=$('#modifyDimension').value;$('#modifyDialog').close();form.requestSubmit()};

/* ---- interactive viewer + parametric editing ---- */
let viewer=null,paramState=null,paramTimer=null;
function hideParamPanel(){$('#paramPanel').hidden=true;$('#paramSliders').innerHTML='';paramState=null}
$('#viewerWrap')?.addEventListener('click',e=>{
  const t=e.target.closest('button');if(!t)return;
  if(t.dataset.rotate!==undefined)viewer?.setAutoRotate(!viewer.controls.autoRotate);
  if(t.dataset.fit!==undefined)viewer?.fitView();
  if(t.dataset.viewsToggle!==undefined){const v=$('#views');v.hidden=!v.hidden;t.classList.toggle('active',!v.hidden)}
});
async function openParamPanel(){
  const runId=currentRun?.id;if(!runId)return hideParamPanel();
  $('#paramStatus').textContent='reading parameters…';$('#paramStatus').className='';
  $('#paramPanel').hidden=false;
  try{
    const data=await fetch(`/api/results/${runId}/params`).then(r=>{if(!r.ok)throw 0;return r.json()});
    if(!data.params?.length)
      {$('#paramSliders').innerHTML='<p class="param-hint">This model exposes no editable parameters. Use full regeneration.</p>';$('#paramStatus').textContent='';return}
    paramState={runId,base:{},current:{}};
    $('#paramSliders').innerHTML=data.params.map(p=>{
      paramState.base[p.name]=p.value;paramState.current[p.name]=p.value;
      return `<div class="param-row"><label><span>${escapeHtml(p.description||p.name)}</span><output data-out="${p.name}">${p.value}</output></label>
      <input type="range" data-param="${p.name}" min="${p.low}" max="${p.high}" step="${p.step}" value="${p.value}">
      <button type="button" class="param-reset" data-reset="${p.name}">reset ${p.value}</button></div>`}).join('');
    $('#paramSliders').querySelectorAll('input[type=range]').forEach(input=>{
      const name=input.dataset.param;
      input.oninput=()=>{
        paramState.current[name]=parseFloat(input.value);
        $(`output[data-out="${name}"]`).textContent=input.value;
        scheduleParamCompile();
      };
    });
    $('#paramSliders').querySelectorAll('[data-reset]').forEach(b=>b.onclick=()=>{
      const name=b.dataset.reset,def=paramState.base[name];
      paramState.current[name]=def;
      const input=$(`input[data-param="${name}"]`);input.value=def;$(`output[data-out="${name}"]`).textContent=def;
      scheduleParamCompile();
    });
    $('#paramStatus').textContent='';
  }catch{
    $('#paramSliders').innerHTML='<p class="param-hint">Parameters unavailable — use full regeneration.</p>';
    $('#paramStatus').textContent='';
  }
}
function scheduleParamCompile(){
  clearTimeout(paramTimer);
  paramTimer=setTimeout(runParamCompile,350); // coalesce rapid drags into one compile
}
async function runParamCompile(){
  if(!paramState)return;
  const changed=Object.entries(paramState.current).filter(([k,v])=>v!==paramState.base[k]);
  const status=$('#paramStatus');
  if(!changed.length){status.textContent='';viewer?.replaceStl(currentRun.files.stl);$('#stl').href=currentRun.files.stl;return}
  status.textContent='recompiling…';status.className='busy';
  const payload=Object.fromEntries(changed);
  try{
    const res=await fetch(`/api/results/${paramState.runId}/parametrize`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)}).then(async r=>{const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d?.detail?.message||d?.message||`HTTP ${r.status}`);return d});
    if(res.ok&&res.stl){
      await viewer?.replaceStl(res.stl);          // camera untouched — geometry only
      $('#stl').href=res.stl;
      status.textContent=`${res.applied.length} param(s) live`;status.className='';
    }else{
      status.textContent=res.message||'compile failed';status.className='fail';
    }
  }catch(err){status.textContent=err.message;status.className='fail'}
}
$('#paramReset')?.addEventListener('click',()=>{
  if(!paramState)return;
  paramState.current={...paramState.base};
  $('#paramSliders').querySelectorAll('input[type=range]').forEach(i=>{i.value=paramState.base[i.dataset.param]});
  $('#paramSliders').querySelectorAll('output').forEach(o=>{o.textContent=paramState.base[o.dataset.out]});
  runParamCompile();
});
