# -*- coding: utf-8 -*-
#
# davinci-frameio-bridge
# Copyright (C) 2026 Marrk
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.

"""
frameio_core
============

Shared helpers for the DaVinci → Frame.io scripts (v2).

Lives at ``~/.resolve_frameio/frameio_core.py`` on the user's machine so it
is NOT picked up by the DaVinci Scripts menu scanner.

Responsibilities
----------------
* Adobe IMS OAuth 2.0 (Web App flow) — login, refresh, token storage.
* HTTPS with a sensible SSL context (certifi → macOS keychain → stdlib).
* Frame.io V4 REST API navigation (accounts, workspaces, projects, folders,
  files, comments) and chunked file uploads.
* Small Qt/Fusion UI helpers reused by every entry-point script.

Security
--------
No secrets live in this file. Everything the OAuth flow produces is written to
``~/.resolve_frameio/config.json`` with mode ``0600``.
See ``SECURITY.md`` at the repo root.
"""

import os
import json
import time
import ssl
import secrets
import mimetypes
import webbrowser
import subprocess  # nosec B404 — only used to call /usr/bin/security with hardcoded args
import urllib.parse
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
API = "https://api.frame.io/v4"
IMS = "https://ims-na1.adobelogin.com/ims"

# Scopes required by Frame.io V4 as of writing. See
# https://developer.adobe.com/developer-console/docs/guides/authentication/OAuth/Scopes/
SCOPES = "openid email profile offline_access additional_info.roles"

# The OAuth Web App on Adobe Developer Console must whitelist this URL (or
# whichever value the user sets in the config dialog).
DEFAULT_REDIRECT = "https://localhost:8765/callback"

USER_AGENT = "DaVinciFrameioBridge/1.0 (+https://github.com)"

CONFIG_DIR = os.path.expanduser("~/.resolve_frameio")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
RENDER_DIR = os.path.expanduser("~/Movies/Frame.io Uploads")


# ---------------------------------------------------------------------------
# SSL context
# ---------------------------------------------------------------------------
def _ssl_context():
    """
    Build an SSL context that works from inside the Python interpreter that
    ships with DaVinci Resolve.

    That interpreter frequently has no CA bundle configured. We try, in order:

    1. ``certifi`` (if the user installed it into the DaVinci Python).
    2. A cached ``cacert.pem`` extracted from the macOS Keychain. Refreshed
       every 30 days.
    3. ``ssl.create_default_context()`` — last-resort stdlib default.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass  # nosec B110 — certifi is optional; we fall through to the next strategy

    pem = os.path.join(CONFIG_DIR, "cacert.pem")
    try:
        if not os.path.isfile(pem) or time.time() - os.path.getmtime(pem) > 30 * 86400:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            certs = b""
            for kc in (
                "/System/Library/Keychains/SystemRootCertificates.keychain",
                "/Library/Keychains/System.keychain",
            ):
                if os.path.exists(kc):
                    certs += subprocess.run(  # nosec B603 — fixed path, hardcoded args
                        ["/usr/bin/security", "find-certificate", "-a", "-p", kc],
                        capture_output=True,
                        check=False,
                    ).stdout
            if certs:
                with open(pem, "wb") as f:
                    f.write(certs)
        if os.path.isfile(pem):
            return ssl.create_default_context(cafile=pem)
    except Exception:
        pass  # nosec B110 — keychain export is best-effort; stdlib default below

    return ssl.create_default_context()


SSL_CTX = _ssl_context()


# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------
def load_config():
    """Read ``~/.resolve_frameio/config.json`` — returns ``{}`` if missing."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}  # nosec B110 — missing/corrupt config is normal first-run state


# Module-level cache so every script sees the same dict and ``save_config``
# just flushes it to disk. Reload via :func:`load_config` if you need to.
cfg = load_config()


