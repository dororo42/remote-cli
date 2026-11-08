"""The APK must ship the same embedded pages as the Windows build, or the app
crashes on the first terminal page with 'web-assets.properties' missing."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import page_assets  # noqa: E402


class EmbeddedPages(unittest.TestCase):
    def test_the_manifest_lists_servable_pages_and_every_file_is_bundled(self):
        with tempfile.TemporaryDirectory() as folder:
            web = Path(folder) / "web"
            (web / "terminal").mkdir(parents=True)
            (web / "index.html").write_text("<p>hello", encoding="utf-8")
            (web / "terminal" / "app.js").write_text("x", encoding="utf-8")
            (web / "notes.txt").write_text("keep me", encoding="utf-8")
            assets = Path(folder) / "assets"

            count = page_assets.page_assets(web, assets)

            self.assertEqual(count, 2)
            manifest = (assets / "web-assets.properties").read_text(encoding="utf-8")
            self.assertIn("index.html=text/html", manifest)
            self.assertIn("terminal/app.js=text/javascript", manifest)
            self.assertNotIn("notes.txt", manifest)  # not a mime PageAssets can serve
            self.assertEqual((assets / "web" / "notes.txt").read_text(encoding="utf-8"), "keep me")
            self.assertEqual((assets / "web" / "terminal" / "app.js").read_text(encoding="utf-8"), "x")

    def test_a_name_the_resolver_cannot_serve_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            web = Path(folder) / "web"
            web.mkdir()
            (web / "bad name.js").write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                page_assets.page_assets(web, Path(folder) / "assets")


if __name__ == "__main__":
    unittest.main()
