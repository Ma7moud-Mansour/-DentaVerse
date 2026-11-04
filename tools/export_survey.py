"""Package the survey as one offline HTML file, without respondent data."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend" / "public" / "research"
OUTPUT = ROOT / "data" / "exports" / "DentaVerse-Survey.html"


def main():
    html = (SOURCE / "survey.html").read_text(encoding="utf-8")
    css = (SOURCE / "survey.css").read_text(encoding="utf-8")
    javascript = (SOURCE / "survey.js").read_text(encoding="utf-8")
    # Callbacks keep JS escapes literal and tolerate HTML formatter whitespace.
    html, styles = re.subn(r'<link\s+rel="stylesheet"\s+href="\./survey.css"\s*/?>', lambda _: f"<style>\n{css}\n</style>", html)
    html, scripts = re.subn(r'<script\s+src="\./survey.js"\s+defer></script>', "", html)
    html = html.replace("</body>", f"<script>\n{javascript}\n</script>\n</body>")
    if styles != 1 or scripts != 1:
        raise ValueError("Survey assets were not embedded")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Offline survey: {OUTPUT}")


if __name__ == "__main__":
    main()