def save_config():
    """
    Persist ``cfg`` to disk and make sure the file is only readable by the
    current user (``chmod 0600``) — this file can hold OAuth tokens.
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except Exception:
        # Best-effort; on Windows chmod is a no-op.
        pass  # nosec B110


# ---------------------------------------------------------------------------
# HTTP primitives
# ---------------------------------------------------------------------------
class ApiError(Exception):
    """Any HTTP / API error we want to surface to the user with a nice message."""


def http(method, url, data=None, headers=None, form=None, raw=None, timeout=120):
    """
    Thin wrapper around ``urllib.request`` with:

    * JSON encoding when ``data`` is a dict.
    * ``application/x-www-form-urlencoded`` when ``form`` is a dict.
    * Raw bytes when ``raw`` is given (used for S3 chunk uploads).
    * JSON decoding of the response (empty body → ``{}``).
    * Human-friendly ``ApiError`` messages (never contains the request body).
    """
    headers = dict(headers or {})
    headers.setdefault("User-Agent", USER_AGENT)

    body = None
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    elif raw is not None:
        body = raw

    # Only https:// URLs ever reach this function (constructed via API/IMS
    # constants and the Frame.io ``links.next`` cursor which is always https).
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as r:  # nosec B310
            txt = r.read()
            if not txt:
                return {}
            try:
                return json.loads(txt)
            except ValueError:
                return {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")
        try:
            errs = json.loads(msg).get("errors") or []
            msg = "; ".join((x.get("detail") or x.get("title") or "") for x in errs) or msg
        except Exception:
            pass  # nosec B110 — body may not be JSON; fall back to raw text
        # Translate the most common Frame.io gotcha into something actionable.
        if "not linked to an Adobe ID" in msg:
            msg = (
                "Sua conta do Frame.io não está ligada a um Adobe ID. Em frame.io: "
                "Account Settings > Profile > Authentication > Adobe > Connect."
            )
        raise ApiError("HTTP %s: %s" % (e.code, msg[:400]))
    except urllib.error.URLError as e:
        raise ApiError("Falha de conexão: %s" % e.reason)


# ---------------------------------------------------------------------------
# Adobe IMS OAuth (Web App flow)
# ---------------------------------------------------------------------------
def auth_url():
    """
    Build the authorization URL to open in the user's browser. Uses a
    cryptographically random ``state`` to defend against CSRF.
    """
    q = {
        "client_id":     cfg["client_id"],
        "redirect_uri":  cfg.get("redirect_uri", DEFAULT_REDIRECT),
        "scope":         SCOPES.replace(" ", ","),
        "response_type": "code",
        "state":         secrets.token_urlsafe(16),
    }
    return IMS + "/authorize/v2?" + urllib.parse.urlencode(q)


def _store_token(tok):
    """Persist the token payload returned by IMS, computing an absolute expiry."""
    if "access_token" not in tok:
        raise ApiError("Resposta de login inesperada.")
    cfg["access_token"] = tok["access_token"]
    if tok.get("refresh_token"):
        cfg["refresh_token"] = tok["refresh_token"]
    # 120s buffer so we never cut it too close.
    cfg["expires_at"] = time.time() + int(tok.get("expires_in", 3600)) - 120
    save_config()


def exchange_code(pasted):
    """
    Exchange the ``code=...`` query parameter from the redirect URL for an
    access + refresh token pair. Accepts either the full redirect URL or the
    bare code.
    """
    pasted = pasted.strip()
    if pasted.startswith("http"):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
        code = (qs.get("code") or [""])[0]
    else:
        code = pasted
    if not code:
        raise ApiError("Não encontrei o código no endereço colado.")
    _store_token(http("POST", IMS + "/token/v3", form={
        "grant_type":    "authorization_code",
        "client_id":     cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "code":          code,
    }))


def logged_in():
    """``True`` if we have a refresh token we can trade for fresh access tokens."""
    return bool(cfg.get("refresh_token"))


def token():
    """
    Return a valid access token, refreshing silently if the current one is
    expired. Raises :class:`ApiError` if the user hasn't logged in yet.
    """
    if cfg.get("access_token") and time.time() < cfg.get("expires_at", 0):
        return cfg["access_token"]
    if not cfg.get("refresh_token"):
        raise ApiError("Faça login no Frame.io (botão Configurar / Login).")
    _store_token(http("POST", IMS + "/token/v3", form={
        "grant_type":    "refresh_token",
        "client_id":     cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "refresh_token": cfg["refresh_token"],
    }))
    return cfg["access_token"]


# ---------------------------------------------------------------------------
# Frame.io V4 — authenticated request + pagination
# ---------------------------------------------------------------------------
def fio(method, path, data=None, params=None):
    """
    Make an authenticated request against the Frame.io V4 API.

    ``path`` can be:

    * A full URL (``https://...``) — used verbatim.
    * Starts with ``/v4/`` — the Frame.io ``links.next`` cursor format.
    * Anything else — treated as a path under :data:`API`.
    """
    if path.startswith("http"):
        url = path
    elif path.startswith("/v4/"):
        url = "https://api.frame.io" + path
    else:
        url = API + path
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    return http(method, url, data=data, headers={"Authorization": "Bearer " + token()})


def fio_all(path, params=None):
    """Follow Frame.io's ``links.next`` cursor until exhausted; flatten ``data``."""
    items, res = [], fio("GET", path, params=params)
    while True:
        items.extend(res.get("data") or [])
        nxt = (res.get("links") or {}).get("next")
        if not nxt:
            return items
        res = fio("GET", nxt)


# ---------------------------------------------------------------------------
# Frame.io V4 — navigation (accounts, workspaces, projects, folders, files)
# ---------------------------------------------------------------------------
def list_workspaces():
    """Return every workspace the user can see, with a human-readable label."""
    out = []
    for acc in fio_all("/accounts"):
        aname = acc.get("display_name") or acc.get("name") or "Conta"
        for ws in fio_all("/accounts/%s/workspaces" % acc["id"]):
            out.append({
                "account_id": acc["id"],
                "id":         ws["id"],
                "label":      "%s / %s" % (aname, ws.get("name", "?")),
            })
    return out


def list_projects(account_id, workspace_id):
    """Projects in a workspace, alphabetically sorted."""
    ps = fio_all("/accounts/%s/workspaces/%s/projects" % (account_id, workspace_id))
    return sorted(ps, key=lambda p: (p.get("name") or "").lower())


def list_folders(account_id, root_id, max_depth=4):
    """
    Walk the folder tree below ``root_id`` (usually a project's root folder).
    Returns ``[(display_path, folder_id)]`` with the project root first.
    """
    out = [("(raiz do projeto)", root_id)]

    def walk(fid, prefix, depth):
        if depth > max_depth:
            return
        kids = fio_all(
            "/accounts/%s/folders/%s/children" % (account_id, fid),
            params={"type": "folder", "page_size": 200},
        )
        kids = sorted(
            (k for k in kids if k.get("type") == "folder"),
            key=lambda k: (k.get("name") or "").lower(),
        )
        for k in kids:
            path = (prefix + " / " if prefix else "") + k.get("name", "?")
            out.append((path, k["id"]))
            walk(k["id"], path, depth + 1)

    walk(root_id, "", 1)
    return out


def create_folder(account_id, parent_id, name):
    """Create a folder inside ``parent_id`` and return its new ID."""
    res = fio(
        "POST",
        "/accounts/%s/folders/%s/folders" % (account_id, parent_id),
        data={"data": {"name": name}},
    )
    d = res.get("data") or {}
    if not d.get("id"):
        raise ApiError("O Frame.io não confirmou a criação da pasta.")
    return d["id"]


def upload_file(account_id, folder_id, path, progress):
    """
    Upload a local file to Frame.io using the V4 local_upload flow:

    1. ``POST /folders/{id}/files/local_upload`` → returns an array of signed
       S3 ``PUT`` URLs (chunked).
    2. ``PUT`` each chunk sequentially, with up to 3 retries.

    ``progress(msg)`` is called after each chunk with a human-readable string.
    Returns the created file ID.
    """
    size = os.path.getsize(path)
    name = os.path.basename(path)
    res = fio(
        "POST",
        "/accounts/%s/folders/%s/files/local_upload" % (account_id, folder_id),
        data={"data": {"name": name, "file_size": size}},
    )
    d = res.get("data") or {}
    urls = d.get("upload_urls") or []
    if not urls:
        raise ApiError("O Frame.io não devolveu endereços de upload.")

    ctype = d.get("media_type") or mimetypes.guess_type(name)[0] or "video/mp4"
    sent = 0
    with open(path, "rb") as f:
        for i, part in enumerate(urls, 1):
            n = int(part.get("size") or 0) or (size - sent)
            chunk = f.read(n)
            for attempt in range(3):
                try:
                    http("PUT", part["url"], raw=chunk, timeout=600, headers={
                        "Content-Type": ctype,
                        "x-amz-acl":    "private",
                    })
                    break
                except ApiError:
                    if attempt == 2:
                        raise
                    time.sleep(2)
            sent += len(chunk)
            progress("Enviando… parte %d de %d (%d%%)" %
                     (i, len(urls), sent * 100 // max(size, 1)))
    return d.get("id")


def list_files(account_id, folder_id):
    """
    Files in a folder, as ``[(label, file_id)]``. Version stacks are expanded
    into one row per version so the user can pick an older cut.
    """
    out = []
    kids = fio_all(
        "/accounts/%s/folders/%s/children" % (account_id, folder_id),
        params={"page_size": 200},
    )
    kids = [k for k in kids if k.get("type") in ("file", "version_stack")]
    for k in sorted(kids, key=lambda k: k.get("updated_at") or "", reverse=True):
        if k.get("type") == "file":
            out.append((k.get("name", "?"), k["id"]))
        elif k.get("type") == "version_stack":
            try:
                vers = fio_all("/accounts/%s/version_stacks/%s/children" % (account_id, k["id"]))
                for n, v in enumerate(vers):
                    tag = " (versão atual)" if n == 0 else " (versão anterior %d)" % n
                    out.append(((v.get("name") or k.get("name", "?")) + tag, v["id"]))
            except ApiError:
                pass
    return out


def list_comments(account_id, file_id):
    """All comments on a file, including replies and owner metadata."""
    return fio_all(
        "/accounts/%s/files/%s/comments" % (account_id, file_id),
        params={"include": "owner,replies", "page_size": 100},
    )


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------
def to_frames(value, fps):
    """
    Convert a Frame.io timestamp into a frame count at ``fps``.

    Accepts an int/float (already frames), a plain integer string, or a
    timecode (HH:MM:SS:FF or HH:MM:SS;FF for drop-frame).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if s.isdigit():
        return int(s)
    try:
        if ";" in s or s.count(":") == 3:
            h, m, sec, f = [int(x) for x in s.replace(";", ":").split(":")]
            return int(round((h * 3600 + m * 60 + sec) * fps)) + f
        parts = [float(x) for x in s.split(":")]
        secs = 0.0
        for p in parts:
            secs = secs * 60 + p
        return int(round(secs * fps))
    except Exception:
        return None


def safe_name(s):
    """Strip characters that Windows/macOS don't allow in file names."""
    for c in '/\\:*?"<>|':
        s = s.replace(c, "-")
    return s.strip() or "Sem nome"


# ---------------------------------------------------------------------------
# UI — settings dialog (shared by every entry-point script)
# ---------------------------------------------------------------------------
def settings_window(ui, disp):
    """
    Blocking dialog that collects ``client_id`` / ``client_secret`` /
    redirect URI and walks the user through the OAuth round-trip.
    """
    win = disp.AddWindow(
        {"ID": "FioSetup", "WindowTitle": "Frame.io – Configurar",
         "Geometry": [220, 220, 560, 330]},
        ui.VGroup({"Spacing": 6}, [
            ui.Label({"Text": "<b>1.</b> Credenciais do Adobe Developer Console (OAuth Web App)", "WordWrap": True}),
            ui.HGroup([ui.Label({"Text": "Client ID",     "Weight": 0.25}),
                       ui.LineEdit({"ID": "cid",  "Text": cfg.get("client_id", "")})]),
            ui.HGroup([ui.Label({"Text": "Client Secret", "Weight": 0.25}),
                       ui.LineEdit({"ID": "csec", "Text": cfg.get("client_secret", ""), "EchoMode": "Password"})]),
            ui.HGroup([ui.Label({"Text": "Redirect URI",  "Weight": 0.25}),
                       ui.LineEdit({"ID": "ruri", "Text": cfg.get("redirect_uri", DEFAULT_REDIRECT)})]),
            ui.Button({"ID": "login", "Text": "2. Abrir login do Frame.io no navegador"}),
            ui.Label({"Text": "<b>3.</b> Depois de entrar, o navegador mostra uma página de erro. "
                              "Copie o endereço inteiro dela e cole aqui:", "WordWrap": True}),
            ui.LineEdit({"ID": "pasted", "PlaceholderText": "https://localhost:8765/callback?code=..."}),
            ui.HGroup([ui.Label({"ID": "st",
                                 "Text": "Conectado ✔" if logged_in() else "Não conectado",
                                 "WordWrap": True}),
                       ui.Button({"ID": "ok", "Text": "Concluir login", "Weight": 0.3})]),
        ]))
    it = win.GetItems()

    def read_fields():
        cfg["client_id"]     = it["cid"].Text.strip()
        cfg["client_secret"] = it["csec"].Text.strip()
        cfg["redirect_uri"]  = it["ruri"].Text.strip() or DEFAULT_REDIRECT
        save_config()

    def on_login(ev):
        read_fields()
        if not cfg["client_id"] or not cfg["client_secret"]:
            it["st"].Text = "Preencha Client ID e Client Secret."
            return
        webbrowser.open(auth_url())
        it["st"].Text = "Navegador aberto. Faça login e cole o endereço."

    def on_ok(ev):
        read_fields()
        if not it["pasted"].Text.strip():
            disp.ExitLoop()
            return
        try:
            exchange_code(it["pasted"].Text)
            disp.ExitLoop()
        except Exception as e:
            it["st"].Text = "Erro: %s" % str(e)[:200]

    win.On.login.Clicked = on_login
    win.On.ok.Clicked    = on_ok
    win.On.FioSetup.Close = lambda ev: disp.ExitLoop()
    win.Show()
    disp.RunLoop()
    win.Hide()


# ---------------------------------------------------------------------------
# UI — destination picker (shared by every entry-point script)
# ---------------------------------------------------------------------------
def folder_rows(ui, with_new=True):
    """
    Three (or four) rows of combo boxes used by every main dialog:
    ``Workspace`` / ``Projeto`` / ``Pasta`` (and optionally ``Nova pasta``).
    """
    rows = [
        ui.HGroup([ui.Label({"Text": "Workspace", "Weight": 0.22}), ui.ComboBox({"ID": "ws"})]),
        ui.HGroup([ui.Label({"Text": "Projeto",   "Weight": 0.22}), ui.ComboBox({"ID": "proj"})]),
        ui.HGroup([ui.Label({"Text": "Pasta",     "Weight": 0.22}),
                   ui.ComboBox({"ID": "folder"}),
                   ui.Button({"ID": "refresh", "Text": "↻", "Weight": 0.06})]),
    ]
    if with_new:
        rows.append(ui.HGroup([
            ui.Label({"Text": "Nova pasta", "Weight": 0.22}),
            ui.LineEdit({"ID": "newfolder",
                         "PlaceholderText": "nome da pasta (criada dentro da pasta escolhida)"}),
            ui.Button({"ID": "mkfolder", "Text": "Criar", "Weight": 0.12}),
        ]))
    return rows


class FolderPicker(object):
    """
    Glues the Workspace/Project/Folder combo boxes built by :func:`folder_rows`
    to the Frame.io API. Also remembers the last selection in ``cfg``.
    """

    def __init__(self, win, it, status, on_folder=None, with_new=True):
        self.it, self.status, self.on_folder = it, status, on_folder
        self.ws, self.projects, self.folders = [], [], []
        # Re-entrancy guard: AddItem fires CurrentIndexChanged, which would
        # otherwise trigger recursive loads during the initial Clear/populate.
        self.loading = False

        win.On.ws.CurrentIndexChanged   = lambda ev: self._safe(self.fill_projects)
        win.On.proj.CurrentIndexChanged = lambda ev: self._safe(self.fill_folders)
        win.On.refresh.Clicked          = lambda ev: self.fill_all()
        if with_new:
            win.On.mkfolder.Clicked = lambda ev: self._safe(self.make_folder)
        if on_folder:
            win.On.folder.CurrentIndexChanged = lambda ev: self._safe(on_folder)

    def _safe(self, fn):
        if self.loading:
            return
        try:
            fn()
        except Exception as e:
            self.loading = False
            self.status("⚠️ %s" % e)

    def _select(self, combo, ids, want):
        if want in ids:
            self.it[combo].CurrentIndex = ids.index(want)

    def fill_all(self):
        def run():
            self.it["ws"].Clear()
            self.status("Conectando ao Frame.io…")
            self.ws = list_workspaces()
            self.loading = True
            for w in self.ws:
                self.it["ws"].AddItem(w["label"])
            self._select("ws", [w["id"] for w in self.ws], cfg.get("last_workspace_id"))
            self.loading = False
            self.fill_projects()
        self._safe(run)

    def fill_projects(self):
        self.it["proj"].Clear()
        self.it["folder"].Clear()
        self.projects, self.folders = [], []
        w = self.workspace()
        if not w:
            return
        self.status("Carregando projetos…")
        self.projects = list_projects(w["account_id"], w["id"])
        self.loading = True
        for p in self.projects:
            self.it["proj"].AddItem(p.get("name", "?"))
        self._select("proj", [p["id"] for p in self.projects], cfg.get("last_project_id"))
        self.loading = False
        self.fill_folders()

    def fill_folders(self, select_id=None):
        self.it["folder"].Clear()
        self.folders = []
        w, p = self.workspace(), self.project()
        if not w or not p:
            return
        self.status("Carregando pastas…")
        self.folders = list_folders(w["account_id"], p["root_folder_id"])
        self.loading = True
        for path, _ in self.folders:
            self.it["folder"].AddItem(path)
        self._select("folder", [f for _, f in self.folders],
                     select_id or cfg.get("last_folder_id"))
        self.loading = False
        self.status("Pronto.")
        if self.on_folder:
            self.on_folder()

    def make_folder(self):
        name = safe_name(self.it["newfolder"].Text)
        if not self.it["newfolder"].Text.strip():
            self.status("Digite o nome da nova pasta.")
            return
        sel = self.selected()
        if not sel:
            self.status("Escolha primeiro onde a pasta será criada.")
            return
        self.status("Criando pasta “%s”…" % name)
        new_id = create_folder(sel["account_id"], sel["folder_id"], name)
        self.it["newfolder"].Text = ""
        self.fill_folders(select_id=new_id)
        self.status("✅ Pasta criada: %s" % self.selected()["label"])

    def workspace(self):
        i = self.it["ws"].CurrentIndex
        return self.ws[i] if 0 <= i < len(self.ws) else None

    def project(self):
        i = self.it["proj"].CurrentIndex
        return self.projects[i] if 0 <= i < len(self.projects) else None

    def selected(self):
        w, p = self.workspace(), self.project()
        i = self.it["folder"].CurrentIndex
        if not w or not p or not (0 <= i < len(self.folders)):
            return None
        path, fid = self.folders[i]
        return {
            "account_id":   w["account_id"],
            "workspace_id": w["id"],
            "project_id":   p["id"],
            "folder_id":    fid,
            "label":        "%s / %s" % (p.get("name", "?"), path),
        }

    def remember(self):
        s = self.selected()
        if s:
            cfg.update({
                "last_workspace_id": s["workspace_id"],
                "last_project_id":   s["project_id"],
                "last_folder_id":    s["folder_id"],
            })
            save_config()
