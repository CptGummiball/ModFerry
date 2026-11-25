# Batch editing and dependencies

## Selecting files

Tick the checkboxes in the file table (or the header checkbox for all). Section **4 · Batch editing** then applies to the selected files only.

## What a batch action changes

| Action | Effect on selected files |
|---|---|
| Minecraft / Loader / Java / Environment `CF` | Replaces **only that category** of CurseForge versions. Other categories stay. |
| Modrinth settings | Applies only the fields you actually change in the dialog (versions, loaders, environment, upload on/off). The version number stays per file. |
| Dependencies | Replaces the **whole** dependency list. |
| Release + Apply | Sets release / beta / alpha. |
| Reset upload status | Marks the files as not uploaded, so the next **Upload** sends them again. Use this only if you deliberately want a second upload. |

The *Default release type* in section 1 only applies to files added afterwards.

## Excluding a file from one platform

Open the file's **Modrinth** cell and untick *Upload to Modrinth* or *Upload to CurseForge*. The status column then shows `n/a` for that platform.

## Dependencies

Each entry has:

| Field | Used for |
|---|---|
| CurseForge slug | required, e.g. `architectury-api` |
| CF ID | optional numeric project ID, sent as JSON integer |
| Modrinth ID/slug | required when uploading to Modrinth; slugs are resolved to IDs before the upload |
| Type | see below |

| Type | CurseForge | Modrinth |
|---|---|---|
| Required | `requiredDependency` | `required` |
| Optional | `optionalDependency` | `optional` |
| Embedded library | `embeddedLibrary` | `embedded` |
| Incompatible | `incompatible` | `incompatible` |
| Tool | `tool` | ❌ not supported. Remove it or disable Modrinth for this file |
| Include | ❌ not documented for the upload API, blocks the upload | ❌ |

ModFerry never converts an unsupported type into another one silently.
