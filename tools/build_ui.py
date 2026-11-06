"""Regenerate the Python UI modules after editing the Qt Designer files.

    python tools/build_ui.py

* designer/*.ui            -> chess_trainer/ui/*_ui.py   (pyuic5 --from-imports)
* assets/images/res.qrc    -> chess_trainer/ui/res_rc.py (pyrcc5)
"""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_OUT = os.path.join(ROOT, "chess_trainer", "ui")


def run(*args):
    print(" ".join(args))
    subprocess.check_call([sys.executable, "-m", *args], cwd=ROOT)


def main():
    run("PyQt5.pyrcc_main", os.path.join("assets", "images", "res.qrc"),
        "-o", os.path.join("chess_trainer", "ui", "res_rc.py"))
    for ui in sorted(glob.glob(os.path.join(ROOT, "designer", "*.ui"))):
        name = os.path.splitext(os.path.basename(ui))[0]
        run("PyQt5.uic.pyuic", "--from-imports", os.path.relpath(ui, ROOT),
            "-o", os.path.join("chess_trainer", "ui", name + ".py"))


if __name__ == "__main__":
    main()
