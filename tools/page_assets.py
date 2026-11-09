"""Builds the APK's embedded page bundle for EmbeddedPages/PageAssets (1.7.4+).

The Windows build does this inside android/build.ps1. The Linux workflow needs
the same `assets/web-assets.properties` and `assets/web/**` files, or the app
throws "应用页面清单缺失" the first time it opens a computer's terminal page.

    python3 tools/page_assets.py <web-root> <assets-dir>
"""
import re
import shutil
import sys
from pathlib import Path

MIME = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".woff2": "font/woff2",
    ".bcmap": "application/octet-stream",
    ".json": "application/json",
}
SAFE_NAME = re.compile(r"[a-zA-Z0-9_./-]+\Z")


def page_assets(web: Path, assets: Path) -> int:
    """Copies web/ under assets/web/ and writes assets/web-assets.properties.
    Returns the number of manifest entries. Every file is bundled, as the
    Windows build does; only the extensions PageAssets can serve are listed."""
    target = assets / "web"
    if target.exists():
        shutil.rmtree(target)          # a rebuild must not keep files the workspace has dropped
    target.mkdir(parents=True, exist_ok=True)
    entries = []
    for path in sorted(web.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(web)
        name = relative.as_posix()
        if not SAFE_NAME.fullmatch(name):
            raise ValueError("Unsupported page asset name: " + name)
        mime = MIME.get(path.suffix)
        if mime:
            entries.append(name + "=" + mime)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    (assets / "web-assets.properties").write_text("\n".join(entries) + "\n", encoding="utf-8")
    return len(entries)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: page_assets.py <web-root> <assets-dir>")
    count = page_assets(Path(sys.argv[1]), Path(sys.argv[2]))
    print("bundled %d page assets" % count)


if __name__ == "__main__":
    main()
