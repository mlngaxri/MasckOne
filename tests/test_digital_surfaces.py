from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "products" / "app" / "src"
WEB = ROOT / "products" / "web" / "src"


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.anchors: list[dict[str, str]] = []
        self.buttons: list[dict[str, str]] = []
        self.elements: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if element_id := values.get("id"):
            self.ids.add(element_id)
        if tag == "a":
            self.anchors.append(values)
        if tag == "button":
            self.buttons.append(values)
        self.elements.append((tag, values))


def parse(path: Path) -> SurfaceParser:
    parser = SurfaceParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def element(parser: SurfaceParser, element_id: str) -> tuple[str, dict[str, str]]:
    for tag, attrs in parser.elements:
        if attrs.get("id") == element_id:
            return tag, attrs
    raise AssertionError(f"missing element #{element_id}")


def test_app_is_explicitly_simulated_and_has_no_dead_primary_controls() -> None:
    html = (APP / "index.html").read_text(encoding="utf-8")
    js = (APP / "app.js").read_text(encoding="utf-8")
    parser = parse(APP / "index.html")
    _, home = element(parser, "home")
    assert home["data-state-source"] == "simulated"
    assert home["data-device-transport"] == "none"
    assert "not live telemetry" in html
    assert "No device command is sent" in html
    _, live = element(parser, "simulation-status")
    assert live["role"] == "status"
    assert live["aria-live"] == "polite"
    assert live["aria-atomic"] == "true"
    preview = next(button for button in parser.buttons if button.get("id") == "preview-cleanse")
    assert preview["aria-controls"] == "simulation-status"
    assert "preview.disabled=true" in js
    assert "No device command was sent" in js
    assert not any(button.get("aria-label") == "Device settings" for button in parser.buttons)
    assert "Device settings are unavailable in this interaction prototype." in html
    forbidden_transport = ("fetch(", "XMLHttpRequest", "WebSocket", "navigator.bluetooth", "BluetoothRemoteGATT")
    assert not any(token in js for token in forbidden_transport)


def test_app_navigation_targets_exist_and_active_state_is_accessible() -> None:
    parser = parse(APP / "index.html")
    internal = [anchor for anchor in parser.anchors if anchor.get("href", "").startswith("#")]
    assert internal
    assert all(anchor["href"][1:] in parser.ids for anchor in internal)
    home = next(anchor for anchor in internal if anchor["href"] == "#home")
    assert home.get("aria-current") == "location"
    js = (APP / "app.js").read_text(encoding="utf-8")
    assert "aria-current" in js
    assert "hashchange" in js


def test_app_build_copies_runtime_script_and_accessibility_css_is_present() -> None:
    build = (ROOT / "products" / "app" / "build.mjs").read_text(encoding="utf-8")
    css = (APP / "styles.css").read_text(encoding="utf-8")
    assert "'app.js'" in build
    assert "prefers-reduced-motion:reduce" in css
    assert "prefers-contrast:more" in css
    assert "forced-colors:active" in css
    assert "safe-area-inset-bottom" in css
    assert ":focus-visible" in css
    assert ".sr-only" in css
    assert "@media(max-width:340px)" in css


def test_web_live_region_exists_before_mutation_and_early_access_fails_closed() -> None:
    parser = parse(WEB / "index.html")
    _, status = element(parser, "access-status")
    assert status["role"] == "status"
    assert status["aria-live"] == "polite"
    assert status["aria-atomic"] == "true"
    notify = next(button for button in parser.buttons if button.get("id") == "notify")
    assert notify["aria-describedby"] == "access-status"
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "button.disabled=true" in js
    assert "No signup or availability is implied" in js
    assert not any(token in js for token in ("fetch(", "XMLHttpRequest", "WebSocket"))


def test_web_navigation_and_motion_accessibility_contract() -> None:
    parser = parse(WEB / "index.html")
    internal = [anchor for anchor in parser.anchors if anchor.get("href", "").startswith("#")]
    assert internal
    assert all(anchor["href"][1:] in parser.ids for anchor in internal)
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion:reduce" in css
    assert "prefers-contrast:more" in css
    assert "forced-colors:active" in css
    assert "@media(max-width:420px)" in css
    assert ":focus-visible" in css
    assert ".skip:focus" in css


def test_brand_mark_is_identical_across_split_roots() -> None:
    web_mark = ROOT / "products" / "web" / "public" / "brand" / "brand-mark.svg"
    app_mark = ROOT / "products" / "app" / "assets" / "brand" / "brand-mark.svg"
    assert web_mark.read_bytes() == app_mark.read_bytes()


def test_history_split_workspaces_keep_mandatory_tests_and_build_cleanly(tmp_path: Path) -> None:
    npm = shutil.which("npm")
    assert npm is not None, "split-artifact verification requires npm in CI"
    for workspace in ("web", "app"):
        source = ROOT / "products" / workspace
        exported = tmp_path / workspace
        shutil.copytree(source, exported)
        package = json.loads((exported / "package.json").read_text(encoding="utf-8"))
        scripts = package.get("scripts", {})
        assert scripts.get("test") == "node test.mjs"
        assert scripts.get("prebuild") == "npm test"
        assert "--if-present" not in scripts.get("test", "")
        assert (exported / "test.mjs").is_file()
        assert not (exported / "config").exists()
        assert not (exported / "schemas").exists()
        assert not (exported / "src" / "masck_one").exists()
        commands = (
            [npm, "install", "--ignore-scripts", "--no-audit", "--no-fund", "--package-lock=false"],
            [npm, "test"],
            [npm, "run", "build"],
        )
        for command in commands:
            completed = subprocess.run(command, cwd=exported, capture_output=True, text=True, timeout=60, check=False)
            assert completed.returncode == 0, (
                f"{workspace} split-artifact command failed: {' '.join(command)}\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        dist_files = {path.name for path in (exported / "dist").iterdir() if path.is_file()}
        assert {"index.html", "styles.css", "app.js"} <= dist_files
        if workspace == "web":
            assert (exported / "dist" / "favicon.svg").is_file()
            assert (exported / "dist" / "brand" / "brand-mark.svg").is_file()
            assert (exported / "dist" / "brand" / "og-source.svg").is_file()
        else:
            assert (exported / "dist" / "assets" / "brand" / "brand-mark.svg").is_file()
            assert (exported / "dist" / "assets" / "brand" / "app-icon-source.svg").is_file()
