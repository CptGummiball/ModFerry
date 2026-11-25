# Security policy

ModFerry handles CurseForge and Modrinth API tokens, so security reports are taken seriously.

## Supported versions

Only the latest release receives security fixes.

| Version | Supported |
|---|---|
| 5.x (latest) | ✅ |
| < 5.0 | ❌ |

## Reporting a vulnerability

**Please do not open a public issue.** Use GitHub's private reporting instead:

👉 [Report a vulnerability](https://github.com/CptGummiball/ModFerry/security/advisories/new)

Please include:

- the ModFerry version and operating system
- what an attacker could do and under which conditions (e.g. a malicious website, a crafted JAR/ZIP, local access)
- steps to reproduce or a proof of concept

You can expect a first answer within a few days. Once a fix is released, the advisory is published and you are credited unless you prefer otherwise.

## Scope

In scope, for example:

- token leakage (files, logs, browser, error messages)
- bypassing the localhost / `Host` / `Origin` protection (DNS rebinding, CSRF)
- crafted files (JAR, ZIP, `.mrpack`) that cause code execution, path traversal or excessive resource use
- HTML/JS injection through the Markdown preview or file metadata

Out of scope:

- running ModFerry on a network-reachable interface against the documentation's advice
- attackers who already control your unlocked user account
- vulnerabilities in CurseForge or Modrinth themselves; please report those to the platforms
