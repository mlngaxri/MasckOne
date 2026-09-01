from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WEB_HTML = ROOT / "products" / "web" / "src" / "index.html"


def test_public_web_does_not_publish_unverified_cycle_duration() -> None:
    html = WEB_HTML.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", html).lower()
    forbidden = (
        "one minute",
        "1 minute",
        "60 seconds",
        "60-second",
        "60 second",
    )
    assert not any(claim in normalized for claim in forbidden)


def test_public_web_keeps_development_evidence_boundary_visible() -> None:
    html = WEB_HTML.read_text(encoding="utf-8")
    assert "being engineered" in html
    assert "Final service geometry remains subject to engineering validation." in html
    assert "No performance or availability claim is implied by this preview." in html
