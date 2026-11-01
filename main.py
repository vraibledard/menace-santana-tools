# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.align import Align  # noqa: E402
from rich.text import Text  # noqa: E402

from core import ui  # noqa: E402
from core.loader import Category, Tool, discover  # noqa: E402
from core.net import NetError  # noqa: E402
from core.theme import BLOOD_BRIGHT  # noqa: E402

START = time.time()


def elapsed() -> str:
    s = int(time.time() - START)
    return f"{s // 60:02d}:{s % 60:02d}"


def run_tool(cat: Category, tool: Tool) -> None:
    ui.show_header(crumbs=[cat.name, tool.name])
    try:
        tool.run()
    except (KeyboardInterrupt, EOFError):
        ui.console.print()
        ui.warn("Interrompu.")
    except NetError as e:
        ui.err(str(e))
    except Exception:
        ui.err("L'outil a planté :")
        ui.console.print_exception(max_frames=3)
    try:
        ui.pause()
    except (KeyboardInterrupt, EOFError):
        pass


def category_menu(cat: Category) -> None:
    while True:
        ui.show_header(crumbs=[cat.name])
        rows = [(str(i), f"{t.name}", "") for i, t in enumerate(cat.tools, 1)] or \
               [("--", "(aucun outil)", "")]
        ui.console.print(ui.listing(cat.title, rows, footer=("0", "RETOUR")))
        for e in cat.errors:
            ui.warn(f"Outil ignoré → {e}")
        try:
            choice = ui.shell_prompt("~/" + cat.id, ["0"] + [str(i) for i in range(1, len(cat.tools) + 1)])
        except (KeyboardInterrupt, EOFError):
            return
        if choice == "0":
            return
        run_tool(cat, cat.tools[int(choice) - 1])


def main() -> None:
    categories, errors = discover()
    if "--fast" not in sys.argv:
        ui.splash([("noyau MENACE", "chargé")]
                  + [(f"module {c.id}", f"{len(c.tools)} outil(s)") for c in categories]
                  + [("interface", "prête")])

    while True:
        ui.show_header()
        rows = [(str(i), f"{c.name}", "") for i, c in enumerate(categories, 1)]
        ui.console.print(ui.listing("MENU PRINCIPAL", rows, footer=("0", "QUITTER")))
        for e in errors:
            ui.warn(f"Module ignoré → {e}")
        try:
            choice = ui.shell_prompt("~", ["0"] + [str(i) for i in range(1, len(categories) + 1)])
        except (KeyboardInterrupt, EOFError):
            choice = "0"
        if choice == "0":
            bye = Text(f"Session terminée • on te retrouvera.", style=f"italic {BLOOD_BRIGHT}")
            ui.console.print()
            ui.console.print(Align.center(ui.info_panel(Align.center(bye))))
            time.sleep(1.0)
            return
        category_menu(categories[int(choice) - 1])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        ui.clear_screen()
