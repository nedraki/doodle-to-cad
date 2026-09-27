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
function escapeHtml(value){const el=document.createElement('div');el.textContent=String(value);return el.innerHTML.replaceAll('"','&quot;')}
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
let currentRun=null;function render(d,input){show('result');const ev=d.evaluation||{},attempts=d.attempts||[];currentRun=d;$('#statusBadge').textContent=d.success?`✓ CAD accepted · ${ev.score??'—'}/100`:`⚠ revision needed · ${ev.score??'—'}/100`;$('#dimensionBadge').textContent=`target ${form.dimension.value} mm`;$('#inputThumb').innerHTML=`<img src="${URL.createObjectURL(input)}">YOUR INPUT`;$('#views').innerHTML=Object.entries(d.files.views||{}).map(([n,u])=>`<figure><img src="${u}?t=${Date.now()}"><figcaption>${n}</figcaption></figure>`).join('');$('#views').className='static-strip';$('#views').hidden=true;{const t=document.querySelector('[data-views-toggle]');if(t)t.classList.remove('active')}hideParamPanel();if(window.CadViewer&&d.files.stl){try{viewer=viewer||new CadViewer($('#viewerWrap'));viewer.showStl(d.files.stl,d.controls?.primary_view)}catch(e){$('#viewerWrap').insertAdjacentHTML('beforeend','<div class="viewer-fallback">WebGL unavailable — see static renders below</div>')}}else if(!window.CadViewer){$('#viewerWrap').hidden=true}$('#resultTitle').textContent=d.success?'DONE — CAD SUPERVISOR ACCEPTED':'MISSION NEEDS REVISION';const failures=(ev.failures||[]).join(' · ');$('#resultText').textContent=d.success?`${d.spec.object||'Design'} · best of ${attempts.length||1} attempt(s) · generated by ${d.model} in ${d.duration_seconds}s.`:`${failures||'The candidate did not reach the configured acceptance score.'} Best candidate: attempt ${d.selected_attempt||1}.`;const report=$('#attemptReport');if(report)report.innerHTML=attempts.map(a=>`<article class="attempt ${a.attempt===d.selected_attempt?'selected':''}"><b>#${a.attempt} · ${a.action||'generate'} · ${a.evaluation.score}/100</b><span>${Object.entries(a.evaluation.scores||{}).map(([k,v])=>`${k} ${v}`).join(' · ')}</span><p>${(a.evaluation.failures||[]).join(' · ')||'No deterministic failures.'}</p>${a.supervisor?`<p>Supervisor: ${a.supervisor.action} — ${a.supervisor.instructions||''}</p>`:''}</article>`).join('');$('#scad').href=d.files.scad;$('#stl').href=d.files.stl||'#';$('#stl').hidden=!d.files.stl}
$('#modify').onclick=async()=>{if(!currentRun){return $('#modifyDialog').showModal()}await openParamPanel()};$('#modifyDimension').oninput=e=>$('#modifyOut').value=e.target.value;document.querySelectorAll('.close-mod').forEach(b=>b.onclick=()=>$('#modifyDialog').close());$('#confirmModify').onclick=()=>{form.dimension.value=$('#modifyDimension').value;$('#modifyDialog').close();form.requestSubmit()};

