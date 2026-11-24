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
Enviar para Frame.io  (menu Workspace > Scripts > Deliver)

Renders the currently open DaVinci timeline with a chosen preset and uploads
the resulting file into a Frame.io folder picked in the dialog.

Install location
----------------
``~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Deliver/``

Depends on ``~/.resolve_frameio/frameio_core.py`` — kept outside the Scripts
folder so DaVinci doesn't list it in the menu.
"""

import os
import sys
import time
import importlib

# ---------------------------------------------------------------------------
# Load the shared library from the user config dir.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.expanduser("~/.resolve_frameio"))
import frameio_core as fc  # noqa: E402
importlib.reload(fc)       # pick up edits made during this DaVinci session

# ---------------------------------------------------------------------------
# DaVinci / Fusion UI bootstrap. ``resolve`` and ``bmd`` are injected when
# the script is launched from the DaVinci menu; the fallback is for running
# it outside DaVinci for debugging.
# ---------------------------------------------------------------------------
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

# Fallback preset — used only if the user hasn't picked one before.
# Pick any valid DaVinci render preset name available in your project.
DEFAULT_PRESET = "H.264 Master"


def render(project, preset, name, progress):
    """
    Render the current timeline with ``preset`` into :data:`fc.RENDER_DIR`
    and return the output file path. ``progress(msg)`` is called roughly
    once a second.
    """
    if not project.LoadRenderPreset(preset):
        raise fc.ApiError("Não consegui carregar o preset “%s”." % preset)

    os.makedirs(fc.RENDER_DIR, exist_ok=True)
    project.SetRenderSettings({
        "SelectAllFrames":    True,
        "TargetDir":          fc.RENDER_DIR,
        "CustomName":         name,
        "UseUniqueFilenames": False,
    })
    job = project.AddRenderJob()
    if not job:
        raise fc.ApiError("O DaVinci não aceitou o trabalho de render.")

    info = next((j for j in project.GetRenderJobList() if j.get("JobId") == job), {})
    out = os.path.join(info.get("TargetDir") or fc.RENDER_DIR,
                       info.get("OutputFilename") or "")

    project.StartRendering([job], False)
    while project.IsRenderingInProgress():
        st = project.GetRenderJobStatus(job) or {}
        progress("Renderizando… %s%%" % st.get("CompletionPercentage", 0))
        time.sleep(1)

    st = project.GetRenderJobStatus(job) or {}
    project.DeleteRenderJob(job)
    if st.get("JobStatus") != "Complete":
        raise fc.ApiError("O render não terminou (%s)." % st.get("JobStatus", "?"))
    if not os.path.isfile(out):
        raise fc.ApiError("Render concluído, mas não achei o arquivo em:\n%s" % out)
    return out


def main():
    project  = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline() if project else None
    if not timeline:
        print("Abra uma timeline antes de rodar o script.")
        return
    presets = project.GetRenderPresetList() or []

    win = disp.AddWindow(
        {"ID": "FioMain", "WindowTitle": "Enviar para Frame.io",
         "Geometry": [180, 180, 620, 360]},
        ui.VGroup({"Spacing": 8}, [
            ui.HGroup([ui.Label({"Text": "Nome do arquivo", "Weight": 0.22}),
                       ui.LineEdit({"ID": "name", "Text": timeline.GetName()})]),
            ui.HGroup([ui.Label({"Text": "Preset", "Weight": 0.22}),
                       ui.ComboBox({"ID": "preset"})]),
        ] + fc.folder_rows(ui) + [
            ui.Label({"ID": "status", "Text": "", "WordWrap": True}),
            ui.HGroup([ui.Button({"ID": "setup",  "Text": "Configurar / Login", "Weight": 0.3}),
                       ui.HGap(),
                       ui.Button({"ID": "cancel", "Text": "Fechar", "Weight": 0.2}),
                       ui.Button({"ID": "go",     "Text": "Renderizar e enviar", "Weight": 0.35})]),
        ]))
    it = win.GetItems()

    def status(t):
        it["status"].Text = t
        print("[Frame.io] " + t)

    picker = fc.FolderPicker(win, it, status)

    for p in presets:
        it["preset"].AddItem(p)
    want = fc.cfg.get("last_preset") or DEFAULT_PRESET
    if want in presets:
        it["preset"].CurrentIndex = presets.index(want)

    def on_setup(ev):
        fc.settings_window(ui, disp)
        picker.fill_all()

    def on_go(ev):
        dest = picker.selected()
        if not dest:
            status("Escolha a pasta do Frame.io.")
            return
        preset = it["preset"].CurrentText
        fc.cfg["last_preset"] = preset
        picker.remember()
        it["go"].Enabled = False
        try:
            out = render(project, preset, fc.safe_name(it["name"].Text), status)
            status("Render pronto. Enviando para o Frame.io…")
            fc.upload_file(dest["account_id"], dest["folder_id"], out, status)
            status("✅ Enviado: %s → %s" % (os.path.basename(out), dest["label"]))
        except Exception as e:
            status("⚠️ %s" % e)
        finally:
            it["go"].Enabled = True

    win.On.setup.Clicked    = on_setup
    win.On.go.Clicked       = on_go
    win.On.cancel.Clicked   = lambda ev: disp.ExitLoop()
    win.On.FioMain.Close    = lambda ev: disp.ExitLoop()

    win.Show()
    if fc.logged_in():
        picker.fill_all()
    else:
        status("Primeiro acesso: clique em “Configurar / Login”.")
    disp.RunLoop()
    win.Hide()


main()
