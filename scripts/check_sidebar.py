"""Check sidebar layout against a running app, without generation or compilation."""
import argparse

from playwright.sync_api import sync_playwright

from check_viewer import assert_fits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--browser")
    args = parser.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=args.browser,
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        params = [
            dict(name=f"dimension_{i}", description="Long descriptive parameter label " * 3,
                 value=20, low=1, high=100, step=1)
            for i in range(30)
        ]
        page.route("**/params", lambda route: route.fulfill(json={"params": params}))
        page.goto(args.base_url)
        page.click("#viewLatest")
        page.wait_for_function("viewer && viewer.mesh")
        for width, height in ((1440, 1000), (1024, 768), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            page.click("#modify")
            page.wait_for_selector("#paramSliders input")
            page.wait_for_timeout(200)
            assert_fits(page)
            assert page.evaluate("""() => {
              const panel = document.querySelector('#paramPanel').getBoundingClientRect();
              const list = document.querySelector('#paramSliders');
              return list.scrollHeight > list.clientHeight &&
                list.scrollWidth <= list.clientWidth &&
                panel.right === innerWidth && panel.top === 0 &&
                panel.bottom <= innerHeight && panel.right <= innerWidth &&
                document.querySelector('#paramPanel').matches(':modal');
            }"""), "Modal drawer must fit the screen and scroll without clipping labels"
            before = page.locator(".param-foot").bounding_box()
            page.locator("#paramSliders").evaluate("(el) => el.scrollTop = el.scrollHeight")
            assert page.locator(".param-foot").bounding_box() == before
            # Keep a pending edit local: this test must not invoke OpenSCAD.
            page.evaluate("""() => {
              const input = document.querySelector('#paramSliders input');
              input.value = 21;
              input.dispatchEvent(new Event('input'));
              clearTimeout(paramTimer);
            }""")
            page.click("#paramClose")
            assert page.locator("#paramPanel").is_hidden()
            assert page.locator("#modify").evaluate("(el) => el === document.activeElement")
            page.wait_for_timeout(200)
            assert_fits(page)
            page.click("#modify")
            assert page.locator("#paramSliders input").first.input_value() == "21"
            page.keyboard.press("Escape")
            assert page.locator("#paramPanel").is_hidden()
            page.click("#modify")
            page.mouse.click(5, 20)
            assert page.locator("#paramPanel").is_hidden()
        assert not errors, errors
        browser.close()
    print("PASS: modal drawer, long labels/list, fixed footer, close/reopen, Escape, backdrop, framing")


if __name__ == "__main__":
    main()
