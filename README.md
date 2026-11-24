# DaVinci → Frame.io Bridge

[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Security Scan](https://img.shields.io/badge/CI-security--scan-brightgreen.svg)](.github/workflows/security-scan.yml)

Scripts para integrar o **DaVinci Resolve** com o **Frame.io V4** via **Adobe
IMS OAuth 2.0**. Renderiza a timeline atual e envia direto pra uma pasta do
Frame.io, importa comentários como marcadores na timeline, e envia
automaticamente ao terminar um render.

Criado por **[Marrk](https://github.com/)** · Licenciado sob **GPL-3.0-or-later**
(uso livre, modificação livre, créditos obrigatórios, derivados devem ser abertos).

> **English version below** · [Jump to English](#-english)

---

## 🇧🇷 Português

### O que esse projeto faz

| Script | O que faz |
|--------|-----------|
| `Enviar_para_Frame.io.py` | Renderiza a timeline atual com um preset do DaVinci e envia o arquivo direto pra uma pasta do Frame.io (escolhida numa janela). |
| `Importar_comentarios.py` | Busca os comentários de um vídeo no Frame.io e cria marcadores na timeline no tempo exato de cada comentário, com autor, texto e respostas. |
| `Enviar_ao_terminar_render.py` | Trigger que o DaVinci chama ao fim de qualquer render — abre a janela de envio automaticamente. |
| `uploader_gui.py` | Janela Tk standalone (fora do DaVinci) usada pelo trigger acima. |
| `frameio_core.py` | Biblioteca compartilhada: OAuth, HTTP, SSL, navegação Frame.io. |

### Requisitos

- **macOS** (testado) ou **Windows** (adaptações em `install.ps1`)
- **DaVinci Resolve** 18.5+ (Studio ou Free)
- Conta no **Frame.io** vinculada a um **Adobe ID**
- Um **OAuth Web App** no [Adobe Developer Console](https://developer.adobe.com/console/)

### Instalação rápida

```bash
# Clone
git clone https://github.com/SEU-USER/davinci-frameio-bridge.git
cd davinci-frameio-bridge

# Rode o instalador (macOS)
./install.sh

# Ou manualmente:
mkdir -p ~/.resolve_frameio
cp src/frameio_core.py ~/.resolve_frameio/
cp src/uploader_gui.py ~/.resolve_frameio/

# Scripts do menu DaVinci (Workspace → Scripts)
cp "src/Enviar_para_Frame.io.py" "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Deliver/"
cp "src/Importar_comentarios.py" "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/"
cp "src/Enviar_ao_terminar_render.py" "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/"
```

### Primeira configuração

Instruções detalhadas com screenshots em **[docs/setup.md](docs/setup.md)**.

Resumo:

1. No [Adobe Developer Console](https://developer.adobe.com/console/) crie um
   **projeto** → adicione a API **Frame.io** → escolha **OAuth Web App**.
2. Em Redirect URI, use `https://localhost:8765/callback`.
3. Copie **Client ID** e **Client Secret**.
4. No DaVinci: **Workspace → Scripts → Deliver → Enviar para Frame.io**.
5. Clique em **Configurar / Login**, cole as credenciais, clique em **Abrir
   login**, autorize, copie o endereço inteiro da página de erro do navegador
   e cole de volta. Pronto.

### Como usar

#### Render + upload manual
Timeline aberta → `Workspace → Scripts → Deliver → Enviar para Frame.io` →
escolhe Workspace / Projeto / Pasta → **Renderizar e enviar**.

#### Upload automático ao fim de qualquer render
Na aba **Deliver**: `Render Settings → File → Trigger script at: End of render
job` → escolhe `Enviar_ao_terminar_render.py`. Ao terminar o render, a janela
de envio abre sozinha (via Tkinter, fora do DaVinci).

#### Importar comentários do cliente
Timeline aberta → `Workspace → Scripts → Importar_comentarios` → escolhe o
vídeo no Frame.io → **Importar marcadores**. Marcadores vermelhos pros
comentários abertos, verdes pros resolvidos (opcional).

### Segurança

Nenhum segredo neste repositório. Tudo que o OAuth gera (tokens, client
secret) fica **só** no seu Mac, em `~/.resolve_frameio/config.json` com
permissão `0600`. Detalhes em **[SECURITY.md](SECURITY.md)**.

### Licença e créditos

Este projeto é software livre sob **GNU GPL v3.0 ou posterior** — você pode:

- ✅ **Usar** pra o que quiser, inclusive comercialmente
- ✅ **Modificar** o código à vontade
- ✅ **Redistribuir** cópias (modificadas ou não)

Em troca, pela GPL você **tem que**:

- 📝 **Manter os créditos** ao autor original (Marrk) e o aviso de copyright
- 🔓 **Abrir o código** de qualquer trabalho derivado, sob a mesma GPL-3.0
- 📜 **Dizer o que mudou** se você modificar o código antes de redistribuir
- ⚠️ **Não dar garantias** — o software vem "as is"

Texto completo da licença em [LICENSE](LICENSE), resumo de créditos em
[COPYRIGHT](COPYRIGHT).

Precisa de licença comercial fechada (sem abrir o fork)? Abra uma issue
na aba de discussões.

### Troubleshooting

| Problema | Solução |
|----------|---------|
| `Sua conta do Frame.io não está ligada a um Adobe ID` | frame.io → **Account Settings → Profile → Authentication → Adobe → Connect** |
| `HTTP 401` ou `refresh_token` expirado | Abra **Configurar / Login** no DaVinci e refaça o login |
| Scripts não aparecem no menu | Verifique que os `.py` estão em `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/{Deliver,}` e reinicie o DaVinci |
| `ModuleNotFoundError: frameio_core` | `frameio_core.py` precisa estar em `~/.resolve_frameio/` (não na pasta de scripts) |
| Falha SSL | Instale `certifi` no Python que o DaVinci usa, ou deixe o próprio código gerar o `cacert.pem` a partir do Keychain |

---

## 🇬🇧 English

### What this project does

| Script | What it does |
|--------|--------------|
| `Enviar_para_Frame.io.py` | Renders the current timeline with a DaVinci preset and uploads the file to a Frame.io folder (picked in a dialog). |
| `Importar_comentarios.py` | Fetches comments from a Frame.io file and creates timeline markers at the exact timecode, with author, text and replies. |
| `Enviar_ao_terminar_render.py` | Trigger that DaVinci calls when any render finishes — opens the upload dialog automatically. |
| `uploader_gui.py` | Standalone Tk window (outside DaVinci) used by the trigger. |
| `frameio_core.py` | Shared library: OAuth, HTTP, SSL, Frame.io navigation. |

### Requirements

- **macOS** (tested) or **Windows** (see `install.ps1`)
- **DaVinci Resolve** 18.5+ (Studio or Free)
- A **Frame.io** account linked to an **Adobe ID**
- An **OAuth Web App** on the [Adobe Developer Console](https://developer.adobe.com/console/)

### Quick install

```bash
git clone https://github.com/YOUR-USER/davinci-frameio-bridge.git
cd davinci-frameio-bridge
./install.sh
```

### First-time setup

Detailed walkthrough with screenshots: **[docs/setup.md](docs/setup.md)**.

TL;DR:

1. Create an **OAuth Web App** project on the Adobe Developer Console, add the
   **Frame.io** API, set Redirect URI to `https://localhost:8765/callback`.
2. Copy **Client ID** / **Client Secret**.
3. In DaVinci: **Workspace → Scripts → Deliver → Enviar para Frame.io**.
4. Click **Configurar / Login**, paste credentials, click **Open login**,
   authorize, copy the full error-page URL back into the field. Done.

### Usage

- **Manual render + upload:** open timeline → run the Deliver script.
- **Auto-upload on render end:** Deliver tab → *Render Settings → File →
  Trigger script at: End of render job* → pick `Enviar_ao_terminar_render.py`.
- **Import client comments:** open timeline → run `Importar_comentarios` →
  pick the file.

### Security

No secrets in this repo. Everything OAuth generates (tokens, client secret)
stays **only** on your machine at `~/.resolve_frameio/config.json` with
`0600` perms. See **[SECURITY.md](SECURITY.md)**.

### License & credits

This project is free software under the **GNU GPL v3.0 or later**. You can:

- ✅ **Use** it for anything, including commercially
- ✅ **Modify** the source freely
- ✅ **Redistribute** copies (modified or not)

In exchange, the GPL requires you to:

- 📝 **Keep author credit** to Marrk and the copyright notices
- 🔓 **Open the source** of any derived work, under the same GPL-3.0
- 📜 **State what you changed** if you modified it before redistribution
- ⚠️ **Provide no warranty** — the software ships "as is"

Full text in [LICENSE](LICENSE), credit summary in [COPYRIGHT](COPYRIGHT).

Need a commercial / closed-source license (so you don't have to open your
fork)? Open a GitHub Discussion to talk.

---

## Contributing

PRs welcome. Before submitting:

```bash
# Scan for accidental secrets
./scripts/scan-secrets.sh

# Lint
python3 -m pyflakes src/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Disclaimer

Not affiliated with Adobe Inc., Blackmagic Design, or Frame.io.
"Adobe", "Frame.io" and "DaVinci Resolve" are trademarks of their respective
owners.
