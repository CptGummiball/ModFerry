# Uploading, dry run and history

## Dry run

**🔍 Dry run** validates everything and shows, per platform, the endpoint and the exact metadata JSON that would be sent for each file, including filled-in changelog placeholders, dependency IDs and server packs. Nothing is uploaded and no network request is made. Use it before every larger release.

## Upload

When you click **⬆ Upload**, ModFerry

1. builds the list per platform; files that were **already uploaded successfully** to a platform are skipped there,
2. validates **both** platforms first, including whether a token is available, so CurseForge is never uploaded when the Modrinth part would fail validation,
3. asks for confirmation with the number of files per platform,
4. uploads to CurseForge, then to Modrinth, one file after another.

Each file creates one file on CurseForge and one version on Modrinth. A failed upload on one platform is not rolled back on the other.

## Status and retries

The status column has one line per platform: `Waiting`, `Uploading`, the new file/version ID with a ↗ link, or the API error. **Retry failed** only resends files whose status is *error* on that platform. To deliberately upload a file again, select it and use **Reset upload status**.

Don't close the browser tab during an upload. ModFerry warns you if you try.

## CurseForge options

- **Publish manually after approval** sets `isMarkedForManualRelease`: after CurseForge's review the file waits for you to publish it.
- Moderation still applies; new files may take a while to appear publicly.

## Modrinth options

- **Version status:** `listed` (public), `unlisted` (reachable via link), `draft` (not visible, good for tests), `archived`.
- **Mark as featured** sets `featured: true`.
- **Show snapshots** adds snapshot versions to the Minecraft list in the Modrinth dialog.

## History

Every successful upload is added to **7 · Upload history** (`data/history.json`, newest first, max. 1000 entries) with time, platform, file, versions, release type and a link:

- Modrinth: direct link to the version.
- CurseForge: direct link to the file if you entered the *project slug*, otherwise a link to the project.

**Clear history** only clears this list; files on the platforms are not touched.
