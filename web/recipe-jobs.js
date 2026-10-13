// Explicit developer entrypoint. The normal drawing form is unchanged.
if (new URLSearchParams(location.search).get('dev') === 'recipes') {
  const panel = document.createElement('section');
  panel.id = 'recipeDeveloper';
  panel.innerHTML = '<h3>Developer: saved recipe</h3><p>Build JSON without a model call. Geometry checks do not verify a drawing.</p><input id="recipeFile" type="file" accept=".json,application/json"><button id="buildRecipe" type="button">Build saved recipe</button><p id="recipeJobStatus" role="status"></p>';
  document.querySelector('aside.controls').append(panel);
  const button = document.querySelector('#buildRecipe');
  const status = document.querySelector('#recipeJobStatus');
  const labels = {'queued':'Queued', 'building recipe':'Starting BRep worker', 'building solid':'Building and checking BRep solid', 'checking mesh':'Checking STL mesh', 'rendering views':'Rendering standard views', 'publishing recipe':'Saving checked result', 'cancelling':'Stopping recipe worker'};
  async function followRecipe(id) {
    jobId = id;
    sessionStorage.setItem('recipeJobId', id);
    show('working');
    document.querySelector('#inputTools').hidden = true;
    document.querySelector('#deckTitle').textContent = 'SAVED RECIPE — BREP';
    document.querySelector('#abort').hidden = false;
    document.querySelector('#launch').hidden = true;
    document.querySelector('#workText').textContent = 'Loading recipe job…';
    const job = await pollJob(id, j => {
      status.textContent = labels[j.stage] || j.stage;
      document.querySelector('#workText').textContent = status.textContent;
    });
    if (job.status === 'cancelled') {
      status.textContent = 'Recipe job cancelled. Previous results are retained.';
      showError(status.textContent, true);
    } else {
      render(job.result, null);
      status.textContent = 'BRep result ready. Solid, mesh and USD checks passed. Drawing fidelity is not evaluated.';
      sessionStorage.setItem('recipeLastResult', id);
    }
  }
  async function run(action) {
    if (jobId !== null) return;
    button.disabled = true;
    try { await action(); }
    catch (error) { status.textContent = error.message; showError(error.message, false); }
    finally {
      sessionStorage.removeItem('recipeJobId');
      jobId = null; jobAbort = null; button.disabled = false;
      document.querySelector('#abort').hidden = true;
      document.querySelector('#launch').hidden = false;
    }
  }
  button.onclick = () => run(async () => {
    const file = document.querySelector('#recipeFile').files[0];
    if (!file) throw Error('Select a recipe JSON file.');
    if (file.size > 1024 * 1024) throw Error('Recipe must be at most 1 MB.');
    const recipe = JSON.parse(await file.text());
    const response = await fetch('/api/brep/jobs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(recipe)});
    const data = await response.json();
    if (!response.ok) throw Error(data.detail?.message || 'Recipe could not start.');
    await followRecipe(data.job_id);
  });
  const saved = sessionStorage.getItem('recipeJobId') || sessionStorage.getItem('recipeLastResult');
  if (saved) run(() => followRecipe(saved));
}
