# Changelogs

## Shared and individual changelogs

The text in section **5 · Markdown changelog** is used for all files. To give one file its own text, click its **Changelog** button and tick *Use an individual changelog for this file*.

Changelogs are sent as Markdown to both platforms (`changelogType: markdown` on CurseForge). The preview is rendered locally with Python-Markdown and sanitized with bleach; the platforms may style it slightly differently.

## Placeholders

These are replaced per file when uploading (and in the dry run and preview):

| Placeholder | Value |
|---|---|
| `{version}` | mod / pack version read from the file (or the Modrinth version number) |
| `{mc}` | Minecraft versions of the file (CurseForge names, otherwise Modrinth versions) |
| `{loader}` | loaders (CurseForge names, otherwise Modrinth loaders) |
| `{name}` | display name |
| `{file}` | file name |
| `{date}` | today, `YYYY-MM-DD` |

Example:

```markdown
## {version}
- Fixed a crash on **{loader}** ({mc})
```

becomes for `qnet-1.1.4+mc1.21.1-fabric.jar`:

```markdown
## 1.1.4+mc1.21.1
- Fixed a crash on **Fabric** (1.21.1)
```

The preview header shows which file's values are used (the first selected file, otherwise the first file).

## Importing CHANGELOG.md

Click **Import CHANGELOG.md …** and choose a `.md` / `.txt` file.

With **newest section only** ticked, ModFerry takes the content below the first `## ` heading that is not empty, so an empty `## [Unreleased]` block is skipped. The heading line itself is not included. Untick it to import the whole file.
