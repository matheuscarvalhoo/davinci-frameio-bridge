# Contributing

Thanks for taking the time to contribute! 🎉

By submitting a pull request you confirm that your contribution is licensed
under the **GNU GPL v3.0-or-later** (same as the rest of the project), and
that you keep the credit to the original author (Marrk) in any derived work.

## Before you start

1. **Fork** the repo and create a branch: `git checkout -b feat/my-feature`.
2. Make sure you have **DaVinci Resolve 18.5+** and a dev account on
   [Adobe Developer Console](https://developer.adobe.com/console/) for testing.
3. Create a **sandbox** OAuth app on Adobe (don't use your personal one for
   dev work).

## Golden rules

1. **Never commit credentials.** Run `./scripts/scan-secrets.sh` before every
   commit. CI will fail a PR that includes anything looking like a token or a
   client secret.
2. **Never log token contents.** Log error codes, HTTP status, timestamps —
   not the bearer string.
3. **Keep UI strings bilingual** where easy. User-facing text is currently in
   PT-BR; new messages should keep the same tone.
4. **Keep the surface area small.** This is a glue project between three
   products. New features that don't fit the glue role probably belong in a
   separate project.

## Dev loop

```bash
# Install editable
./install.sh

# Edit under src/, re-run install.sh (or just cp the changed file)
# Reopen DaVinci so it picks up the script
```

## Testing checklist

Before opening a PR, run through this on your machine:

- [ ] Fresh login works (`Configurar / Login`)
- [ ] Token refresh works after waiting past `expires_at`
- [ ] A timeline renders and uploads to a folder of your choice
- [ ] Creating a new folder inside Frame.io works
- [ ] Importing comments creates timeline markers at correct timecodes
- [ ] Nothing in `~/.resolve_frameio/config.json` leaks to stdout or logs

## Pull request format

- **Title:** `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`
- **Body:** 2–5 lines explaining *what* and *why*. Screenshots for UI changes.
- **Linked issue:** `Closes #123` when applicable.

## Code style

- Python 3.9+
- Follow the style already in `src/frameio_core.py` (plain stdlib, small
  functions, no heavy dependencies)
- No `requirements.txt` additions without justification — this tool has to
  work with the Python shipped inside DaVinci.

## Reporting bugs

Open an issue with:
- OS + DaVinci version
- Steps to reproduce
- Expected vs actual
- Any traceback (with tokens **redacted**)
