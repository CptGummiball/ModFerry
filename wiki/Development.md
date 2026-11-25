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

Use `MODFERRY_DATA` with a scratch folder while developing so your real tokens and profiles stay untouched. The tests do this automatically. CI runs the tests on Windows and Ubuntu with Python 3.11 and 3.13.

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

## Versions

There is no version number to bump in the code. `version.py` reads it from:

1. the `VERSION` file inside a release ZIP (written from the Git tag),
2. `git describe` in a Git checkout (e.g. `5.0.0` on the tag, `5.0.0-3-gabc1234` three commits later),
3. otherwise `dev`.

## Releasing

1. On GitHub: **Releases → Draft a new release**.
2. Type a new tag such as `v5.1.0` (`vMAJOR.MINOR.PATCH`, optionally `-beta.1`), target `main`.
3. Click **Generate release notes**. They are grouped by label (`.github/release.yml`); labels come from the PR titles.
4. **Publish release**.

The **Release** workflow then runs the tests, builds `ModFerry-5.1.0.zip` with `tools/make_release.py --version 5.1.0` and attaches it to the release. If the tests fail, no ZIP is attached; fix the problem and re-run the workflow.

To build a ZIP locally: `python tools/make_release.py` (version from `git describe`) or `--version 5.1.0`.

## Automation overview

| Workflow | When | What |
|---|---|---|
| Tests | every PR, every push to `main`, before a release | unit tests on Windows + Linux, Python 3.11 and 3.13 |
| Release | a release is published | tests, build the ZIP with the tag's version, attach it |
| PR labels | PR opened or title edited | label from the title type (`feat:`, `fix:`, …) |
| Dependabot auto-merge | Dependabot PR for minor/patch updates | enables auto-merge; GitHub merges once the tests are green |
| Wiki sync | changes in `wiki/` reach `main` | copies the pages into the GitHub wiki |

Major dependency updates are grouped separately by Dependabot and always wait for a manual review.
Edit wiki pages in `wiki/` (or via pull request), not in the wiki UI: pages that only exist in the wiki are removed on the next sync.
