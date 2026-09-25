(() => {
  const board=document.querySelector('#blueprint');
  const canvas=document.querySelector('#canvas');
  const overlay=document.querySelector('#projectionLines');
  const standard=document.querySelector('#projectionStandard');
  let cached={x:[],y:[]};
  let scanPending=false;

  // A technical drawing is one continuous sheet, not a collection of view boxes.
  document.querySelectorAll('.projection-zone').forEach(node=>node.remove());
  document.querySelector('#projectedSheets').remove();
  document.querySelector('#drawView').hidden=true;
  document.querySelector('#uploadView').closest('label').hidden=true;
  document.querySelector('.front-label').textContent='FRONT + PROJECTED + ISOMETRIC VIEWS · ONE DRAWING SHEET';
  document.querySelector('#deckTitle').textContent='DRAWING SHEET — ORTHOGRAPHIC + ISOMETRIC';
  const uploadLabel=document.querySelector('#image').closest('label');
  uploadLabel.childNodes[0].textContent='↑ Upload drawing sheet…';
  board.classList.add('continuous-sheet');

  function cluster(values,tolerance=5){
    if(!values.length)return[];
    values.sort((a,b)=>a-b);const groups=[];
    for(const value of values){const last=groups.at(-1);if(!last||value-last.at(-1)>tolerance)groups.push([value]);else last.push(value)}
    return groups.filter(g=>g.length>=3).map(g=>({value:g.reduce((a,b)=>a+b,0)/g.length,weight:g.length})).sort((a,b)=>b.weight-a.weight).slice(0,36).map(g=>g.value);
  }

  function scanInk(){
    scanPending=false;
    const ctx=canvas.getContext('2d'),d=devicePixelRatio||1,w=canvas.width,h=canvas.height;
    if(!w||!h)return;
    let pixels;try{pixels=ctx.getImageData(0,0,w,h).data}catch{return}
    const xs=[],ys=[],step=Math.max(2,Math.round(2*d));
    const dark=(x,y)=>{const i=(Math.min(h-1,y)*w+Math.min(w-1,x))*4;return pixels[i]<125&&pixels[i+1]<125&&pixels[i+2]<125&&pixels[i+3]>50};
    // Accumulate ink/background transitions. Long or repeated edges become stronger candidates.
    for(let y=step;y<h-step;y+=step){let previous=dark(0,y);for(let x=step;x<w;x+=step){const current=dark(x,y);if(current!==previous)xs.push(x/d);previous=current}}
    for(let x=step;x<w-step;x+=step){let previous=dark(x,0);for(let y=step;y<h;y+=step){const current=dark(x,y);if(current!==previous)ys.push(y/d);previous=current}}
    const circular=circleCandidates(dark,w,h,d,Math.max(3,Math.round(3*d)));
    cached={x:mergeCandidates(cluster(xs),circular.x),y:mergeCandidates(cluster(ys),circular.y)};
  }

  function mergeCandidates(base,extra){
    const merged=[...base];
    for(const value of extra)if(!merged.some(existing=>Math.abs(existing-value)<3))merged.push(value);
    return merged.sort((a,b)=>a-b);
  }

  function circleCandidates(dark,w,h,d,step){
    const cols=Math.ceil(w/step),rows=Math.ceil(h/step),ink=new Uint8Array(cols*rows),seen=new Uint8Array(cols*rows);
    for(let gy=0;gy<rows;gy++)for(let gx=0;gx<cols;gx++)ink[gy*cols+gx]=dark(Math.min(w-1,gx*step),Math.min(h-1,gy*step))?1:0;
    const x=[],y=[],neighbors=[[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]];
    for(let start=0;start<ink.length;start++){
      if(!ink[start]||seen[start])continue;
      const queue=[start];seen[start]=1;let head=0,minX=cols,maxX=0,minY=rows,maxY=0,count=0;
      while(head<queue.length){const at=queue[head++],gx=at%cols,gy=Math.floor(at/cols);count++;minX=Math.min(minX,gx);maxX=Math.max(maxX,gx);minY=Math.min(minY,gy);maxY=Math.max(maxY,gy);
        for(const [dx,dy] of neighbors){const nx=gx+dx,ny=gy+dy;if(nx<0||ny<0||nx>=cols||ny>=rows)continue;const ni=ny*cols+nx;if(ink[ni]&&!seen[ni]){seen[ni]=1;queue.push(ni)}}
      }
      const bw=(maxX-minX+1)*step/d,bh=(maxY-minY+1)*step/d,aspect=bw/bh,fill=count/((maxX-minX+1)*(maxY-minY+1));
      // A hand-drawn circle is roughly square and mostly empty inside. This also tolerates ellipses and imperfect rings.
      if(bw>=14&&bh>=14&&aspect>=.62&&aspect<=1.62&&fill>=.025&&fill<=.48){
        const left=minX*step/d,right=Math.min(w/d,maxX*step/d),top=minY*step/d,bottom=Math.min(h/d,maxY*step/d);
        x.push(left,(left+right)/2,right);y.push(top,(top+bottom)/2,bottom);
      }
    }
    return{x,y};
  }
  function queueScan(){if(scanPending)return;scanPending=true;setTimeout(scanInk,50)}

  function nearest(values,target,threshold){
    let best=null,distance=Infinity;
    for(const value of values){const delta=Math.abs(value-target);if(delta<distance){best=value;distance=delta}}
    return distance<=threshold?{value:best,distance}:null;
  }
  function showNearestGuide(event){
    const rect=canvas.getBoundingClientRect();
    const x=event.clientX-rect.left,y=event.clientY-rect.top;
    const vertical=nearest(cached.x,x,22),horizontal=nearest(cached.y,y,22);
    let line='';
    if(vertical&&(!horizontal||vertical.distance<=horizontal.distance))line=`<line x1="${vertical.value}" y1="0" x2="${vertical.value}" y2="${rect.height}"/>`;
    else if(horizontal)line=`<line x1="0" y1="${horizontal.value}" x2="${rect.width}" y2="${horizontal.value}"/>`;
    overlay.innerHTML=line;
  }
  canvas.addEventListener('pointermove',showNearestGuide);
  canvas.addEventListener('pointerleave',()=>overlay.innerHTML='');
  canvas.addEventListener('pointerup',queueScan);
  canvas.addEventListener('pointerdown',()=>overlay.innerHTML='');
  document.querySelector('#clear').addEventListener('click',()=>{cached={x:[],y:[]};overlay.innerHTML=''});
  document.querySelector('#image').addEventListener('change',()=>setTimeout(scanInk,200));
  standard.addEventListener('change',()=>board.dataset.projection=standard.value);
  board.dataset.projection=standard.value;
  setTimeout(scanInk,200);

  const attemptPanel=document.createElement('details');
  attemptPanel.id='attemptPanel';attemptPanel.innerHTML='<summary>CAD supervisor report</summary><div id="attemptReport"></div>';
  document.querySelector('#result').append(attemptPanel);

  const newDrawing=document.createElement('button');
  newDrawing.type='button';newDrawing.id='newDrawing';newDrawing.textContent='＋ New drawing';
  document.querySelector('.result-actions').prepend(newDrawing);
  newDrawing.addEventListener('click',()=>{
    document.querySelector('#result').hidden=true;
    document.querySelector('#error').hidden=true;
    document.querySelector('#working').hidden=true;
    document.querySelector('#inputTools').hidden=false;
    document.querySelector('#deckTitle').textContent='DRAWING SHEET — ORTHOGRAPHIC + ISOMETRIC';
    document.querySelector('#timer').textContent='';
    primary.clear();dirty=false;extras.length=0;renderExtras();cached={x:[],y:[]};overlay.innerHTML='';
  });

  // A refresh always starts a new sheet. The last server-side run is available
  // only when the user explicitly asks for it.
  const viewLatest=document.createElement('button');
  viewLatest.type='button';viewLatest.id='viewLatest';viewLatest.textContent='↺ View last result';
  document.querySelector('#launch').insertAdjacentElement('afterend',viewLatest);
  viewLatest.addEventListener('click',async()=>{
    const original=viewLatest.textContent;
    viewLatest.disabled=true;viewLatest.textContent='Loading last result…';
    try{
      const response=await fetch('/api/results/latest');
      if(!response.ok)throw new Error('No previous CAD result is available.');
      const result=await response.json();
      const inputResponse=await fetch(`/results/${result.id}/input.png`);
      const input=inputResponse.ok?await inputResponse.blob():new Blob();
      render(result,input);
      document.querySelector('#deckTitle').textContent='RESULT — AGENTIC CAD GENERATION';
      document.querySelector('#inputTools').hidden=true;
    }catch(error){
      document.querySelector('#error').hidden=false;
      document.querySelector('#error').textContent=error.message;
    }finally{
      viewLatest.disabled=false;viewLatest.textContent=original;
    }
  });
})();
