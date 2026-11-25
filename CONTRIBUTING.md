# Contributing to ModFerry

Thanks for helping! Bug reports, ideas, translations and pull requests are all welcome.

## Ways to help

- **Report a bug**: use the [bug report form](https://github.com/CptGummiball/ModFerry/issues/new/choose). Include the dry-run output if the problem is about uploads, and never paste tokens.
- **Suggest a feature**: open a feature request and describe your workflow first, then the solution.
- **Ask a question**: use [Discussions → Q&A](https://github.com/CptGummiball/ModFerry/discussions), not issues.
- **New Minecraft version**: the pack format table needs a new row; use the "New Minecraft version" form or send a small PR.
- **Translations**: fix texts or add a language (see the [Development](https://github.com/CptGummiball/ModFerry/wiki/Development) wiki page).
- **Security issues**: report them privately, see [SECURITY.md](SECURITY.md).

## Development setup

```bash
git clone https://github.com/<you>/ModFerry.git
cd ModFerry
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Run the app against a scratch data folder so your real tokens and profiles stay untouched:

```bash
# Linux/macOS
MODFERRY_DATA=/tmp/modferry-dev python app.py
# Windows PowerShell
$env:MODFERRY_DATA = "$env:TEMP\modferry-dev"; python app.py
```

There is no build step: the frontend is plain HTML/CSS/JS in `static/`.

## Pull request workflow

1. **Open or find an issue first** for anything bigger than a typo, so we can agree on the approach.
2. Fork the repo and create a branch from `main`: `fix/modrinth-env`, `feat/server-pack-names`, `docs/wiki-typo` …
3. Keep the PR focused on one thing. Small PRs get reviewed faster.
4. Fill in the PR template checklist.
5. CI must be green (tests on Windows + Linux, Python 3.10 and 3.13).
6. PRs are merged with **squash merge**. The PR title becomes the commit message, so please write it like one (see below).

## Commit / PR title style

The PR title matters: it becomes the line in the release notes, and its type sets the label automatically
(`feat` → enhancement, `fix` → bug, `docs` → documentation, `i18n` → translation, `pack-format` → pack-format).
Short and imperative:

```
fix: keep server pack status when main upload succeeded
feat: add shader pack loader detection
docs: explain profile pattern matching
i18n: improve German upload messages
```

## Code guidelines

- **Never guess metadata.** If a value is not stated unambiguously in the file, leave it empty and show a warning. This is ModFerry's core rule.
- **Don't send what the APIs don't document.** Unsupported values must be rejected with a clear message, never silently converted.
- **Every user-facing text in both languages**: `static/i18n/*.json` for the UI, `messages.py` for backend errors.
- **Tokens never leave the token store**: not in profiles, history, logs, error messages or the browser.
- Python: standard library first; new dependencies need a good reason.
- Add tests for detection, validation and payload changes (`tests/`). Tests must not use the network.

## License

By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md).
