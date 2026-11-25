# Troubleshooting

Run a **🔍 Dry run** first: most problems show up there with a clear message.

## Start

| Problem | Fix |
|---|---|
| "Python 3.11+ is required" | Install Python from python.org; on Windows make sure the `py` launcher is installed. |
| "The .venv folder uses an older Python" / "ModFerry needs Python 3.11 or newer" | ModFerry was set up with an older Python before. Install Python 3.11+, delete the `.venv` folder and start again. |
| Installation of dependencies fails | Check your internet connection / proxy and start again. |
| Port already in use | Another ModFerry is running, or use a different port: [[Configuration]]. |
| "Only local access is allowed" | Open `http://127.0.0.1:8765` or `http://localhost:8765`, not your computer's network name. |

## CurseForge

| Message | Meaning / fix |
|---|---|
| HTTP 401 / 403 | Token invalid or not allowed for this project. Create a new token and check the project ID. |
| "Could not load CurseForge versions" | Token missing/wrong or CurseForge unreachable. |
| HTTP 400 (metadata rejected) | Read the error text in the status column. Common causes: no Minecraft version selected, a version/loader combination CurseForge doesn't accept for this project, or an unknown dependency slug. Compare with the dry run. |
| "Ambiguous: 26.2 exists 2× on CurseForge" | The name exists in several version groups. Open the picker, compare category and ID, choose one. |
| Upload OK but file not visible | CurseForge moderates uploads; maybe *publish manually after approval* was on. |

## Modrinth

| Message | Meaning / fix |
|---|---|
| HTTP 401 | Token missing the *Create versions* scope or invalid. |
| "Could not verify Modrinth project ID" | Project slug/ID or a dependency's Modrinth ID doesn't exist, or the token can't see the project. |
| Version number already exists | Modrinth needs a unique `version_number` per project. Edit it in the Modrinth cell. |
| "Modrinth loaders … not valid for this project type" | e.g. resource packs must use `minecraft`, data packs `datapack`. |
| "Tool is not a supported Modrinth dependency" | Remove the dependency or disable Modrinth for the file. |

## Files

| Problem | Fix |
|---|---|
| "A file to upload no longer exists" | ModFerry was restarted; the cache is cleared on start. Remove and re-add the file. |
| Pack format newer than the built-in table | Choose the Minecraft versions manually, or update ModFerry. |
| Wrong Java version | The value is the bytecode minimum. Pick the Java version you actually support. |

## Still stuck?

Open an [issue](https://github.com/CptGummiball/ModFerry/issues/new/choose) with the ModFerry version, OS, project type and the error message. **Never post your tokens.**
