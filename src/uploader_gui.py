# -*- coding: utf-8 -*-
#
# davinci-frameio-bridge
# Copyright (C) 2026 Marrk
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. See LICENSE at the repository root.
#
# This program is distributed WITHOUT ANY WARRANTY. See the license for details.

"""
uploader_gui.py
===============

Standalone Tk window that uploads an already-rendered file to Frame.io.

Called by ``Enviar_ao_terminar_render.py`` immediately after a DaVinci render
finishes. Lives outside the DaVinci process so it can present a real window
even when Resolve is in headless render mode.

Usage::

    python3 uploader_gui.py "/path/to/rendered.mp4"
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk

# Resolve the shared library sitting next to this script in
# ``~/.resolve_frameio/``.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frameio_core as fc  # noqa: E402

PATH = sys.argv[1] if len(sys.argv) > 1 else ""


class App(object):
    """Owns the Tk window, the network threads, and the upload state."""

    def __init__(self, root):
        self.root = root
        self.ws, self.projects, self.folders = [], [], []
        self.busy = False

        root.title("Enviar para Frame.io")
        root.geometry("620x330")
        root.minsize(560, 300)

        f = ttk.Frame(root, padding=14)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        # File name header
        name = os.path.basename(PATH) if PATH else "nenhum arquivo"
        ttk.Label(f, text="Arquivo:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(f, text=name, font=("", 12, "bold")).grid(
            row=0, column=1, columnspan=2, sticky="w",
        )

        # Workspace / Project / Folder
        self.cb_ws     = self._combo(f, 1, "Workspace", self.on_ws)
        self.cb_proj   = self._combo(f, 2, "Projeto",   self.on_proj)
        self.cb_folder = self._combo(f, 3, "Pasta",     None)
        ttk.Button(f, text="↻", width=3, command=self.load_all).grid(
            row=3, column=2, padx=(6, 0),
        )

        # New-folder helper
        ttk.Label(f, text="Nova pasta").grid(row=4, column=0, sticky="w", pady=4)
        self.new_name = tk.StringVar()
        e = ttk.Entry(f, textvariable=self.new_name)
        e.grid(row=4, column=1, sticky="ew")
        e.bind("<Return>", lambda ev: self.make_folder())
        ttk.Button(f, text="Criar", command=self.make_folder).grid(
            row=4, column=2, padx=(6, 0),
        )
        ttk.Label(
            f,
            text="(a pasta nova é criada dentro da pasta selecionada acima)",
            foreground="gray",
        ).grid(row=5, column=1, sticky="w")

        # Progress + status
        self.bar = ttk.Progressbar(f, mode="determinate", maximum=100)
        self.bar.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(12, 4))
        self.status = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.status, wraplength=580).grid(
            row=7, column=0, columnspan=3, sticky="w",
        )

        # Action buttons
        btns = ttk.Frame(f)
        btns.grid(row=8, column=0, columnspan=3, sticky="e", pady=(12, 0))
        self.btn_cancel = ttk.Button(btns, text="Não enviar", command=root.destroy)
        self.btn_cancel.pack(side="left", padx=4)
        self.btn_go = ttk.Button(btns, text="Enviar", command=self.send)
        self.btn_go.pack(side="left")

        # Force the window to the front — it was spawned by a background
        # process so macOS will not focus it automatically.
        root.lift()
        root.attributes("-topmost", True)
        root.after(1500, lambda: root.attributes("-topmost", False))
        root.focus_force()

        if not PATH or not os.path.isfile(PATH):
            self.set_status("⚠️ Não encontrei o arquivo renderizado.")
            self.btn_go.state(["disabled"])
        if not fc.logged_in():
            self.set_status(
                "Faça login primeiro: no DaVinci, Workspace > Scripts > Deliver > "
                "Enviar para Frame.io > Configurar / Login."
            )
            return
        self.load_all()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _combo(self, parent, row, label, cmd):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        cb = ttk.Combobox(parent, state="readonly")
        cb.grid(row=row, column=1, sticky="ew")
        if cmd:
            cb.bind("<<ComboboxSelected>>", lambda ev: cmd())
        return cb

    def set_status(self, t):
        self.root.after(0, lambda: self.status.set(t))

    def bg(self, work, done=None):
        """
        Run ``work()`` on a background thread so the Tk event loop keeps
        responsive during HTTP calls. ``done(result)`` is scheduled on the
        Tk thread if ``work`` returns normally.
        """
        def run():
            try:
                res = work()
                if done:
                    self.root.after(0, lambda: done(res))
            except Exception as e:
                self.set_status("⚠️ %s" % e)
                self.root.after(0, self.unlock)
        self.lock()
        threading.Thread(target=run, daemon=True).start()

    def lock(self):
        self.busy = True
        for w in (self.cb_ws, self.cb_proj, self.cb_folder):
            w.state(["disabled"])

    def unlock(self):
        self.busy = False
        for w in (self.cb_ws, self.cb_proj, self.cb_folder):
            w.state(["!disabled"])
            w.state(["readonly"])

    @staticmethod
    def _pick(cb, ids, want):
        if not ids:
            cb.set("")
        else:
            cb.current(ids.index(want) if want in ids else 0)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_all(self):
        self.set_status("Conectando ao Frame.io…")

        def done(ws):
            self.ws = ws
            self.cb_ws["values"] = [w["label"] for w in ws]
            self._pick(self.cb_ws, [w["id"] for w in ws], fc.cfg.get("last_workspace_id"))
            self.unlock()
            self.on_ws()
        self.bg(fc.list_workspaces, done)

    def on_ws(self):
        i = self.cb_ws.current()
        if i < 0:
            return
        w = self.ws[i]
        self.set_status("Carregando projetos…")

        def done(ps):
            self.projects = ps
            self.cb_proj["values"] = [p.get("name", "?") for p in ps]
            self._pick(self.cb_proj, [p["id"] for p in ps], fc.cfg.get("last_project_id"))
            self.unlock()
            self.on_proj()
        self.bg(lambda: fc.list_projects(w["account_id"], w["id"]), done)

    def on_proj(self, select_id=None):
        wi, pi = self.cb_ws.current(), self.cb_proj.current()
        if wi < 0 or pi < 0:
            return
        acc     = self.ws[wi]["account_id"]
        root_id = self.projects[pi]["root_folder_id"]
        self.set_status("Carregando pastas…")

        def done(fs):
            self.folders = fs
            self.cb_folder["values"] = [p for p, _ in fs]
            self._pick(self.cb_folder, [i for _, i in fs],
                       select_id or fc.cfg.get("last_folder_id"))
            self.unlock()
            self.set_status("Escolha onde salvar e clique em Enviar.")
        self.bg(lambda: fc.list_folders(acc, root_id), done)

    def selected(self):
        wi, pi, fi = self.cb_ws.current(), self.cb_proj.current(), self.cb_folder.current()
        if min(wi, pi, fi) < 0:
            return None
        path, fid = self.folders[fi]
        return {
            "account_id":   self.ws[wi]["account_id"],
            "workspace_id": self.ws[wi]["id"],
            "project_id":   self.projects[pi]["id"],
            "folder_id":    fid,
            "label":        "%s / %s" % (self.projects[pi].get("name", "?"), path),
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def make_folder(self):
        name = self.new_name.get().strip()
        sel = self.selected()
        if not name:
            self.set_status("Digite o nome da nova pasta.")
            return
        if not sel:
            self.set_status("Escolha primeiro onde a pasta será criada.")
            return
        self.set_status("Criando pasta “%s”…" % name)

        def done(new_id):
            self.new_name.set("")
            self.unlock()
            self.on_proj(select_id=new_id)
        self.bg(
            lambda: fc.create_folder(sel["account_id"], sel["folder_id"], fc.safe_name(name)),
            done,
        )

    def send(self):
        sel = self.selected()
        if not sel:
            self.set_status("Escolha a pasta do Frame.io.")
            return
        fc.cfg.update({
            "last_workspace_id": sel["workspace_id"],
            "last_project_id":   sel["project_id"],
            "last_folder_id":    sel["folder_id"],
        })
        fc.save_config()
        self.btn_go.state(["disabled"])

        def progress(t):
            self.set_status(t)
            try:
                pct = int(t.rsplit("(", 1)[1].split("%")[0])
                self.root.after(0, lambda: self.bar.configure(value=pct))
            except Exception:
                pass  # nosec B110 — progress parse is best-effort

        def done(_):
            self.bar.configure(value=100)
            self.set_status("✅ Enviado para %s" % sel["label"])
            self.btn_cancel.configure(text="Fechar")
            self.unlock()

        def work():
            try:
                return fc.upload_file(sel["account_id"], sel["folder_id"], PATH, progress)
            except Exception:
                self.root.after(0, lambda: self.btn_go.state(["!disabled"]))
                raise
        self.bg(work, done)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
