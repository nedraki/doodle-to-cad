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
const STAGE_LABELS={'waiting for your answer':'Waiting for your answer…','planning BRep geometry':'Planning drawing planes, sections and connections…','correcting BRep construction':'Correcting measured BRep construction errors…','interpreting drawing':'Reading drawing features…','planning BRep recipe':'Creating the BRep construction recipe…','building recipe':'Starting BRep worker…','building solid':'Building and checking the solid…','checking mesh':'Checking the exported mesh…','rendering views':'Rendering the part…','publishing recipe':'Saving the BRep candidate…',queued:'Queued…',analyzing:'Reading ink and geometry…',interpreting:'Building the object and part graph…',generating:'Authoring parametric OpenSCAD…',finalizing:'Preparing the 3D model…'};
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
    showClarification(id,job);
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
  finally{hideClarification();clearInterval(tick);$('#abort').hidden=true;$('#launch').hidden=false;jobId=null;jobAbort=null;health()}
};
$('#abort').onclick=async()=>{if(jobId){try{await fetch(`/api/generate/${jobId}/cancel`,{method:'POST'})}catch{}jobAbort?.abort()}else jobAbort?.abort()};
let currentRun=null;function render(d,input,meshLoaded=false){show('result');const ev=d.evaluation||{},attempts=d.attempts||[];currentRun=d;$('#statusBadge').textContent=d.success?`✓ CAD accepted · ${ev.score??'—'}/100`:`⚠ revision needed · ${ev.score??'—'}/100`;$('#dimensionBadge').textContent=`target ${d.generation?.maximum_dimension_mm??form.dimension.value} mm`;if(input)$('#inputThumb').innerHTML=`<img src="${URL.createObjectURL(input)}">YOUR INPUT`;$('#views').innerHTML=Object.entries(d.files.views||{}).map(([n,u])=>`<figure><img src="${u}?t=${Date.now()}"><figcaption>${d.revision?.id&&d.revision.id!=='original'?'Edited':'Original'} · ${n}</figcaption></figure>`).join('');$('#views').className='static-strip';$('#views').hidden=true;{const t=document.querySelector('[data-views-toggle]');if(t)t.classList.remove('active')}hideParamPanel();if(window.CadViewer&&d.files.stl){try{viewer=viewer||new CadViewer($('#viewerWrap'));if(!meshLoaded)viewer.showStl(d.files.stl,d.controls?.primary_view)}catch(e){$('#viewerWrap').insertAdjacentHTML('beforeend','<div class="viewer-fallback">WebGL unavailable — see static renders below</div>')}}else if(!window.CadViewer){$('#viewerWrap').hidden=true}$('#resultTitle').textContent=d.success?'DONE — CAD SUPERVISOR ACCEPTED':'MISSION NEEDS REVISION';const failures=(ev.failures||[]).join(' · ');$('#resultText').textContent=d.success?`${d.spec.object||'Design'} · best of ${attempts.length||1} attempt(s) · generated by ${d.model} in ${d.duration_seconds}s.`:`${failures||'The candidate did not reach the configured acceptance score.'} Best candidate: attempt ${d.selected_attempt||1}.`;const report=$('#attemptReport');if(report)report.innerHTML=attempts.map(a=>`<article class="attempt ${a.attempt===d.selected_attempt?'selected':''}"><b>#${a.attempt} · ${a.action||'generate'} · ${a.evaluation.score}/100</b><span>${Object.entries(a.evaluation.scores||{}).map(([k,v])=>`${k} ${v}`).join(' · ')}</span><p>${(a.evaluation.failures||[]).join(' · ')||'No deterministic failures.'}</p>${a.supervisor?`<p>Supervisor: ${a.supervisor.action} — ${a.supervisor.instructions||''}</p>`:''}</article>`).join('');$('#scad').href=d.files.source||d.files.scad;$('#stl').href=d.files.stl||'#';$('#stl').hidden=!d.files.stl;initializeResultVersion(d)}
$('#modify').onclick=async()=>{if(!currentRun){return $('#modifyDialog').showModal()}await openParamPanel()};$('#modifyDimension').oninput=e=>$('#modifyOut').value=e.target.value;document.querySelectorAll('.close-mod').forEach(b=>b.onclick=()=>$('#modifyDialog').close());$('#confirmModify').onclick=()=>{form.dimension.value=$('#modifyDimension').value;$('#modifyDialog').close();form.requestSubmit()};

