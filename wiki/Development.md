# Development

## Setup

```bash
git clone https://github.com/CptGummiball/ModFerry.git
cd ModFerry
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py
```

Use `MODFERRY_DATA` with a scratch folder while developing so your real tokens and profiles stay untouched. The tests do this automatically. CI runs the tests on Windows and Ubuntu with Python 3.10 and 3.13.

## Layout

| File | Purpose |
|---|---|
| `app.py` | Flask app: routes, validation, CurseForge/Modrinth uploads, history |
| `file_inspect.py` | project types, allowed extensions, modpack detection, dispatcher |
| `jar_inspect.py` | mod metadata (fabric/quilt/forge/neoforge) and Java bytecode |
| `pack_formats.py` | `pack.mcmeta` parsing and the pack format → Minecraft version table |
| `secrets_store.py` | encrypted token store (DPAPI / Fernet) |
| `markdown_preview.py` | sanitized Markdown rendering |
| `messages.py` | backend messages in German and English |
| `static/` | `index.html`, `style.css`, `app.js`, `i18n/*.json`, images |
| `tests/` | unit tests (no network) |

No build step and no JS framework: edit and reload.

## Translations

- UI texts: `static/i18n/de.json` and `static/i18n/en.json` (same keys in both). HTML elements use `data-i18n`, `data-i18n-ph` (placeholder) and `data-i18n-title`; JS uses `t('key', {var})`.
- Backend errors: `messages.py`. The UI sends its language in the `X-ModFerry-Lang` header.
- A new language: add `static/i18n/<code>.json`, an `<option>` in the language select, the language code to `LANGS` in `messages.py` and a translation to every entry in `MESSAGES`.

## Updating the pack format table

When Mojang releases a new version, add a row to `TABLE` in `pack_formats.py`:

```python
(('26.4',), (104, 0), (128, 1)),   # (versions, resource pack format, data pack format)
```

Take the values from the release table on the [Minecraft Wiki](https://minecraft.wiki/w/Pack_format) and add a test in `tests/test_v4.py`.

## API references

- CurseForge upload API: https://support.curseforge.com/support/solutions/articles/9000197321-curseforge-upload-api
- Modrinth create version: https://docs.modrinth.com/api/operations/createversion/
- Modrinth modpack format: https://support.modrinth.com/en/articles/8802351-modrinth-modpack-format-mrpack

## Releasing

1. Bump `VERSION` in `app.py` and add a section to `CHANGELOG.md`.
2. Run the tests.
3. Build the ZIP with `python tools/make_release.py` (creates `dist/ModFerry-<version>.zip` without user data, venv or caches).
4. Tag `vX.Y.Z`, create a GitHub release and attach the ZIP.
