# Project types

A CurseForge or Modrinth project has exactly one type, so ModFerry works with one type at a time. Choose it at the top; switching clears the file list.

| Type | Files | CurseForge fields | Modrinth loaders | Detected from |
|---|---|---|---|---|
| 🧩 Mod | `.jar` | Minecraft, loader, Java, environment | detected loader (fabric, forge, neoforge, quilt, …) | mod metadata, bytecode |
| 🎨 Resource pack | `.zip` | Minecraft | `minecraft` (fixed) | `pack.mcmeta` |
| 📜 Data pack | `.zip` | Minecraft | `datapack` (fixed) | `pack.mcmeta` |
| ✨ Shader pack | `.zip` | Minecraft | `iris`, `optifine`, `canvas`, `vanilla` (you choose) | file name only |
| 📦 Modpack | `.zip` → CurseForge, `.mrpack` → Modrinth | Minecraft, loader | `fabric`, `forge`, `neoforge`, `quilt` | `manifest.json` / `modrinth.index.json` |

The Modrinth loader names come from Modrinth's official loader tags (`supported_project_types`). The Modrinth *environment* field is only sent for mods and modpacks.

## Modpacks

CurseForge and Modrinth use **different modpack formats**, so the uploads run separately:

- A **`.zip` containing `manifest.json`** (CurseForge format) is only uploaded to CurseForge.
- A **`.mrpack` containing `modrinth.index.json`** is only uploaded to Modrinth.

Add both files of a release; the table shows "not for Modrinth" / "n/a" for the other platform. ModFerry reads the Minecraft version, the loader and the pack version from each file.

### Server packs (CurseForge)

CurseForge rows of a modpack have a **+ Server pack** link. The chosen `.zip` is uploaded right after the main file as an **additional file** (`parentFileID`). If the server pack fails, the main file stays uploaded and the status shows a warning. The main file is never uploaded twice.

## Shader packs

Shader packs have no standard metadata, so ModFerry only uses Minecraft versions found in the file name. Pick the versions and the Modrinth loader yourself.
