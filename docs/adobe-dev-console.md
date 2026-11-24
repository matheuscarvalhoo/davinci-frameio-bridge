# Adobe Developer Console — step by step

This project depends on an **OAuth Web App** that *you* own on the Adobe
Developer Console. We don't ship credentials — each user creates their own.

## Why?

Frame.io is an Adobe product. The V4 REST API accepts a bearer token minted
by Adobe IMS (the Adobe identity system). To mint one you need:

- A `client_id` + `client_secret` from an Adobe "Project" you created
- A redirect URI whitelisted in that project
- Your personal Adobe account to actually authorize access

Since every user authenticates with their own account, every user needs their
own OAuth app. This also means **you have full control** over revoking access
at any time, and nothing in this repo can access your Frame.io data.

## Step-by-step

### 1. Open the Console

<https://developer.adobe.com/console/>

Sign in with the Adobe account that your Frame.io is linked to.

> If Frame.io isn't linked yet: open frame.io → Account Settings → Profile →
> Authentication → Adobe → Connect.

### 2. Create a project

- Click **Create new project** (or open any existing one).
- Rename it to something descriptive, e.g. *"DaVinci Bridge"*.

### 3. Add the Frame.io API

- Inside the project, click **Add API**.
- Search for **Frame.io**.
- Click **Next**.

### 4. Choose the credential type

Pick **OAuth Web App** (not Server-to-Server, not Single Page, not Native).

Reasons:
- The scripts run on your workstation, not a server — so no S2S.
- We need a `refresh_token` so you don't have to re-login constantly, which
  rules out SPA.
- Native OAuth works too but requires more setup; Web App is simplest.

### 5. Redirect URI

Add **exactly** this URL:

```
https://localhost:8765/callback
```

And the matching pattern:

```
https://localhost:8765/callback.*
```

Nothing listens on that port — we only read the `code` query parameter from
the error page the browser shows after Adobe redirects. This is a standard
pattern for installed-app OAuth flows.

### 6. Scopes

Select the ones the scripts need:

- `openid`
- `email`
- `profile`
- `offline_access` ← **critical**, enables `refresh_token`
- `additional_info.roles`

### 7. Save and grab credentials

- Click **Save configured API**.
- You land on the credential detail page.
- Copy the **Client ID** (hex, usually 32 chars).
- Click **Retrieve client secret** and copy that too.

### 8. Done

Head back to the [setup guide](./setup.md#passo-3--primeiro-login) and paste
the two values into the DaVinci dialog.

## Revoking access later

To invalidate every token the scripts hold:

1. Adobe Developer Console → your project → the OAuth Web App credential.
2. Click **Retrieve client secret** → **Reset client secret**.
3. Delete `~/.resolve_frameio/config.json` on your machine.

Next time you open the script you'll be prompted to log in again.
