// Developer-only interpretation review. Does not submit the drawing generator.
if (new URLSearchParams(location.search).get('dev') === 'evidence') {
  const panel=document.createElement('section');panel.id='featureEvidence';
  panel.style.cssText='background:#f7f2e5;color:#222;padding:24px;margin:20px;border:2px solid #222;border-radius:14px;line-height:1.5';
  panel.innerHTML='<h3>Developer: drawing evidence</h3><p>Interpret the drawing without notes. This does not build a part.</p><button type="button" id="interpretEvidence">Interpret drawing</button><p id="evidenceStatus" role="status"></p><div id="evidenceReport"></div>';
  document.querySelector('.deck').append(panel);
  const button=panel.querySelector('button');button.style.cssText='padding:10px 18px;border:2px solid #222;border-radius:8px;background:#ffdc52;color:#222;font:inherit;cursor:pointer';
  function line(parent,tag,text){const el=document.createElement(tag);el.textContent=text;parent.append(el);return el;}
  window.renderFeatureEvidence = result => {
    const report=panel.querySelector('#evidenceReport');report.replaceChildren();
    line(report,'h3',result.interpretation.object_hypothesis);
    line(report,'p','Interpretation hypotheses — drawing fidelity is not verified. No part was built.');
    const link=line(report,'a','Download evidence JSON');link.href=result.files.interpretation;
    const overlay=document.createElement('img');overlay.src=result.files.overlay;overlay.alt='Measured drawing regions';overlay.style.cssText='display:block;max-width:100%;max-height:420px';report.append(overlay);
    if(result.view_assignment_review)line(report,'p',result.view_assignment_review.rule + ' Unassigned IDs: ' + result.view_assignment_review.excluded_from_direction_assignment.join(', '));
    line(report,'h4','Shared projection axes');
    for(const relation of result.shared_axis_evidence || [])line(report,'p',`${relation.axis}: ${relation.measured_spans_pixels.join(' / ')} pixels · ${relation.status}. ${relation.assumption}`);
    for(const category of ['features','relationships']){
      line(report,'h4',category==='features'?'Features':'Relationships');
      for(const claim of result.interpretation[category]){
        const card=document.createElement('article');card.style.cssText='padding:10px;margin:8px 0;border:1px solid #888;background:#fff';report.append(card);
        line(card,'strong',`${claim.id} · ${claim.status} · ${claim.type}`);
        line(card,'p',claim.description);
        line(card,'p',claim.reason);
        line(card,'small','Sources: '+claim.evidence.map(r=>`${r.view_id}/${r.region_id}`).join(', '));
        for(const ref of claim.evidence){
          const region=result.regions.find(r=>r.view_id===ref.view_id && r.region_id===ref.region_id);
          if(region)line(card,'small',` · ${region.direction}: measured view-local box [${region.bbox_view_normalized.join(', ')}]`);
        }
        if(claim.review_note)line(card,'p',claim.review_note);
      }
    }
    for(const category of ['assumptions','unresolved','conflicts']){
      line(report,'h4',category);
      const list=document.createElement('ul');report.append(list);
      for(const entry of result.interpretation[category])line(list,'li',entry);
    }
  };
  button.onclick=async()=>{
    const status=panel.querySelector('#evidenceStatus');button.disabled=true;
    try{
      const uploaded=document.querySelector('#image').files[0];
      if(!uploaded && !dirty)throw Error('Draw or upload an image first.');
      const data=new FormData();data.append('image',uploaded || await primary.blob(),uploaded?.name || 'drawing.png');
      data.append('primary_view',form.primary_view.value);data.append('projection_standard',form.projection_standard.value);
      status.textContent='Interpreting drawing evidence…';
      const response=await fetch('/api/dev/interpret',{method:'POST',body:data});const result=await response.json();
      if(!response.ok)throw Error(result.detail?.message || String(result.detail || 'Interpretation failed'));
      renderFeatureEvidence(result);status.textContent='Evidence ready for review. No geometry generated.';
    }catch(error){status.textContent=error.message}
    finally{button.disabled=false}
  };
}
