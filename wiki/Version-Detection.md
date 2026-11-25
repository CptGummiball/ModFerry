# Version detection

ModFerry fills in as much as it can from the files themselves, but it **never guesses**. If a value is not stated unambiguously, it is left empty and marked with ⚠ so you decide.

## Mods (`.jar`)

| Source | Read |
|---|---|
| `fabric.mod.json` | loader `fabric`, mod `version`, `depends.minecraft` |
| `quilt.mod.json` | loader `quilt`, `quilt_loader.version`, Minecraft dependency |
| `META-INF/neoforge.mods.toml` | loader `neoforge`, `[[mods]] version`, Minecraft `versionRange` |
| `META-INF/mods.toml` | loader `forge`, same fields |
| `META-INF/MANIFEST.MF` | `Implementation-Version` when the toml says `${file.jarVersion}` |
| `.class` files | highest class file version → minimum Java (e.g. 65 → Java 21) |
| file name | fallback for Minecraft version and loader |

**Only exact Minecraft versions are used.** `"1.21.1"`, `"=1.21.1"` or `"[1.21.1]"` are taken; ranges like `>=1.21`, `[26.2,26.3)` or `[1.21,)` are not, because they may mean several versions. In file names, the new year-based versions (`26.2`) win over separate `1.x` numbers so a mod version `1.1.2` is not mistaken for Minecraft 1.1.2.

The Java value is the bytecode **minimum**; your mod may still need a newer runtime.

## Resource packs and data packs (`.zip`)

`pack.mcmeta` is read in this order:

1. `min_format` + `max_format` (since 1.21.9; integers or `[major, minor]`)
2. `supported_formats` (integer, `[min, max]` or `{min_inclusive, max_inclusive}`)
3. `pack_format`

The declared range is mapped to Minecraft **release** versions with the built-in table from the [Minecraft Wiki](https://minecraft.wiki/w/Pack_format) (`pack_formats.py`). Resource packs and data packs use different numbers. Example: a resource pack with `pack_format: 34` and `supported_formats: [34, 46]` gets 1.21 to 1.21.4.

If the format is newer than the table (a Minecraft version released after this ModFerry version), you get a warning and choose manually. Updating the table is a one-line change (see [[Development]]).

ModFerry also warns if a data pack has no `data/` folder or a resource pack has no `assets/` folder.

## Modpacks

| File | Read |
|---|---|
| CurseForge `.zip` → `manifest.json` | `minecraft.version`, primary `modLoaders[].id` (e.g. `neoforge-21.1.1` → neoforge), `version` |
| Modrinth `.mrpack` → `modrinth.index.json` | `dependencies.minecraft`, loader key (`fabric-loader`, `quilt-loader`, `forge`, `neoforge`), `versionId` |

## From detection to platform values

- **CurseForge:** a detected version is only selected if exactly **one** CurseForge entry has that name. If the name exists in several version groups, you get "Ambiguous …, please pick manually" and the picker shows category and API ID. Loader and Java are matched the same way.
- **Modrinth:** Minecraft versions and loaders are copied directly. The **version number** is built from the mod version plus the missing parts, e.g. `1.4.2` + fabric + 1.21.1 → `1.4.2+fabric-1.21.1`, or `1.4.2+mc1.21.1` → `1.4.2+mc1.21.1-fabric`. It must be unique per Modrinth project; duplicates are rejected before uploading.