/* ---- interactive viewer + parametric editing ---- */
let viewer=null,paramState=null,paramTimer=null;
function closeParamPanel(){$('#paramPanel').close();$('#modify').setAttribute('aria-expanded','false')}
function hideParamPanel(){closeParamPanel();clearTimeout(paramTimer);$('#paramSliders').innerHTML='';paramState=null}
$('#paramClose').onclick=()=>{closeParamPanel();$('#modify').focus()};
$('#paramPanel').addEventListener('cancel',e=>{e.preventDefault();$('#paramClose').click()});
$('#paramPanel').addEventListener('click',e=>{
  if(e.target!==e.currentTarget)return;
  const bounds=e.currentTarget.getBoundingClientRect();
  if(e.clientX<bounds.left||e.clientX>bounds.right||e.clientY<bounds.top||e.clientY>bounds.bottom)$('#paramClose').click();
});
$('#viewerWrap')?.addEventListener('click',e=>{
  const t=e.target.closest('button');if(!t)return;
  if(t.dataset.rotate!==undefined)viewer?.setAutoRotate(!viewer.controls.autoRotate);
  if(t.dataset.fit!==undefined)viewer?.fitView();
  if(t.dataset.cameraView)viewer?.setView(t.dataset.cameraView);
  if(t.dataset.viewsToggle!==undefined){const v=$('#views');v.hidden=!v.hidden;t.classList.toggle('active',!v.hidden)}
});
async function openParamPanel(){
  const runId=currentRun?.id;if(!runId)return hideParamPanel();
  if(!$('#paramPanel').open)$('#paramPanel').showModal();
  $('#modify').setAttribute('aria-expanded','true');
  $('#paramClose').focus({preventScroll:true});
  if(paramState?.runId===runId)return;
  $('#paramStatus').textContent='reading parameters…';$('#paramStatus').className='';
  try{
    const data=await fetch(`/api/results/${runId}/params`).then(r=>{if(!r.ok)throw 0;return r.json()});
    if(!data.params?.length)
      {$('#paramSliders').innerHTML='<p class="param-hint">This model exposes no editable parameters. Use full regeneration.</p>';$('#paramStatus').textContent='';return}
    paramState={runId,base:{},current:{},controls:new Map()};
    const list=$('#paramSliders');list.replaceChildren();
    let lastGroup=null,container=list;
    data.params.forEach((p,index)=>{
      paramState.base[p.name]=p.value;paramState.current[p.name]=p.value;
      // Only use explicit metadata; names do not imply a geometric feature.
      const group=p.group||null;
      if(group!==lastGroup){
        container=list;
        if(group){container=document.createElement('fieldset');container.className='param-group';
          const legend=document.createElement('legend');legend.textContent=group;container.append(legend);list.append(container)}
        lastGroup=group;
      }
      const row=document.createElement('div');row.className='param-row';
      const id=`param-${index}`,label=p.label||p.description||p.name;
      const unit=p.unit==='radius/diameter'?'mm':(p.unit||'mm');
      const step=unit==='count'?1:0.01;
      const format=value=>Number(value.toFixed(2));
      row.innerHTML=`<label id="${id}-label" for="${id}-number">${escapeHtml(label)}</label>
        <div class="param-value"><output data-out="${escapeHtml(p.name)}"></output><span class="param-unit">${escapeHtml(unit)}</span></div>
        <input id="${id}-slider" type="range" data-param="${escapeHtml(p.name)}" aria-labelledby="${id}-label" step="any">
        <div class="param-entry"><button type="button" data-adjust="-1" aria-label="Decrease ${escapeHtml(label)}">−</button>
        <input id="${id}-number" type="number" aria-labelledby="${id}-label" aria-describedby="${id}-help ${id}-error">
        <button type="button" data-adjust="1" aria-label="Increase ${escapeHtml(label)}">+</button></div>
        <div id="${id}-help" class="param-help"></div>
        <p id="${id}-error" class="param-error" aria-live="polite" hidden></p>
        <button type="button" class="param-reset" data-reset="${escapeHtml(p.name)}"></button>`;
      if(p.label&&p.description){
        const effect=document.createElement('p');effect.className='param-help';effect.textContent=p.description;
        effect.id=`${id}-effect`;row.append(effect);
        row.querySelector('[type=range]').setAttribute('aria-describedby',effect.id);
        row.querySelector('[type=number]').setAttribute('aria-describedby',`${id}-help ${id}-error ${effect.id}`);
      }
      container.append(row);
      const slider=row.querySelector('[type=range]'),number=row.querySelector('[type=number]'),output=row.querySelector('output'),error=row.querySelector('.param-error');
      for(const input of [slider,number]){input.min=p.low;input.max=p.high}
      number.step=String(step);
      slider.step=unit==='count'?'1':'0.1';
      // Anchor the slider to a decimal grid, even when generated bounds are fractional.
      slider.min=Math.ceil(p.low/Number(slider.step))*Number(slider.step);
      slider.max=Math.floor(p.high/Number(slider.step))*Number(slider.step);
      row.querySelector('.param-help').textContent=`${format(p.low)}–${format(p.high)} ${unit} · slider ${slider.step} · buttons ±${step}`;
      const reset=row.querySelector('[data-reset]');reset.textContent=`↺ Reset to ${format(p.value)} ${unit}`;
      reset.setAttribute('aria-label',`Reset ${label} to ${format(p.value)} ${unit}`);
      const sync=value=>{
        slider.value=value;number.value=format(value);output.textContent=format(value);
        slider.setAttribute('aria-valuetext',`${format(Number(slider.value))} ${unit}`);
        number.setAttribute('aria-invalid','false');error.hidden=true;
        row.querySelector('[data-adjust="-1"]').disabled=value<=p.low;
        row.querySelector('[data-adjust="1"]').disabled=value>=p.high;
      };
      const commit=value=>{paramState.current[p.name]=value;sync(value);scheduleParamCompile()};
      const validate=()=>{
        const raw=number.valueAsNumber;
        const value=format(raw);
        if(!Number.isFinite(raw)||raw<p.low||raw>p.high||value<p.low||value>p.high||(unit==='count'&&!Number.isInteger(raw))){
          clearTimeout(paramTimer);number.setAttribute('aria-invalid','true');
          error.textContent=`Enter ${unit==='count'?'a whole number':'a number'} from ${format(p.low)} to ${format(p.high)} ${unit}.`;error.hidden=false;
          return false;
        }
        commit(value);return true;
      };
      const adjust=direction=>{
        if(number.getAttribute('aria-invalid')==='true')return;
        commit(Math.min(p.high,Math.max(p.low,format(format(paramState.current[p.name])+direction*step))));
      };
      slider.oninput=()=>commit(format(Number(slider.value)));
      number.oninput=validate;
      for(const input of [slider,number])input.addEventListener('keydown',event=>{
        const direction={ArrowUp:1,ArrowRight:1,ArrowDown:-1,ArrowLeft:-1}[event.key];
        if(direction&&input===number&&['ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();adjust(direction)}
        if(event.key==='Enter'&&input===number){event.preventDefault();validate()}
        if(event.key==='Escape'&&number.getAttribute('aria-invalid')==='true'){
          event.preventDefault();event.stopPropagation();sync(paramState.current[p.name]);scheduleParamCompile();
        }
      });
      row.querySelectorAll('[data-adjust]').forEach(button=>button.onclick=()=>adjust(Number(button.dataset.adjust)));
      reset.onclick=()=>commit(paramState.base[p.name]);
      paramState.controls.set(p.name,sync);sync(p.value);
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
  if(!paramState||$('#paramSliders [aria-invalid="true"]'))return;
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
  clearTimeout(paramTimer);
  paramState.current={...paramState.base};
  paramState.controls.forEach((sync,name)=>sync(paramState.base[name]));
  runParamCompile();
});
