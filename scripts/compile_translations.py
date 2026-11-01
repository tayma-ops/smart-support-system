"""Compile standard gettext catalogs without requiring GNU tools on Windows."""

from pathlib import Path

try:
    import polib
except ImportError:
    raise SystemExit(
        "Install translation tooling: python -m pip install -r requirements-dev.txt"
    ) from None

ROOT = Path(__file__).resolve().parent.parent
for source in (ROOT / "locale").glob("*/LC_MESSAGES/django.po"):
    catalog = polib.pofile(str(source))
    if catalog.untranslated_entries() or catalog.fuzzy_entries():
        raise SystemExit(f"Catalog contains untranslated or fuzzy entries: {source}")
    catalog.save_as_mofile(str(source.with_suffix(".mo")))
    print(f"Compiled {source.relative_to(ROOT)} ({len(catalog)} messages)")