// Keep generation provenance separate from the successfully displayed edit.
let resultVersion=null;
function initializeResultVersion(run){
  resultVersion={edited:run.backend==='usd-brep'&&!!run.revision?.id&&run.revision.id!=='original',original:{badge:$('#statusBadge').textContent,title:$('#resultTitle').textContent,text:$('#resultText').textContent}};
  const isBrep=run.backend==='usd-brep';
  $('#paramReset').textContent=isBrep?'Discard preview':'↺ Reset all';
  $('#scad').textContent=isBrep?'📥 Recipe .json':'📥 .scad';
  $('#originalScad').textContent=isBrep?'Original recipe .json':'Original .scad';
  $('#originalScad').href=(run.original_files||run.files).source||(run.original_files||run.files).scad;
  $('#usd').hidden=!run.files.usd;$('#usd').href=run.files.usd||'#';
  $('#brepDetails').hidden=isBrep||!brepConfigured;
  $('#restoreScad').hidden=!isBrep||!run.original_run_id;
  if(isBrep){
    const drawing=run.evaluation?.status||'unverified';
    $('#statusBadge').textContent=`Build: passed · Geometry: passed · Drawing: ${drawing}`;
    $('#resultTitle').textContent='INSPECT DETAILS BEFORE PRINTING';
    $('#resultText').textContent=run.evaluation?.checks
      ? run.evaluation.checks.map(c=>`${c.name}: ${c.status}`).join(' · ')
      : 'The solid and mesh passed geometry checks. Drawing fidelity has not been evaluated.';
    resultVersion.original={badge:$('#statusBadge').textContent,title:$('#resultTitle').textContent,text:$('#resultText').textContent};
  }
  $('#originalStl').href=(run.original_files||run.files).stl||'#';$('#originalStl').hidden=!(run.original_files||run.files).stl;
  renderRepairSummary(run);
  syncGeometrySelection();
  setResultEditState('original');
  if(run.backend==='openscad'&&run.repair){
    if(run.revision?.candidate){resultVersion.edited=true;
      $('#statusBadge').textContent='Repair preview · not kept';$('#resultTitle').textContent='TARGETED REPAIR PREVIEW — NOT KEPT';
      $('#resultText').textContent='Targeted candidate built from the displayed version. Keep makes it current; Discard returns to the pre-repair version; Refine runs again from this candidate.';}
    else{$('#statusBadge').textContent='Repair kept · measured checks below';$('#resultTitle').textContent='TARGETED REPAIR KEPT';}
  }
  syncRevisionControls();
}
function setResultEditState(phase){
  if(!resultVersion)return;
  const {edited,original}=resultVersion;
  const shown=edited?'edited model':'original model';
  const badge=edited?'Edited · compiled, not geometrically validated':`Original · ${original.badge}`;
  $('#statusBadge').textContent=phase==='updating'?`Updating · showing ${shown}`:phase==='failed'?`Update failed · showing ${shown}`:badge;
  $('#resultTitle').textContent=edited?'EDITED MODEL — COMPILED ONLY':original.title;
  $('#resultText').textContent=edited?'Parameter edits compiled successfully. Geometric validation has not been rerun. Downloads match the displayed model; original generation and attempt history remain available.':original.text;
  if(edited&&currentRun?.backend==='usd-brep'){
    $('#statusBadge').textContent=phase==='failed'?'Update failed · showing last valid BRep':phase==='updating'?'Updating · showing last valid BRep':'Build: passed · Geometry: passed · Drawing: unverified after edit';
    $('#resultTitle').textContent=currentRun.revision?.candidate?'EDIT PREVIEW — NOT KEPT':'SAVED BREP EDIT';
    $('#resultText').textContent='Recipe rebuilt and solid/mesh checks passed. Drawing checks have not been rerun for this edit. Downloads match the displayed part.';
  }
  $('#statusBadge').dataset.state=phase;
}

