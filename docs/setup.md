# Setup — Primeira configuração / First-time setup

Este guia explica o setup completo: criar o OAuth app no Adobe, instalar os
scripts no DaVinci, e completar o primeiro login.

> English version below.

---

## 🇧🇷 Português

### Pré-requisitos

| Item | Detalhe |
|------|---------|
| macOS ou Windows | Testado em macOS 13+; o instalador `.ps1` cobre Windows |
| DaVinci Resolve | 18.5 ou superior (Studio ou Free) |
| Conta Frame.io | Já migrada e vinculada a um Adobe ID (`frame.io → Account Settings → Profile → Authentication → Adobe → Connect`) |
| Navegador | Qualquer — o fluxo OAuth abre no padrão do sistema |

### Passo 1 — Criar o OAuth Web App no Adobe

1. Abra o [Adobe Developer Console](https://developer.adobe.com/console/) com
   a mesma conta Adobe vinculada ao Frame.io.
2. Clique em **Create new project** (ou abra um existente).
3. **Add API** → procure por **Frame.io** → **Next**.
4. Escolha **OAuth Web App** → **Next**.
5. Em **Redirect URI** adicione exatamente:
   ```
   https://localhost:8765/callback
   ```
6. Em **Redirect URI pattern** use:
   ```
   https://localhost:8765/callback.*
   ```
7. Selecione os scopes que o projeto pede
   (`openid`, `email`, `profile`, `offline_access`, `additional_info.roles`).
8. **Save configured API**.

Na tela do OAuth Web App, anote:
- **Client ID** (hexadecimal, ~32 chars)
- **Client Secret** (aparece com o botão "Retrieve client secret")

> ⚠️ **Nunca** cometa esses valores no git nem cole em issues/PRs.

### Passo 2 — Instalar os scripts

```bash
git clone https://github.com/SEU-USER/davinci-frameio-bridge.git
cd davinci-frameio-bridge
./install.sh
```

O instalador cria `~/.resolve_frameio/` e copia:

- `~/.resolve_frameio/frameio_core.py`
- `~/.resolve_frameio/uploader_gui.py`
- `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Deliver/Enviar_para_Frame.io.py`
- `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Importar_comentarios.py`
- `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Enviar_ao_terminar_render.py`

### Passo 3 — Primeiro login

1. Abra o DaVinci Resolve e carregue qualquer projeto com uma timeline.
2. Menu: **Workspace → Scripts → Deliver → Enviar para Frame.io**.
3. Clique em **Configurar / Login**.
4. Cole o **Client ID** e o **Client Secret** nos campos.
5. Clique em **2. Abrir login do Frame.io no navegador**.
6. Entre com sua conta Adobe, autorize o app.
7. O navegador mostra uma página de erro (é esperado — ninguém está escutando
   em `localhost:8765`). Copie o **endereço inteiro** da barra do navegador.
8. Cole o endereço no campo da janela do DaVinci.
9. **Concluir login** — pronto, status mostra "Conectado ✔".

A partir daqui:
- Tokens ficam em `~/.resolve_frameio/config.json` (mode 600).
- O refresh token é trocado automaticamente quando o access token expira.
- Você não precisa repetir o login salvo se revogar o app no Adobe ou
  apagar o `config.json`.

### Passo 4 — Opcional: auto-upload ao fim de qualquer render

1. No DaVinci, aba **Deliver**.
2. Em **Render Settings → File → Trigger script at**, escolha
   **End of render job**.
3. Aponte para `Enviar_ao_terminar_render.py`.
4. Daí em diante, cada render termina abrindo a janela de upload sozinha.

---

## 🇬🇧 English

### Prerequisites

| Item | Detail |
|------|--------|
| macOS or Windows | Tested on macOS 13+; `.ps1` installer covers Windows |
| DaVinci Resolve | 18.5+ (Studio or Free) |
| Frame.io account | Migrated and linked to an Adobe ID |
| Browser | Any — OAuth flow opens the system default |

### Step 1 — Create the OAuth Web App on Adobe

Same as the Portuguese section above. In short:

Adobe Developer Console → new project → Add API → **Frame.io** →
**OAuth Web App** → Redirect URI `https://localhost:8765/callback`
→ pattern `https://localhost:8765/callback.*` → pick the scopes →
Save → grab **Client ID** and **Client Secret**.

### Step 2 — Install

```bash
git clone https://github.com/YOUR-USER/davinci-frameio-bridge.git
cd davinci-frameio-bridge
./install.sh
```

### Step 3 — First login

1. Open DaVinci, load any project with a timeline.
2. **Workspace → Scripts → Deliver → Enviar para Frame.io**.
3. **Configurar / Login**, paste Client ID + Secret.
4. **Open login in browser**, authorize.
5. Copy the full error-page URL and paste it back in the dialog.
6. **Concluir login** → status reads "Conectado ✔".

Tokens are stored at `~/.resolve_frameio/config.json` (mode 600). Refresh is
automatic.

### Step 4 — Optional: auto-upload on render end

Deliver tab → Render Settings → File → Trigger script at **End of render
job** → pick `Enviar_ao_terminar_render.py`.
