## What does this change?

<!-- Short description. Link the issue: "Closes #123" -->

## Type

- [ ] Bug fix
- [ ] New feature
- [ ] Pack format table update
- [ ] Translation
- [ ] Documentation
- [ ] Refactoring / maintenance

## Checklist

- [ ] `python -m unittest discover -s tests -v` passes
- [ ] New logic has tests (detection, validation, payloads)
- [ ] New UI texts exist in **both** `static/i18n/de.json` and `static/i18n/en.json` (and backend texts in `messages.py`)
- [ ] I tested it in the browser (`python app.py`), with `MODFERRY_DATA` pointing to a scratch folder
- [ ] No tokens, personal data or files from `data/` are included
- [ ] The PR title follows the `type: description` style (`feat:`, `fix:`, `docs:`, `i18n:`, `pack-format:`). It becomes the line in the release notes and sets the label automatically.

## Screenshots / dry-run output

<!-- For UI changes or changed upload metadata. Remove tokens! -->
