# Configuration

ModFerry needs no configuration file. Two optional environment variables exist:

| Variable | Default | Purpose |
|---|---|---|
| `MODFERRY_PORT` | `8765` | Port of the local web server |
| `MODFERRY_DATA` | `./data` | Folder for profiles, history, tokens and the file cache |

Windows (PowerShell):

```powershell
$env:MODFERRY_PORT = "8800"; .\start-windows.bat
```

Linux / macOS:

```bash
MODFERRY_PORT=8800 ./start-linux.sh
```

## The data folder

| Path | Content |
|---|---|
| `data/profiles.json` | your profiles (no tokens) |
| `data/history.json` | upload history |
| `data/tokens.enc` | encrypted tokens |
| `data/files/` | copies of the files you added, only while the app runs |

Files in `data/files/` are deleted when you remove them from the table and on every start of ModFerry. Back up `profiles.json` (and `history.json` if you like) when moving to a new computer; `tokens.enc` only works on the same Windows account or with your master password.

## Limits

- up to 100 files per upload batch
- max. 500 MB per file
- CurseForge version list is cached for one hour per token