/* ---- interactive viewer + parametric editing ---- */
let viewer=null,paramState=null,paramTimer=null,paramRevision=0,paramAbort=null;
function closeParamPanel(){viewer?.highlightParameter(null);$('#paramPanel').close();$('#modify').setAttribute('aria-expanded','false')}
function hideParamPanel(){closeParamPanel();invalidateParamCompile();$('#paramSliders').innerHTML='';paramState=null;revisionBusy=false}
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
    const data=await fetch(`/api/results/${runId}/params?revision_id=${encodeURIComponent(currentRun.revision?.id||'original')}`).then(r=>{if(!r.ok)throw 0;return r.json()});
    if(currentRun?.id!==runId)return;
    if(!data.params?.length)
      {$('#paramSliders').innerHTML='<p class="param-hint">This model exposes no editable parameters. Use full regeneration.</p>';$('#paramStatus').textContent='';return}
    paramState={runId,revisionId:data.revision_id||'original',base:{},current:{},controls:new Map(),originalParams:data.params};
    viewer?.setFeatureParams(data.params);
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
      const indicate=()=>{
        list.querySelectorAll('.feature-active').forEach(el=>el.classList.remove('feature-active'));
        row.classList.add('feature-active');viewer?.highlightParameter(p.name);
      };
      const clear=()=>{
        const focused=list.querySelector('.param-row:focus-within');
        if(focused){focused.dispatchEvent(new Event('focusin'));return}
        row.classList.remove('feature-active');viewer?.highlightParameter(null);
      };
      row.addEventListener('mouseenter',indicate);
      row.addEventListener('mouseleave',clear);
      row.addEventListener('focusin',indicate);
      row.addEventListener('focusout',()=>queueMicrotask(clear));
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
          invalidateParamCompile();setResultEditState('failed');$('#paramStatus').textContent='Correct the highlighted value to update geometry.';$('#paramStatus').className='';number.setAttribute('aria-invalid','true');
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
// Invalidate on input, before the debounce expires, including pending STL loads.
function invalidateParamCompile(){
  clearTimeout(paramTimer);
  paramRevision++;
  paramAbort?.abort();paramAbort=null;
}
function scheduleParamCompile(){
  invalidateParamCompile();
  revisionBusy=true;syncRevisionControls();
  setResultEditState('updating');
  $('#paramStatus').textContent='waiting to update…';$('#paramStatus').className='busy';
  paramTimer=setTimeout(runParamCompile,350);
}
async function runParamCompile(){
  if(!paramState||$('#paramSliders [aria-invalid="true"]'))return;
  invalidateParamCompile();
  if(currentRun?.backend==='usd-brep')return runRevisionPreview();
  const revision=paramRevision,state=paramState,run=currentRun;
  const isCurrent=()=>revision===paramRevision&&paramState===state&&currentRun===run;
  const changed=Object.entries(state.current).filter(([k,v])=>v!==state.base[k]);
  const status=$('#paramStatus');
  setResultEditState('updating');
  status.textContent=changed.length?'recompiling…':'restoring original…';status.className='busy';
  try{
    let url=run.files.stl,scad=run.files.source||run.files.scad,usd=run.files.usd,params=state.originalParams;
    if(changed.length){
      const controller=new AbortController();paramAbort=controller;
      const revisionQuery=state.revisionId&&state.revisionId!=='original'?`?revision_id=${encodeURIComponent(state.revisionId)}`:'';
      const response=await fetch(`/api/results/${state.runId}/parametrize${revisionQuery}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(changed)),signal:controller.signal});
      const res=await response.json().catch(()=>({}));
      if(!isCurrent())return;
      if(!response.ok||!res.ok||!res.stl||!(res.source||res.scad))throw Error(res?.detail?.message||res.message||`Compile failed (HTTP ${response.status})`);
      url=res.stl;scad=res.source||res.scad;usd=res.usd;params=res.params||[];
    }
    if(!isCurrent())return;
    if(!viewer)throw Error('3D viewer unavailable');
    const displayed=await viewer?.replaceStl(url,params,isCurrent);
    if(!isCurrent()||displayed===false)return;
    $('#stl').href=url;$('#scad').href=scad;$('#usd').href=usd||'#';$('#usd').hidden=!usd;
    resultVersion.edited=changed.length>0;setResultEditState(changed.length?'edited':'original');
    status.textContent=changed.length?`${changed.length} param(s) updated` : '';status.className='';
  }catch(err){
    if(!isCurrent())return;
    setResultEditState('failed');
    status.textContent=`Update failed — last successful geometry retained. ${err.message}`;status.className='fail';
  }finally{if(isCurrent())paramAbort=null}
}
$('#paramReset')?.addEventListener('click',()=>{
  if(!paramState)return;
  clearTimeout(paramTimer);
  if(currentRun?.backend==='usd-brep')return restoreSavedRevision();
  paramState.current={...paramState.base};
  paramState.controls.forEach((sync,name)=>sync(paramState.base[name]));
  runParamCompile();
});

// A preview is immutable; keeping it is the only operation that changes reload state.
let revisionBusy=false;
function syncRevisionControls(){
  for(const id of ['selectionMode','selectionTarget','clearSelection'])$('#'+id).disabled=revisionBusy||geometrySelectionBusy;
  const candidate=!!currentRun?.revision?.candidate,isRepair=candidate&&currentRun?.backend==='openscad'&&!!currentRun.repair;
  $('#modify').disabled=geometrySelectionBusy||(currentRun?.backend==='openscad'&&candidate);
  $('#keepRevision').textContent=isRepair?'Keep repair':'Keep this edit';
  $('#discardRevision').textContent=isRepair?'Discard repair':'Discard preview';
  for(const id of ['keepRevision','discardRevision']){const b=$('#'+id);b.hidden=!candidate;b.disabled=revisionBusy}
  $('#refineRepair').hidden=!isRepair;$('#refineRepair').disabled=revisionBusy;
  $('#fixPart').hidden=candidate||geometrySelectionBusy;$('#fixPart').disabled=revisionBusy;
  $('#revisionStatus').textContent=isRepair?(revisionBusy?'Building repair candidate…':'Repair preview — keep or discard it.'):currentRun?.backend==='usd-brep'?(revisionBusy?'Updating preview…':candidate?'Preview — not kept':currentRun.revision?.id&&currentRun.revision.id!=='original'?'Saved edit':''):'';
}
async function runRevisionPreview(){
  const epoch=paramRevision,state=paramState,run=currentRun;
  const valid=()=>epoch===paramRevision&&paramState===state&&currentRun===run;
  const updates=Object.fromEntries(Object.entries(state.current).filter(([k,v])=>v!==state.base[k]));
  const status=$('#paramStatus');revisionBusy=true;syncRevisionControls();
  try{
    if(!Object.keys(updates).length){setResultEditState(run.revision?.candidate?'edited':'original');return}
    const controller=new AbortController();paramAbort=controller;
    const response=await fetch(`/api/results/${state.runId}/revisions/preview`,{method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,body:JSON.stringify({parent_id:state.revisionId,selection_version:run.revision?.selection_version||0,updates})});
    const candidate=await response.json();if(!valid())return;
    if(!response.ok)throw Error(candidate.detail?.message||candidate.detail||'Preview failed');
    if(!viewer)throw Error('3D viewer unavailable');
    if(!await viewer.replaceStl(candidate.files.stl,candidate.params||[],valid)||!valid())return;
    $('#stl').href=candidate.files.stl;$('#scad').href=candidate.files.source;$('#usd').href=candidate.files.usd;
    currentRun=candidate;state.revisionId=candidate.revision.id;syncGeometrySelection();
    state.base={...state.current};state.originalParams=candidate.params||state.originalParams;
    resultVersion.edited=true;setResultEditState('edited');status.textContent='Preview ready — keep or discard it.';status.className='';
  }catch(error){if(valid()){setResultEditState('failed');status.textContent=`Update failed — last valid part retained. ${error.message}`;status.className='fail'}}
  finally{if(epoch===paramRevision){revisionBusy=false;paramAbort=null;syncRevisionControls()}}
}
async function restoreSavedRevision(){
  const run=currentRun;if(!run)return;invalidateParamCompile();const epoch=paramRevision;
  revisionBusy=true;syncRevisionControls();
  try{
    const response=await fetch(`/api/results/${run.id}`);const saved=await response.json();
    if(epoch!==paramRevision||currentRun!==run)return;if(!response.ok)throw Error('Could not load the saved version');
    const valid=()=>epoch===paramRevision&&currentRun===run;
    if(await viewer.replaceStl(saved.files.stl,saved.params||[],valid)&&valid()){revisionBusy=false;render(saved,null,true)}
  }catch(error){if(epoch===paramRevision)$('#revisionStatus').textContent=error.message}
  finally{if(epoch===paramRevision){revisionBusy=false;syncRevisionControls()}}
}
$('#discardRevision').onclick=restoreSavedRevision;

/* ---- targeted repair: "this part is close — change only what I describe" ---- */
let repairEpoch=0;
const repairIcons={passed:'✓',failed:'✗',improved:'▲',regressed:'▼',unchanged:'＝',reported:'✎',measured:'▪',unverified:'?'};
function repairSummaryHtml(run){
  const rep=run.repair||{};
  const checks=(rep.checks||[]).map(c=>{
    let delta='';
    if('before' in c&&'after' in c&&c.before!==undefined&&c.after!==undefined)delta=` ${JSON.stringify(c.before)}→${JSON.stringify(c.after)}`;
    const drift=(c.drift||[]).map(d=>`${d.axis}${JSON.stringify(d.before)}→${JSON.stringify(d.after)}`).join(' ');
    return `<li><b>${repairIcons[c.status]||'·'} ${escapeHtml(c.name)}</b>${escapeHtml(delta)}${drift?` <small>drift ${escapeHtml(drift)}</small>`:''}${c.changed&&c.changed.length?` <small>changed: ${escapeHtml(c.changed.join(', '))}</small>`:''}</li>`}).join('');
  const interp=rep.interpretation
    ?`<p><b>Model interpretation:</b> ${escapeHtml(rep.interpretation.requested_change||'')}${(rep.interpretation.preserve||[]).length?` — <b>intended unchanged:</b> ${escapeHtml(rep.interpretation.preserve.join(', '))}`:''}</p>`
    :(rep.interpretation_failure?'<p><b>Model interpretation unavailable</b> — deterministic checks below are still measured.</p>':'');
  return `<b class="repair-title">TARGETED REPAIR ${run.revision?.candidate?'PREVIEW — NOT KEPT':'KEPT'}</b><p><b>Your correction:</b> ${escapeHtml(rep.instruction||'')}</p>${interp}<p><b>Started from:</b> ${escapeHtml(rep.started_from||'?')} · generation score not carried over (drawing checks not rerun)</p><ul class="repair-checks">${checks}</ul><p class="repair-note">Measured: compile, watertightness, connected components, extents, editable parameters (documented tolerances). The requested correction itself needs visual inspection above.</p>`;
}
function renderRepairSummary(run){
  const el=$('#repairSummary');
  if(run&&run.backend==='openscad'&&run.repair){el.innerHTML=repairSummaryHtml(run);el.hidden=false}
  else{el.hidden=true;el.innerHTML=''}
}
function openRepairDialog(){
  if(!currentRun)return;
  const shown=currentRun.revision?.candidate?'the displayed repair candidate':currentRun.revision?.id&&currentRun.revision.id!=='original'?'a kept revision':'the accepted generation';
  $('#repairBaseline').textContent=`The repair candidate starts from the version you see now (${shown}${currentRun.files&&(currentRun.files.source||currentRun.files.scad)&&!/(\/|\b)model\.scad(\?|$)/.test(currentRun.files.source||currentRun.files.scad)?', including applied parameter edits':''}).`;
  $('#repairError').hidden=true;$('#repairDialog').showModal();$('#repairInstruction').focus();
}
$('#fixPart').onclick=openRepairDialog;
$('#refineRepair').onclick=openRepairDialog;
document.querySelectorAll('.close-repair').forEach(b=>b.onclick=()=>$('#repairDialog').close());
$('#repairGenerate').onclick=async()=>{
  const run=currentRun,button=$('#repairGenerate');if(!run||button.disabled)return;
  const instruction=$('#repairInstruction').value.trim();
  if(!instruction){$('#repairError').hidden=false;$('#repairError').textContent='Describe the correction first.';return}
  invalidateParamCompile();const epoch=++repairEpoch;button.disabled=true;$('#repairError').hidden=true;
  try{
    const response=await fetch(`/api/results/${run.id}/revisions/repair`,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({parent_id:run.revision?.id||'original',selection_version:run.revision?.selection_version??0,instruction,
        displayed:{source:run.files.source||run.files.scad,stl:run.files.stl}})});
    const candidate=await response.json();
    if(epoch!==repairEpoch||currentRun!==run)return;
    if(!response.ok){const d=candidate.detail;throw Error(typeof d==='string'?d:d?.message||d?.compile_log||'Repair candidate failed')}
    if(!window.CadViewer)throw Error('3D viewer unavailable');
    const loaded=await viewer.replaceStl(candidate.files.stl,candidate.params||[],()=>epoch===repairEpoch&&currentRun===run);
    if(!loaded||epoch!==repairEpoch||currentRun!==run)return;
    $('#repairDialog').close();
    render(candidate,null,true);
  }catch(error){
    if(epoch===repairEpoch&&currentRun===run){$('#repairError').hidden=false;$('#repairError').textContent=`Repair failed — the displayed part was kept. ${error.message}`;}
  }finally{if(epoch===repairEpoch)button.disabled=false}
};
$('#keepRevision').onclick=async()=>{
  const run=currentRun;if(revisionBusy||!run?.revision?.candidate)return;
  invalidateParamCompile();const epoch=paramRevision;revisionBusy=true;syncRevisionControls();
  try{
    const response=await fetch(`/api/results/${run.id}/revisions/keep`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision_id:run.revision.id,selection_version:run.revision.selection_version})});
    const saved=await response.json();if(epoch!==paramRevision||currentRun!==run)return;
    if(!response.ok)throw Error(saved.detail||'Could not keep this edit');
    revisionBusy=false;render(saved,null,true);
  }catch(error){if(epoch===paramRevision)$('#resultText').textContent=error.message}
  finally{if(epoch===paramRevision){revisionBusy=false;syncRevisionControls()}}
};

let geometrySelectionRequest=0,geometrySelectionBusy=false;
const geometryTargetLabel=t=>(t?.label||'Geometry').replace(/^Cutout cut(\d+)$/, 'Rectangular opening $1');
function syncGeometrySelection(){
  const run=currentRun,catalog=run?.diagnostics?.selection_catalog;
  $('#geometrySelection').hidden=run?.backend!=='usd-brep';
  const mode=$('#selectionMode').value,selection=run?.target_selection||{status:'none'};
  const category=t=>t.rule.kind==='box_cutout'?'feature':t.rule.kind==='outer_vertical_edges'?'edges':'face';
  const targets=(catalog?.targets||[]).filter(t=>category(t)===mode);
  const select=$('#selectionTarget');select.replaceChildren(new Option('Choose a target or click its geometry',''));
  for(const target of targets)select.add(new Option(geometryTargetLabel(target),target.id));
  select.value=selection.status==='matched'?selection.target.id:'';
  $('#selectionStatus').textContent=!catalog?'Selection requires a new build with geometry details.':catalog.status==='unavailable'?'Geometry selection is unavailable for this build.':selection.status==='matched'?`Selected: ${geometryTargetLabel(selection.target)} · checked for the displayed version`:selection.status==='none'?'Choose a supported target. Drag to orbit; click to select.':`${selection.status}: ${selection.reason||'Select again.'}`;
  viewer?.setGeometrySelection(catalog,selection,mode,chooseGeometryTarget);
  syncTargetedEdit();
}
async function chooseGeometryTarget(targetId){
  const run=currentRun;if(!run||revisionBusy||geometrySelectionBusy)return;
  const request=++geometrySelectionRequest;geometrySelectionBusy=true;syncRevisionControls();
  try{
    const response=await fetch(`/api/results/${run.id}/selection`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision_id:run.revision?.id||'original',target_id:targetId||null,target_version:run.target_version||0,selection_version:run.revision?.selection_version||0})});
    const selected=await response.json();if(request!==geometrySelectionRequest||currentRun!==run)return;
    if(!response.ok)throw Error(selected.detail||'Could not select this target');
    run.target_selection=selected.target_selection;run.target_version=selected.target_version;syncGeometrySelection();
  }catch(error){if(request===geometrySelectionRequest&&currentRun===run)$('#selectionStatus').textContent=error.message}
  finally{if(request===geometrySelectionRequest){geometrySelectionBusy=false;syncRevisionControls();syncTargetedEdit()}}
}
$('#selectionMode').onchange=syncGeometrySelection;
$('#selectionTarget').onchange=e=>chooseGeometryTarget(e.target.value);
$('#clearSelection').onclick=()=>chooseGeometryTarget(null);

// Targeted edits on the selected target (#32). Data-only recipe changes with
// measured before/after checks; one editing surface is active at a time.
const TARGETED_BY_RULE={box_cutout:{operation:'pocket_depth',label:'New pocket depth'},outer_vertical_edges:{operation:'edge_fillet',label:'Fillet radius'}};
let targetedBusy=false,targetedEpoch=0;
function syncTargetedEdit(){
  const panel=$('#targetedEdit');if(!panel)return;
  const run=currentRun,selection=run?.target_selection;
  const supported=run?.backend==='usd-brep'&&selection?.status==='matched'&&TARGETED_BY_RULE[selection.target.rule.kind];
  panel.hidden=!supported;
  if(!supported){$('#targetedPreview').disabled=true;return}
  $('#targetedLabel').textContent=supported.label;
  $('#targetedPreview').disabled=targetedBusy||revisionBusy||geometrySelectionBusy;
}
$('#targetedPreview').onclick=async()=>{
  const run=currentRun;if(!run||revisionBusy||targetedBusy)return;
  const selection=run.target_selection;if(selection?.status!=='matched')return;
  const supported=TARGETED_BY_RULE[selection.target.rule.kind];if(!supported)return;
  const value=Number($('#targetedValue').value);
  if(!Number.isFinite(value)||value<=0){$('#targetedStatus').className='fail';$('#targetedStatus').textContent='Enter a positive number in millimetres.';return}
  const epoch=++targetedEpoch;targetedBusy=true;syncTargetedEdit();
  $('#targetedStatus').className='';$('#targetedStatus').textContent='Building and measuring the change…';
  try{
    const response=await fetch(`/api/results/${run.id}/revisions/targeted`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({parent_id:run.revision?.id||'original',selection_version:run.revision?.selection_version??0,operation:supported.operation,value})});
    const candidate=await response.json();if(epoch!==targetedEpoch||currentRun!==run)return;
    if(!response.ok){
      const detail=candidate.detail||{};
      const failed=detail.checks?Object.entries(detail.checks).filter(([,c])=>c.status!=='passed').map(([name])=>name).join('; '):'';
      $('#targetedStatus').className='fail';
      $('#targetedStatus').textContent=`${typeof detail==='string'?detail:(detail.message||'The change failed.')}${failed?` Failed checks: ${failed}.`:''} The saved version is unchanged.`;
      return;
    }
    if(!viewer)throw Error('3D viewer unavailable');
    if(!(await viewer.replaceStl(candidate.files.stl,candidate.params||[],()=>epoch===targetedEpoch&&currentRun===run)))return;
    if(epoch!==targetedEpoch||currentRun!==run)return;
    closeParamPanel();
    $('#stl').href=candidate.files.stl;$('#scad').href=candidate.files.source;$('#usd').href=candidate.files.usd;
    currentRun=candidate;resultVersion.edited=true;setResultEditState('edited');
    const checks=Object.entries(candidate.targeted.checks);
    const passed=checks.filter(([,c])=>c.status==='passed').length;
    $('#targetedStatus').className='';
    $('#targetedStatus').textContent=`Measured ${passed}/${checks.length} checks passed on the preview: ${checks.map(([n,c])=>`${c.status==='passed'?'✓':'✗'} ${n}`).join(' · ')}. Keep it or discard it.`;
    syncGeometrySelection();syncRevisionControls();
  }catch(error){if(epoch===targetedEpoch&&currentRun===run){$('#targetedStatus').className='fail';$('#targetedStatus').textContent=`The change failed. The saved version is unchanged. ${error.message}`}}
  finally{if(epoch===targetedEpoch){targetedBusy=false;syncTargetedEdit()}}
};

// BRep translations are separate candidates; keep the original result available.
let brepConfigured=false,scadBeforeBrep=null;
fetch('/api/brep').then(r=>r.json()).then(d=>{brepConfigured=d.configured;
  $('#brepDetails').hidden=!brepConfigured||!currentRun||currentRun.backend==='usd-brep';
}).catch(()=>{});
$('#brepDetails').onclick=async()=>{
  const run=currentRun,button=$('#brepDetails');if(!run||button.disabled)return;
  button.disabled=true;button.textContent='Building editable BRep candidate…';
  try{
    const response=await fetch(`/api/results/${run.id}/brep`,{method:'POST'});
    const candidate=await response.json();
    if(!response.ok)throw Error(candidate.detail?.message||'BRep translation failed');
    if(currentRun!==run)return;
    if(!viewer)throw Error('3D viewer unavailable');
    const loaded=await viewer.replaceStl(candidate.files.stl,[],()=>currentRun===run);
    if(!loaded||currentRun!==run)return;
    scadBeforeBrep=run;
    render(candidate,null,true);
    await openParamPanel();
  }catch(error){if(currentRun===run)$('#resultText').textContent=`BRep candidate failed. Current geometry retained. ${error.message}`;}
  finally{button.disabled=false;button.textContent='BRep from original · experimental';}
};
$('#restoreScad').onclick=async()=>{
  const run=currentRun;if(!run?.original_run_id)return;
  try{
    let original=scadBeforeBrep?.id===run.original_run_id?scadBeforeBrep:null;
    if(!original){
      const response=await fetch(`/api/results/${run.original_run_id}`);
      if(!response.ok)throw Error('Original result unavailable');
      original=await response.json();
    }
    if(currentRun!==run)return;
    if(!viewer)throw Error('3D viewer unavailable');
    const loaded=await viewer.replaceStl(original.files.stl,[],()=>currentRun===run);
    if(loaded&&currentRun===run)render(original,null,true);
  }catch(error){if(currentRun===run)$('#resultText').textContent=error.message;}
};

const defaultGenerationHelp=document.querySelector('#generationHelp').textContent;
form.backend.onchange=()=>{
  const direct=form.backend.value==='usd-brep';
  document.querySelector('#backendHelp').hidden=!direct;
  document.querySelector('#generationHelp').textContent=direct
    ? 'The agent reads the drawing and creates an editable BRep recipe. The worker checks the solid, mesh and drawing projections. Detailed features still require review.'
    : defaultGenerationHelp;
};


// Ask about one identified opening while retaining the original generation job.
let clarificationId=null;
function hideClarification(){$('#working').classList.remove('awaiting-answer');document.querySelector('#clarificationPanel')?.remove();clarificationId=null}
function showClarification(id,job){
  if(job.status!=='waiting_for_answer'||!job.question){hideClarification();return}
  const q=job.question;if(clarificationId===q.id)return;
  hideClarification();clarificationId=q.id;
  const panel=document.createElement('section');panel.id='clarificationPanel';
  panel.style.cssText='background:#fff9ed;color:#182d36;padding:24px;border:3px solid #ff593c;border-radius:18px;max-width:600px;margin:20px auto;text-align:left';
  const thickness=['wall_thickness','floor_thickness','uniform_thickness'].includes(q.kind);
  const controls=thickness?`<label>Thickness (mm)<input name="thickness" type="number" min="0.01" max="${Number(q.maximum_thickness_mm)}" step="any" required></label>`:`<label><input type="radio" name="openingChoice" value="through" required> Yes — make a through-hole</label><label><input type="radio" name="openingChoice" value="recess" required> No — leave a bottom</label><label id="recessDepthLabel" hidden>Recess depth (mm)<input name="depth" type="number" min="0.01" max="${Number(q.maximum_depth_mm)}" step="any"></label>`;
  panel.innerHTML=`<h2>One detail before we build</h2><p><b>${escapeHtml(q.feature_label)}</b></p><p>${escapeHtml(q.reason)}</p><h3>${escapeHtml(q.text)}</h3><form id="clarificationForm">${controls}<p id="answerError" role="alert"></p><button type="submit">Continue with this answer</button><button type="button" id="cancelQuestion">Cancel generation</button></form><p>Your drawing is kept. We will save your answer with the design.</p>`;
  $('#working').append(panel);$('#working').classList.add('awaiting-answer');
  const answerForm=panel.querySelector('form');
  if(!thickness)answerForm.onchange=()=>{const recess=answerForm.elements.openingChoice.value==='recess';panel.querySelector('#recessDepthLabel').hidden=!recess;answerForm.elements.depth.required=recess};
  answerForm.onsubmit=async event=>{
    event.preventDefault();const button=answerForm.querySelector('[type=submit]');button.disabled=true;
    const payload={question_id:q.id};
    if(thickness)payload.thickness_mm=Number(answerForm.elements.thickness.value);
    else{payload.choice=answerForm.elements.openingChoice.value;if(payload.choice==='recess')payload.depth_mm=Number(answerForm.elements.depth.value)}
    try{const res=await fetch(`/api/generate/${id}/answer`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await res.json();if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:'Could not save this answer.');if(clarificationId===q.id){hideClarification();$('#workText').textContent='Continuing with your answer…'}}
    catch(error){panel.querySelector('#answerError').textContent=error.message;button.disabled=false}
  };
  panel.querySelector('#cancelQuestion').onclick=()=>$('#abort').click();
}
