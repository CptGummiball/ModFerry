# Profiles

A profile stores the settings of one project so the next release takes seconds.

## What is saved

- project type, CurseForge project ID and slug, Modrinth project
- target platforms, default release type, "publish manually", Modrinth status / featured / snapshots
- the shared changelog
- per file: display name, CurseForge versions, Modrinth versions/loaders/version number/environment, dependencies, individual changelog, release type, platform switches

**Not saved:** API tokens and the files themselves. Profiles are stored in `data/profiles.json`.

## Matching files of a new release

Profiles match files **by pattern**: the detected mod version is replaced with a placeholder. A profile saved with

```
qnet-1.1.4+mc1.21.1-fabric.jar   (version 1.1.4+mc1.21.1)
```

matches `qnet-1.1.5+mc1.21.1-fabric.jar` (version 1.1.5+mc1.21.1). The display name and Modrinth version number are updated the same way, e.g. `QNet 1.1.4+mc1.21.1 (Fabric)` → `QNet 1.1.5+mc1.21.1 (Fabric)`.

An exact file name match always wins. Files without a detectable version are only matched by exact name.

## Workflow

1. Choose the profile **before** adding files. New files are then matched immediately.
2. Or choose it afterwards: all files in the table are matched and the notice tells you how many.
3. After changes, click **Save** and keep the same name to update the profile.

Choosing a profile of another project type switches the type (and asks before clearing the list).
