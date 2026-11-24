# Security Policy

## Overview

This project integrates DaVinci Resolve with Frame.io via Adobe IMS OAuth 2.0.
Because it handles **OAuth tokens** and **client secrets**, security is treated
as a first-class concern.

## Where secrets live

Every secret used by this tool lives **only** inside each user's own machine,
at:

```
~/.resolve_frameio/config.json
```

That file is created at runtime, has permission mode `0600` (readable only by
the owner), and is explicitly ignored by [`.gitignore`](./.gitignore).

| What                | Where                                   | Shipped in repo? |
|---------------------|-----------------------------------------|------------------|
| `client_id`         | `~/.resolve_frameio/config.json`        | ❌ Never         |
| `client_secret`     | `~/.resolve_frameio/config.json`        | ❌ Never         |
| `access_token`      | `~/.resolve_frameio/config.json`        | ❌ Never         |
| `refresh_token`     | `~/.resolve_frameio/config.json`        | ❌ Never         |
| CA bundle           | `~/.resolve_frameio/cacert.pem`         | ❌ Never         |
| Logs                | `~/.resolve_frameio/trigger.log`, etc.  | ❌ Never         |

## What this project does **not** do

- ❌ **Does not** bundle any credentials.
- ❌ **Does not** send telemetry.
- ❌ **Does not** phone home.
- ❌ **Does not** store secrets in environment variables used by other apps.
- ❌ **Does not** upload the config file anywhere.
- ❌ **Does not** log token contents (only timestamps and error metadata).

## Network traffic

Outbound HTTPS only, and only to these hosts:

| Host                           | Purpose                                 |
|--------------------------------|-----------------------------------------|
| `ims-na1.adobelogin.com`       | Adobe IMS OAuth (login + token refresh) |
| `api.frame.io`                 | Frame.io V4 REST API                    |
| Frame.io S3 upload URLs        | Chunked uploads (short-lived, signed)   |

TLS verification is always enabled. The code tries, in order:
`certifi` → macOS keychain export → system default context.

## Reporting a vulnerability

If you believe you've found a security issue, please **do not** open a public
issue. Instead, open a GitHub Security Advisory
([Security tab → Advisories → New draft security advisory](../../security/advisories/new)),
or email the maintainer directly through the address on the GitHub profile.

You can expect:
- An acknowledgement within 72 hours
- A fix or mitigation plan within 14 days for critical issues
- Credit in the release notes (if desired)

## For contributors

Before opening a PR, **please** run:

```bash
# Simple grep sweep for anything that looks like a credential
./scripts/scan-secrets.sh
```

Never paste real `client_id` / `client_secret` / tokens in:
- Commit messages
- Issues
- Pull requests
- Screenshots
- Debug logs attached to issues

If you accidentally commit a real secret:
1. **Rotate it immediately** at [Adobe Developer Console](https://developer.adobe.com/console/).
2. Open an issue so maintainers can purge the git history (`git filter-repo`).
