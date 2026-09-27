"""Browser regression check; requires a running app and an existing STL result."""
import argparse
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:8080')
parser.add_argument('--browser')
args = parser.parse_args()
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=args.browser, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    params = [dict(name='width', label='Overall width', description='Changes body width', unit='mm',
                   value=20, low=0, high=40, feature={'kind': 'dimension', 'axis': 'x', 'label': 'Overall width'}),
              dict(name='opening', label='Upper opening', description='Changes opening size', unit='mm',
                   value=10, low=0, high=20, feature={'kind': 'region', 'label': 'Upper opening', 'min': [0, 0, 0], 'max': [10, 5, 10]}),
              dict(name='legacy', description='Legacy parameter', unit='mm', value=5, low=0, high=10)]
    page.route('**/params', lambda route: route.fulfill(json={'params': params}))
    page.goto(args.base_url)
    page.click('#viewLatest')
    page.wait_for_function('viewer && viewer.mesh')
    page.click('#modify')
    page.locator('#param-0-number').focus()
    assert page.evaluate('viewer.featureOverlay.children.length') == 2
    assert 'dimension arrows' in page.locator('.feature-caption').inner_text()
    page.locator('#param-1-number').focus()
    assert page.evaluate('viewer.featureOverlay.children.length') == 1
    assert 'Upper opening' in page.locator('.feature-caption').inner_text()
    page.locator('#param-2-number').focus()
    assert page.evaluate('viewer.featureOverlay.children.length') == 0
    assert 'unavailable' in page.locator('.feature-caption').inner_text()
    page.locator('#paramClose').focus()
    page.locator('.param-row').nth(1).hover()
    assert page.evaluate('viewer.activeParameter') == 'opening'
    # Metadata and mesh are swapped together, preserving the camera.
    page.evaluate('''async () => {
      const position = viewer.camera.position.clone();
      const params = viewer.featureParams.map(p => ({...p}));
      params[1].feature = {...params[1].feature, max:[15,5,10]};
      await viewer.replaceStl(currentRun.files.stl, params);
      if (!viewer.camera.position.equals(position)) throw Error('Camera moved');
    }''')
    assert page.evaluate('viewer.featureOverlay.children[0].box.max.x') == 15
    page.click('#paramClose')
    assert page.evaluate('viewer.featureOverlay.children.length') == 0
    assert not errors, errors
    browser.close()
print('Feature highlight browser checks passed')
