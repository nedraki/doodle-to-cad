"""Exercise parameter controls against a running app; mock compile requests only.

Requires an existing result with an STL. Pass --output to capture the real drawer.
"""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8080')
    parser.add_argument('--browser')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.browser, args=[
            '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors, requests = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        def compile_request(route):
            requests.append(route.request.post_data_json)
            route.fulfill(json={'ok': False, 'message': 'Compile intercepted by browser check'})
        page.route('**/parametrize', compile_request)
        page.goto(args.base_url)
        page.click('#viewLatest')
        page.wait_for_function('viewer && viewer.mesh')
        page.evaluate("viewer.setView('isometric')")
        page.click('#modify')
        page.wait_for_selector('#paramSliders input')
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(args.output / 'after.png'))
            page.set_viewport_size({'width': 390, 'height': 844})
            page.screenshot(path=str(args.output / 'after-mobile.png'))
            page.set_viewport_size({'width': 1440, 'height': 1000})
        # Known metadata exercises fractional originals, signed bounds, counts,
        # explicit grouping and escaping independently of a model's output.
        params = [
            dict(name='width', description='Width "precise"', value=12.345, low=0, high=25,
                 step=.01, unit='mm', group='Body'),
            dict(name='offset', description='Offset', value=-5, low=-10, high=0,
                 step=.01, unit='mm', group='Body'),
            dict(name='hole_count', description='Holes', value=4, low=0, high=8,
                 step=1, unit='count', group='Pattern <explicit>'),
        ]
        page.click('#paramClose')
        page.route('**/params', lambda route: route.fulfill(json={'params': params}))
        page.evaluate('hideParamPanel()')
        page.click('#modify')
        page.wait_for_selector('#param-0-number')
        number = page.locator('#param-0-number')
        slider = page.locator('#param-0-slider')
        assert number.input_value() == '12.35'
        assert slider.input_value() == '12.3'
        assert page.evaluate('paramState.current.width') == 12.345
        assert page.locator('[data-adjust="1"]').first.get_attribute('aria-label') == 'Increase Width "precise"'
        assert page.locator('.param-group legend').all_text_contents() == ['Body', 'Pattern <explicit>']
        number.fill('13.123')
        page.wait_for_timeout(450)
        assert requests[-1] == {'width': 13.12}
        assert slider.input_value() == '13.1'
        number.press('ArrowUp')
        assert number.input_value() == '13.13'
        page.locator('.param-row').first.locator('[data-adjust="-1"]').click()
        assert number.input_value() == '13.12'
        slider.focus(); slider.press('ArrowLeft')
        assert number.input_value() == '13'
        assert slider.get_attribute('step') == '0.1'
        # Blank/out-of-bounds values cancel pending edits, including other rows.
        number.fill('14')
        number.fill('')
        count = len(requests)
        page.locator('#param-1-number').fill('-4')
        page.wait_for_timeout(450)
        assert len(requests) == count
        assert number.get_attribute('aria-invalid') == 'true'
        assert page.locator('#param-0-error').is_visible()
        number.fill('26')
        page.wait_for_timeout(450)
        assert len(requests) == count
        number.press('Escape')
        assert page.locator('#paramPanel').is_visible()
        assert number.input_value() == '14'
        page.locator('[data-reset="width"]').click()
        assert number.input_value() == '12.35'
        assert slider.input_value() == '12.3'
        assert page.evaluate('paramState.current.width') == 12.345
        holes = page.locator('#param-2-number')
        holes.fill('2.5')
        page.wait_for_timeout(450)
        assert len(requests) == count
        assert holes.get_attribute('aria-invalid') == 'true'
        page.click('#paramReset')
        assert holes.input_value() == '4'
        assert page.locator('#param-1-number').input_value() == '-5'
        page.wait_for_timeout(450)
        assert len(requests) == count  # reset loads original STL, no compile
        assert page.locator('#param-2-slider').get_attribute('step') == '1'
        holes.fill('8')
        assert page.locator('.param-row').nth(2).locator('[data-adjust="1"]').is_disabled()
        page.wait_for_timeout(450)
        assert requests[-1] == {'hole_count': 8}
        assert not errors, errors
        browser.close()
    print('PASS: precise entry, sliders, keyboard, fine steps, units, explicit groups, validation, bounds, resets')


if __name__ == '__main__':
    main()
