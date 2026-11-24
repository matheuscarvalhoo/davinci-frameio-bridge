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
Frame.io - Enviar ao terminar render

End-of-render trigger. In the DaVinci Deliver tab:

    Render Settings → File → Trigger script at: End of render job
    → point it at this file.

DaVinci runs this script headlessly (no UI available), so it only:

1. Figures out which file was just rendered (by job ID when the API provides
   it, otherwise the most recent file in the render folder).
2. Launches the standalone ``uploader_gui.py`` as a separate process so a
   proper window can appear even though DaVinci is in headless render mode.

A tiny log is written to ``~/.resolve_frameio/trigger.log`` for debugging.
"""

import os
import time
import subprocess  # nosec B404 — used to spawn the user's own Python interpreter with hardcoded args

HOME = os.path.expanduser("~")
CORE = os.path.join(HOME, ".resolve_frameio")
LOG  = os.path.join(CORE, "trigger.log")
GUI  = os.path.join(CORE, "uploader_gui.py")

# Candidate Python interpreters, from most to least likely to exist on the
# user's Mac. The first file that actually exists wins. Falls back to
# ``python3`` on PATH.
PYTHONS = [
    "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
    "/Library/Frameworks/Python.framework/Versions/3.15/bin/python3",
    "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
    "/opt/homebrew/bin/python3",
    "/usr/local/bin/python3",
    "/usr/bin/python3",
]


def log(msg):
    """Append one timestamped line to the trigger log. Never raises."""
    try:
        os.makedirs(CORE, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except Exception:
        pass  # nosec B110 — logging must never crash the trigger


def get_resolve():
    """Return the ``resolve`` object injected by DaVinci, or ``None``."""
    r = globals().get("resolve")
    if r:
        return r
    try:
        import DaVinciResolveScript as dvr
        return dvr.scriptapp("Resolve")
    except Exception as e:
        log("sem acesso ao Resolve: %s" % e)
        return None


def find_output(job_id):
    """
    Locate the rendered file. Strategy:

    1. If we can read the render queue, prefer the exact job matching
       ``job_id``.
    2. Otherwise, pick the most recent file in any of the render-queue target
       directories (within the last 30 minutes).
    """
    cands, folder = [], ""
    try:
        project = get_resolve().GetProjectManager().GetCurrentProject()
        for j in project.GetRenderJobList() or []:
            d = j.get("TargetDir") or ""
            p = os.path.join(d, j.get("OutputFilename") or "")
            if job_id and str(j.get("JobId")) == str(job_id):
                folder = d
                if os.path.isfile(p):
                    return p
            if d:
                cands.append(p)
                folder = folder or d
    except Exception as e:
        log("erro lendo fila de render: %s" % e)

    dirs = {os.path.dirname(c) for c in cands} | ({folder} if folder else set())
    for d in dirs:
        if os.path.isdir(d):
            cands += [os.path.join(d, f) for f in os.listdir(d)]
    # Only files that finished in the last 30 minutes.
    cands = [c for c in cands
             if os.path.isfile(c) and time.time() - os.path.getmtime(c) < 1800]
    return max(cands, key=os.path.getmtime) if cands else None


def main():
    job_id = globals().get("job")
    st     = globals().get("status")
    log("disparado: job=%r status=%r" % (job_id, st))

    if st and str(st).lower() not in ("complete", "completed"):
        log("render não concluído; nada a enviar")
        return

    path = find_output(job_id)
    log("arquivo: %r" % path)

    py = next((p for p in PYTHONS if os.path.isfile(p)), "python3")
    # `py` comes from a hardcoded allowlist; `GUI` is a fixed path inside
    # ~/.resolve_frameio/; `path` is the DaVinci-produced render file name,
    # treated as a single argv element (no shell interpolation).
    subprocess.Popen(  # nosec B603
        [py, GUI, path or ""],
        start_new_session=True,
        stdout=open(os.path.join(CORE, "gui.log"), "a"),
        stderr=subprocess.STDOUT,
    )
    log("janela aberta com %s" % py)


try:
    main()
except Exception as e:
    log("ERRO: %r" % e)
