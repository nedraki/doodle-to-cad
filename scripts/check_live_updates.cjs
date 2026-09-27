// Deterministic response and mesh-load ordering checks against production functions.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('web/app.js','utf8');
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}};
const requests=[],loads=[],status={},link={},scadLink={},badge={dataset:{}},title={},description={},reset={};
const context=vm.createContext({AbortController,clearTimeout,setTimeout,console,
  paramState:{runId:'abcdef',base:{width:20},current:{width:21},originalParams:[],controls:new Map()},
  currentRun:{files:{stl:'original',scad:'original.scad'}},resultVersion:{edited:false,original:{badge:'CAD accepted',title:'Original title',text:'Original provenance'}},paramRevision:0,paramAbort:null,paramTimer:null,
  $:selector=>selector==='#paramStatus'?status:selector==='#stl'?link:selector==='#scad'?scadLink:selector==='#statusBadge'?badge:selector==='#resultTitle'?title:selector==='#resultText'?description:selector==='#paramReset'?{addEventListener:(_,fn)=>reset.fn=fn}:null,
  fetch:()=>{const d=deferred();requests.push(d);return d.promise},
  viewer:{replaceStl:(url,params,guard)=>{const d=deferred();loads.push({url,guard,...d});return d.promise}}
});
vm.runInContext(source.slice(source.indexOf('function setResultEditState('),source.indexOf('/* ---- interactive viewer')),context);
vm.runInContext(source.slice(source.indexOf('// Invalidate on input')),context);
const run=()=>vm.runInContext('runParamCompile()',context);
const input=value=>vm.runInContext(`paramState.current.width=${value};scheduleParamCompile();clearTimeout(paramTimer)`,context);
const respond=(request,url)=>request.resolve({ok:true,json:async()=>({ok:true,stl:url,scad:url+".scad",params:[]})});
const tick=()=>new Promise(setImmediate);
(async()=>{
  const older=run();input(22);const newer=run();
  respond(requests[1],'newer');await tick();loads[0].resolve(true);await newer;
  respond(requests[0],'older');await older;
  assert.equal(loads.length,1);assert.equal(link.href,'newer');assert.equal(scadLink.href,'newer.scad');assert.equal(badge.dataset.state,'edited');assert.match(description.textContent,/validation has not been rerun/);
  input(23);const pendingMesh=run();respond(requests[2],'pending');await tick();
  input(24);assert.equal(loads[1].guard(),false);loads[1].resolve(false);await pendingMesh;
  assert.equal(scadLink.href,'newer.scad');assert.equal(link.href,'newer');
  const pendingReset=run();reset.fn();await tick();
  assert.equal(loads[2].url,'original');loads[2].resolve(true);await tick();
  respond(requests[3],'pre-reset');await pendingReset;assert.equal(link.href,'original');assert.equal(scadLink.href,'original.scad');assert.equal(badge.dataset.state,'original');assert.equal(title.textContent,'Original title');
  input(25);const failed=run();requests[4].reject(Error('compiler unavailable'));await failed;
  assert.equal(badge.dataset.state,'failed');assert.equal(scadLink.href,'original.scad');assert.match(status.textContent,/last successful geometry retained/);assert.equal(link.href,'original');
  input(26);const failedLoad=run();respond(requests[5],'unloadable');await tick();
  loads[3].reject(Error('STL download failed'));await failedLoad;
  assert.equal(link.href,'original');assert.equal(scadLink.href,'original.scad');assert.equal(badge.dataset.state,'failed');
  input(27);const oldRun=run();vm.runInContext('currentRun={files:{stl:"different-run"}}',context);
  requests[6].reject(Error('late failure'));await oldRun;assert.equal(status.className,'busy');
  // Exercise the actual viewer guard before it can dispose the visible mesh.
  const viewerContext=vm.createContext({});
  vm.runInContext(fs.readFileSync('web/viewer.js','utf8').replace('window.CadViewer = CadViewer;',''),viewerContext);
  const load=vm.runInContext('CadViewer.prototype._load',viewerContext);
  let callback,disposed=false;
  const fake={token:0,loader:{load:(_url,cb)=>{callback=cb}}};
  const result=load.call(fake,'stale',false,[],()=>false);
  callback({dispose:()=>disposed=true});assert.equal(await result,false);assert.ok(disposed);
  console.log('Live update ordering checks passed');
})().catch(err=>{console.error(err);process.exitCode=1});
