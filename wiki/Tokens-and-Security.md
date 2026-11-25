# Tokens and security

## Getting tokens

| Platform | Where | Notes |
|---|---|---|
| CurseForge | [authors.curseforge.com → API tokens](https://authors.curseforge.com/account/api-tokens) | Author upload API token. Your account must be allowed to upload to the project. |
| Modrinth | [modrinth.com/settings/pats](https://modrinth.com/settings/pats) | Personal access token with the scope **Create versions**. Read access to projects is used to resolve slugs. |

Treat tokens like passwords. Revoke a token on the platform if it may have leaked.

## Token store

Paste the tokens and click **Save tokens encrypted**. Empty token fields always mean "use the saved token".

| OS | Encryption | Unlocking |
|---|---|---|
| Windows | **DPAPI**, bound to your Windows user account | automatic |
| Linux / macOS | **Fernet** (AES) with a key from your master password (PBKDF2-SHA256, 600 000 iterations) | enter the master password (min. 12 characters) once per start |

The encrypted file is `data/tokens.enc`. It cannot be decrypted on another Windows account/PC or without the master password. There is **no password recovery**. If you forget it, delete `tokens.enc` and save the tokens again.

Anyone with access to your *unlocked* user account or the running ModFerry can use the saved tokens. Delete them with **Delete CF token / Delete MR token** if needed.

Tokens are **never** written to profiles, the history, the browser storage or log output.

## What the app protects against

- The server only listens on `127.0.0.1`.
- Requests with a foreign `Host` header are rejected (DNS rebinding).
- Write requests with a foreign `Origin` are rejected, so other websites cannot control ModFerry (CSRF).
- The Markdown preview is sanitized; scripts and `javascript:` links are removed.

**Do not expose ModFerry to a network or the internet.** It has no user accounts and is meant for one person on one computer.

## What leaves your computer

Only the files and metadata you upload, sent directly to the CurseForge and Modrinth APIs. ModFerry has no telemetry and no server of its own.
