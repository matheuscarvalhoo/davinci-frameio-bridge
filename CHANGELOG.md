# Changelog

All notable changes to this project will be documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-24

### Added

- Initial public release.
- `Enviar_para_Frame.io.py` — render current timeline with a DaVinci preset
  and upload to a Frame.io folder.
- `Importar_comentarios.py` — fetch Frame.io comments and create timeline
  markers at the exact timecodes.
- `Enviar_ao_terminar_render.py` — end-of-render trigger that launches the
  standalone uploader.
- `uploader_gui.py` — Tk-based standalone upload window.
- `frameio_core.py` — shared library for Adobe IMS OAuth, HTTP with
  cert-store fallback, and Frame.io V4 navigation.
- Installers for macOS (`install.sh`) and Windows (`install.ps1`).
- Full `SECURITY.md`, bilingual `README.md`, and GitHub Actions secret-scan
  workflow.

### Security

- Secrets never leave `~/.resolve_frameio/config.json` (chmod `0600`).
- `.gitignore` blocks every path that could carry credentials.
- Pre-commit grep-based secret scanner in `scripts/scan-secrets.sh`.

### License

- Released under **GNU GPL v3.0-or-later**. See [LICENSE](LICENSE) and
  [COPYRIGHT](COPYRIGHT).
