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
Frame.io - Importar comentários   (menu Workspace > Scripts)

Fetches comments from a selected Frame.io file and creates one DaVinci
timeline marker per comment, at its exact timecode, with the author and
the comment thread in the marker notes.

Red markers = open comments. Green markers = resolved (opt-in).

Install location
----------------
``~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/``

Depends on ``~/.resolve_frameio/frameio_core.py``.
"""

import os
import sys
import importlib

sys.path.insert(0, os.path.expanduser("~/.resolve_frameio"))
import frameio_core as fc  # noqa: E402
importlib.reload(fc)

try:
    resolve  # noqa: F821
except NameError:
    import DaVinciResolveScript as dvr
    resolve = dvr.scriptapp("Resolve")
try:
    bmd  # noqa: F821
except NameError:
    import DaVinciResolveScript as bmd

ui = resolve.Fusion().UIManager
disp = bmd.UIDispatcher(ui)

# Every marker we create carries this prefix in its ``customData`` so we can
# find and replace our own markers without touching the ones the user placed
# by hand.
TAG         = "frameio:"
COLOR_OPEN  = "Red"
COLOR_DONE  = "Green"


def clean(s):
    """Collapse whitespace in a comment body for use as the marker name."""
    return " ".join((s or "").split())


def main():
    project  = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline() if project else None
    if not timeline:
        print("Abra a timeline que vai receber os marcadores.")
        return
    try:
        fps = float(
            timeline.GetSetting("timelineFrameRate")
            or project.GetSetting("timelineFrameRate")
            or 24
        )
    except Exception:
        fps = 24.0

    tl_name = timeline.GetName()
    files = []

    win = disp.AddWindow(
        {"ID": "FioImport", "WindowTitle": "Importar comentários do Frame.io",
         "Geometry": [200, 200, 640, 380]},
        ui.VGroup({"Spacing": 8}, [
            ui.Label({"Text": "Timeline: <b>%s</b> (%g fps)" % (tl_name, fps)}),
        ] + fc.folder_rows(ui, with_new=False) + [
            ui.HGroup([ui.Label({"Text": "Vídeo", "Weight": 0.22}),
                       ui.ComboBox({"ID": "file"})]),
            ui.CheckBox({"ID": "done",    "Text": "Incluir comentários já resolvidos (em verde)",
                         "Checked": False}),
            ui.CheckBox({"ID": "replace", "Text": "Apagar marcadores importados antes (evita duplicar)",
                         "Checked": True}),
            ui.Label({"ID": "status", "Text": "", "WordWrap": True}),
            ui.HGroup([ui.Button({"ID": "setup",  "Text": "Configurar / Login", "Weight": 0.3}),
                       ui.HGap(),
                       ui.Button({"ID": "cancel", "Text": "Fechar", "Weight": 0.2}),
                       ui.Button({"ID": "go",     "Text": "Importar marcadores", "Weight": 0.35})]),
        ]))
    it = win.GetItems()

    def status(t):
        it["status"].Text = t
        print("[Frame.io] " + t)

    def fill_files():
        it["file"].Clear()
        del files[:]
        sel = picker.selected()
        if not sel:
            return
        status("Carregando vídeos da pasta…")
        files.extend(fc.list_files(sel["account_id"], sel["folder_id"]))
        for label, _ in files:
            it["file"].AddItem(label)
        # Pre-select either the file we used last time, or the one whose name
        # matches the current timeline.
        want = fc.safe_name(tl_name).lower()
        for i, (label, fid) in enumerate(files):
            if fid == fc.cfg.get("last_comment_file_id") or label.lower().startswith(want):
                it["file"].CurrentIndex = i
                break
        status("%d vídeo(s) nesta pasta." % len(files) if files else "Nenhum vídeo nesta pasta.")

    picker = fc.FolderPicker(win, it, status, on_folder=fill_files, with_new=False)

    def remove_old():
        """Delete markers we previously created (they carry our TAG)."""
        n = 0
        for frame, m in list((timeline.GetMarkers() or {}).items()):
            if str(m.get("customData") or "").startswith(TAG):
                timeline.DeleteMarkerAtFrame(frame)
                n += 1
        return n

    def on_go(ev):
        sel = picker.selected()
        i = it["file"].CurrentIndex
        if not sel or not (0 <= i < len(files)):
            status("Escolha o vídeo no Frame.io.")
            return
        label, file_id = files[i]
        picker.remember()
        fc.cfg["last_comment_file_id"] = file_id
        fc.save_config()
        try:
            status("Buscando comentários…")
            comments = fc.list_comments(sel["account_id"], file_id)
            removed  = remove_old() if it["replace"].Checked else 0
            used     = set((timeline.GetMarkers() or {}).keys())
            added    = skipped = 0

            for c in sorted(comments, key=lambda c: fc.to_frames(c.get("timestamp"), fps) or 0):
                done = bool(c.get("completed_at"))
                if done and not it["done"].Checked:
                    skipped += 1
                    continue
                frame = fc.to_frames(c.get("timestamp"), fps)
                if frame is None:
                    # Comments without a timestamp attach to the start.
                    frame = 0
                # DaVinci allows only one marker per frame — bump forward.
                while frame in used:
                    frame += 1
                author = (c.get("owner") or {}).get("name") or "Cliente"
                text   = (c.get("text")  or "").strip()
                note   = "%s: %s" % (author, text)
                for r in c.get("replies") or []:
                    note += "\n↳ %s: %s" % (
                        (r.get("owner") or {}).get("name") or "?",
                        (r.get("text")  or "").strip(),
                    )
                dur  = max(1, fc.to_frames(c.get("duration"), fps) or 1)
                name = ("✔ " if done else "") + clean(text)[:60]
                if timeline.AddMarker(
                    frame,
                    COLOR_DONE if done else COLOR_OPEN,
                    name, note, dur,
                    TAG + str(c.get("id")),
                ):
                    used.add(frame)
                    added += 1

            msg = "✅ %d marcador(es) criado(s) a partir de “%s”." % (added, label)
            if skipped:
                msg += " %d já resolvido(s) ignorado(s)." % skipped
            if removed:
                msg += " %d marcador(es) antigo(s) substituído(s)." % removed
            if not comments:
                msg = "Esse vídeo ainda não tem comentários no Frame.io."
            status(msg)
        except Exception as e:
            status("⚠️ %s" % e)

    def on_setup(ev):
        fc.settings_window(ui, disp)
        picker.fill_all()

    win.On.go.Clicked        = on_go
    win.On.setup.Clicked     = on_setup
    win.On.cancel.Clicked    = lambda ev: disp.ExitLoop()
    win.On.FioImport.Close   = lambda ev: disp.ExitLoop()

    win.Show()
    if fc.logged_in():
        picker.fill_all()
    else:
        status("Primeiro acesso: clique em “Configurar / Login”.")
    disp.RunLoop()
    win.Hide()


main()
