# Changelog

All notable changes to ModFerry are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [5.0.0] (2026-11-25)

First public release under the name **ModFerry** (previously "CurseForge Batch Uploader").

### Added
- Project types: resource packs, data packs, shader packs and modpacks in addition to mods.
- Minecraft versions for resource/data packs from `pack.mcmeta` (`pack_format`, `supported_formats`, `min_format`/`max_format`).
- Modpacks: CurseForge `.zip` (`manifest.json`) and Modrinth `.mrpack` (`modrinth.index.json`) are detected and uploaded separately; optional CurseForge server pack as additional file (`parentFileID`).
- English UI next to German, chosen from the browser language; backend messages are translated too.
- Dry run that shows the exact metadata per platform.
- Upload history (`data/history.json`) with links to the uploaded files.
- Changelog placeholders `{version}`, `{mc}`, `{loader}`, `{name}`, `{file}`, `{date}` and CHANGELOG.md import.
- Modrinth version status (listed/unlisted/draft/archived), featured flag and snapshot versions.
- Mod version detection from mod metadata (incl. `${file.jarVersion}` → `Implementation-Version`).
- Proper dialogs for Modrinth settings and per-file changelogs (no more `prompt()` chains).
- `MODFERRY_PORT` and `MODFERRY_DATA` environment variables.

### Changed
- Profiles match files by pattern, so a new mod version reuses the settings of the previous one.
- Upload status is tracked per platform; "Upload" skips files that already succeeded, "Retry failed" only resends failures.
- Both platforms are validated (incl. token presence) before anything is uploaded.
- Frontend split into readable `index.html`, `style.css`, `app.js` and translation files.
- Maximum file size raised to 500 MB.

### Fixed
- Cached files in `data/files/` were never deleted after a restart; they are now cleaned on start.
- Retrying after a mixed result (one platform failed, the other succeeded) could upload a file twice.
- Duplicate Modrinth version numbers are rejected before uploading.
- Profile deletion now writes atomically.

## [4.x] and earlier

Internal versions: CurseForge batch uploads, Modrinth support, dependencies, encrypted token store, metadata detection for mods.
