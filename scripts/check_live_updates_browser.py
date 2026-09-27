"""Live-edit browser smoke check against a running app with an existing result."""
import argparse
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:8080')
parser.add_argument('--browser')
args = parser.parse_args()
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=args.browser, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    params = [dict(name='width', value=20, low=1, high=40, unit='mm')]
    page.route('**/params', lambda route: route.fulfill(json={'params': params}))
    requests = []
    page.route('**/parametrize', lambda route: requests.append(route))
    page.goto(args.base_url)
    page.click('#viewLatest')
    page.wait_for_function('viewer && viewer.mesh')
    page.click('#modify')
    page.wait_for_selector('#param-0-number')
    page.evaluate('window.previousMesh=viewer.mesh; viewer.setAutoRotate(false)')
    for value in ['21', '22', '23']:
        page.fill('#param-0-number', value)
    page.wait_for_timeout(500)
    assert len(requests) == 1
    assert requests[0].request.post_data_json == {'width': 23}
    assert page.evaluate('viewer.mesh===window.previousMesh')
    # Orbit remains usable while compilation is pending; replacement preserves it.
    page.evaluate('viewer.camera.position.x+=10; viewer.controls.update(); window.cameraBefore=viewer.camera.position.toArray()')
    assert page.locator('#statusBadge').get_attribute('data-state') == 'updating'
    original_scad = page.locator('#scad').get_attribute('href')
    original_badge = page.evaluate('resultVersion.original.badge')
    original_history = page.locator('#attemptReport').inner_html()
    url = page.evaluate('currentRun.files.stl')
    requests[0].fulfill(json={'ok': True, 'stl': url, 'scad': '/results/test/edited.scad', 'params': params})
    page.wait_for_function('document.querySelector("#paramStatus").textContent.includes("updated")')
    assert page.evaluate('viewer.camera.position.toArray().every((v,i)=>Math.abs(v-window.cameraBefore[i])<1e-7)')
    assert page.locator('#scad').get_attribute('href') == '/results/test/edited.scad'
    assert page.locator('#originalScad').get_attribute('href') == original_scad
    assert page.locator('#statusBadge').get_attribute('data-state') == 'edited'
    assert 'not geometrically validated' in page.locator('#statusBadge').inner_text()
    assert 'COMPILED ONLY' in page.locator('#resultTitle').inner_text()
    page.evaluate('window.previousMesh=viewer.mesh')
    page.fill('#param-0-number', '24')
    page.wait_for_timeout(500)
    requests[1].fulfill(json={'ok': False, 'message': 'Intentional test compile failure'})
    page.wait_for_function('document.querySelector("#paramStatus").className==="fail"')
    assert page.evaluate('viewer.mesh===window.previousMesh')
    assert 'last successful geometry retained' in page.locator('#paramStatus').inner_text()
    assert page.locator('#statusBadge').get_attribute('data-state') == 'failed'
    assert page.locator('#scad').get_attribute('href') == '/results/test/edited.scad'
    page.click('#paramReset')
    page.wait_for_function('document.querySelector("#paramStatus").textContent===""')
    assert page.input_value('#param-0-number') == '20'
    assert page.locator('#scad').get_attribute('href') == original_scad
    assert page.locator('#stl').get_attribute('href') == url
    assert page.locator('#statusBadge').inner_text() == 'Original · ' + original_badge
    assert page.locator('#attemptReport').inner_html() == original_history
    assert not errors, errors
    browser.close()
print('Live update browser checks passed')
