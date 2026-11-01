# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
from __future__ import annotations

import json
import os
import re
import time
import random
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from core.theme import ASH, BANNER, BANNER_COMPACT, BLOOD, BLOOD_BRIGHT, BONE, GOOD, HOST, MUTED, ORANGE, TITLE, VERSION, LOADING_MSGS

console = Console(highlight=False)
SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

import atexit

if os.name == "nt":
    os.system("")  # active les codes ANSI sous Windows


def set_cursor(style: str = "block") -> None:
    """Change la forme du curseur : block / underline / bar (+ 'blink_' devant pour clignotant)."""
    codes = {"blink_block": 1, "block": 2, "blink_underline": 3, "underline": 4, "blink_bar": 5, "bar": 6}
    console.file.write(f"\033[{codes.get(style, 0)} q")
    console.file.flush()


set_cursor("blink_block")                      # bloc clignotant, comme sous Linux
atexit.register(lambda: set_cursor("default")) # remet le curseur normal en quittant


# ═════════════ couleurs & barres ═════════════
def _lerp(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def gradient_bar(frac: float, width: int = 40) -> Text:
    n = round(max(0.0, min(frac, 1.0)) * width)
    t = Text()
    for i in range(width):
        t.append("█" if i < n else "░", style=_lerp(ORANGE, BLOOD_BRIGHT, i / max(width - 1, 1)) if i < n else "#3a1a1a")
    return t


# ═════════════ écran & en-têtes ═════════════
def clear_screen() -> None:
    console.file.write("\033[2J\033[3J\033[H")
    console.file.flush()


def is_tall() -> bool:
    return console.size.height >= 24


def banner(dim: float = 1.0) -> Text:
    out = Text()
    if is_tall():
        lines = BANNER.splitlines()
        for y, line in enumerate(lines):
            color = _lerp(ORANGE, BLOOD, y / (len(lines) - 1))
            out.append(line + "\n", style=f"bold {_lerp('#000000', color, dim) if dim < 1 else color}")
    else:
        width = max(len(l) for l in BANNER_COMPACT)
        for line in BANNER_COMPACT:
            for x, ch in enumerate(line):
                color = _lerp(ORANGE, BLOOD_BRIGHT, x / width)
                out.append(ch, style=f"bold {_lerp('#000000', color, dim) if dim < 1 else color}")
            out.append("\n")
    out.rstrip()
    return out


def status_bar(items: list[tuple[str, str]]) -> Text:
    t = Text()
    for key, value in items:
        t.append(f" {key} ", style=f"bold black on {ORANGE}")
        t.append(f" {value} ", style=f"{BONE} on #2a0000")
        t.append("  ")
    return t


def show_header(crumbs: list[str] | None = None, status: list[tuple[str, str]] | None = None) -> None:
    clear_screen()
    if crumbs is None:
        console.print()
        console.print(Align.center(banner()))
        console.print()
        console.print(Rule(f"[bold {ORANGE}]{TITLE}[/]  [{ASH}]{VERSION}[/]", style=BLOOD, characters="━"))
        if status:
            console.print(Align.center(status_bar(status)))
        console.print()
    else:
        t = Text()
        t.append("  ", style=f"bold {BLOOD_BRIGHT}")
        t.append(TITLE, style=f"bold {ORANGE}")
        for c in crumbs:
            t.append("  ▸  ", style=ASH)
            t.append(c, style=f"bold {BONE}")
        console.print(Rule(t, align="left", style=BLOOD, characters="━"))
        console.print()


# ═════════════ chargements animés ═════════════
def splash(steps: list[tuple[str, str]]) -> None:
    """Affiche uniquement la bannière et la barre de progression jusqu'à 100 %."""
    clear_screen()
    total = max(len(steps), 1)
    frames = 8

    def build(pct: float, tick: int):
        bar = Text.assemble(
            (f"{SPIN[tick % len(SPIN)]} ", f"bold {ORANGE}"),
            gradient_bar(pct, 46),
            (f"  {int(pct * 100):>3}%", f"bold {BONE}"),
        )
        return Group(
            Text(""),
            Align.center(banner()),
            Text(""),
            Align.center(bar),
            Text(""),
        )

    with Live(
        build(0, 0),
        console=console,
        auto_refresh=False,
        vertical_overflow="visible",
    ) as live:
        tick = 0
        for i, _step in enumerate(steps):
            for f in range(frames):
                pct = (i + (f + 1) / frames) / total
                live.update(build(pct, tick), refresh=True)
                tick += 1
                time.sleep(0.03)

        live.update(build(1.0, tick), refresh=True)
        time.sleep(0.4)

# ═════════════ étapes en parallèle ═════════════
def run_steps(title: str, steps: list[tuple[str, Callable]], workers: int = 32) -> list[dict]:
    """Exécute les étapes en parallèle avec une barre animée.
    Retourne, dans l'ordre de `steps`, des dicts {"ok": bool, "data": ..., "error": str}."""
    total = max(len(steps), 1)
    results: list[dict] = [{"ok": False, "data": None, "error": "non exécuté"} for _ in steps]

    def work(i: int) -> int:
        try:
            results[i] = {"ok": True, "data": steps[i][1]()}
        except Exception as e:
            results[i] = {"ok": False, "data": None, "error": str(e)}
        return i

    def build(done: int, tick: int, last: str) -> Group:
        bar = Text.assemble(
            (f"{SPIN[tick % len(SPIN)]} ", f"bold {ORANGE}"),
            gradient_bar(done / total, 36),
            (f"  {done}/{total}", f"bold {BONE}"),
        )
        return Group(Text(f" {title}", style=f"bold {ORANGE}"), bar, Text(f" {last}", style=ASH))

    ex = ThreadPoolExecutor(max_workers=min(workers, max(len(steps), 1)))
    try:
        pending = {ex.submit(work, i) for i in range(len(steps))}
        done, tick, last = 0, 0, ""
        with Live(build(0, 0, ""), console=console, auto_refresh=False, transient=True) as live:
            while pending:
                finished, pending = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)
                for f in finished:
                    done += 1
                    last = steps[f.result()][0]
                tick += 1
                live.update(build(done, tick, last), refresh=True)
    except BaseException:
        ex.shutdown(wait=False, cancel_futures=True)
        raise
    ex.shutdown(wait=True)
    return results


@contextmanager
def working(label: str):
    """with ui.working("Chargement…"): ...  → spinner pendant l'attente."""
    with console.status(f"[{ORANGE}]{label}[/]", spinner="dots", spinner_style=ORANGE):
        yield

# ───────────── composants ─────────────
def loading(message: str | None = None, duration: float = 1.2) -> None:
    message = message or random.choice(LOADING_MSGS)
    with Progress(
        SpinnerColumn("dots2", style=BLOOD_BRIGHT),
        TextColumn(f"[bold {ORANGE}]{{task.description}}[/]"),
        BarColumn(bar_width=34, style="#2a0000", complete_style=BLOOD_BRIGHT, finished_style=ORANGE),
        TextColumn(f"[{BONE}]{{task.percentage:>3.0f}}%[/]"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(message, total=100)
        steps = 50
        for _ in range(steps):
            progress.update(task, advance=100 / steps)
            time.sleep(duration / steps)

# ═════════════ menus — style terminal, sans descriptions ═════════════
def listing(title: str, rows: list[tuple[str, str, str]], footer: tuple[str, str] = ("0", "QUITTER")) -> Panel:
    """rows = [(touche, libellé, info à droite)]. Style ligne de commande, pas de tableau."""
    inner = max(console.width - 14, 30) - 8 - 10  # panneau - bordures/pad - colonne clé - colonne info
    grid = Table.grid(padding=0, expand=True)
    grid.add_column(width=6)
    grid.add_column(ratio=1, overflow="crop", no_wrap=True)
    grid.add_column(justify="right", width=10)
    for key, label, info in rows:
        grid.add_row(Text(f" [{key}] ", style=f"bold {BLOOD_BRIGHT}"),
                     Text.assemble((label, f"bold {BONE}")),
                     Text(info, style=f"bold {ORANGE}"))
    grid.add_row("", "", "")
    fkey, flabel = footer
    grid.add_row(Text(f" [{fkey}] ", style=f"bold {BLOOD_BRIGHT}"), Text(flabel, style=f"bold {BONE}"), "")
    return Panel(grid, title=Text(f" {title} ", style=f"bold {ORANGE}"), title_align="left",
                 border_style=BLOOD, box=box.HEAVY, padding=(1, 2))


# ═════════════ saisie ═════════════
class _ShellPrompt(Prompt):
    prompt_suffix = " "


def _erase_prev_line() -> None:
    """Remonte d'une ligne et l'efface."""
    console.file.write("\033[1A\r\033[2K")
    console.file.flush()


def shell_prompt(path: str, choices: list[str]) -> str:
    console.print()
    console.print(Text.assemble(("┌──(", ASH), (HOST, f"bold {BLOOD_BRIGHT}"), (")-[", ASH),
                                (path, f"bold {ORANGE}"), ("]", ASH)))
    error_shown = False
    while True:
        value = _ShellPrompt.ask(f"[{ASH}]└─[/][bold {BLOOD_BRIGHT}]$[/]").strip()
        if value in choices:
            if error_shown:           # nettoie le message d'erreur avant de continuer
                _erase_prev_line()    # ligne de saisie
                _erase_prev_line()    # ligne d'erreur
                console.print(Text.assemble(("└─", ASH), ("$ ", f"bold {BLOOD_BRIGHT}"), (value, BONE)))
            return value

        _erase_prev_line()            # efface la saisie invalide
        if error_shown:
            _erase_prev_line()        # efface l'ancien message d'erreur
        msg = f"'{value}' n'est pas un choix valide." if value else "Choix vide."
        console.print(Text.assemble(("✖ ", f"bold {BLOOD_BRIGHT}"), (msg, BLOOD_BRIGHT)))
        error_shown = True


def ask(label: str, **kw) -> str:
    return Prompt.ask(f"[bold {ORANGE}]❯[/] [{BONE}]{label}[/]", **kw)


def confirm(label: str, default: bool = False) -> bool:
    return Confirm.ask(f"[bold {ORANGE}]❯[/] [{BONE}]{label}[/]", default=default)


def pause() -> None:
    console.print()
    Prompt.ask(f"[{ASH}]── Entrée pour continuer ──[/]", default="", show_default=False)


# ═════════════ messages ═════════════
def _tag(sym: str, color: str, msg: str) -> None:
    t = Text.assemble((f"[{sym}]", f"bold {color}"), " ")
    t.append(str(msg), style=BONE)
    console.print(t)


def ok(msg: str) -> None:
    _tag("+", GOOD, msg)


def info(msg: str) -> None:
    _tag("*", ORANGE, msg)


def warn(msg: str) -> None:
    _tag("!", ORANGE, msg)


def err(msg: str) -> None:
    _tag("x", BLOOD_BRIGHT, msg)


def verdict(level: str, text: str) -> Text:
    sym, color = {"good": ("✔", GOOD), "mid": ("▲", ORANGE), "bad": ("✖", BLOOD_BRIGHT)}.get(level, ("•", ASH))
    return Text.assemble((f"{sym} ", f"bold {color}"), (text, color))


# ═════════════ résultats ═════════════
def _cell(v) -> object:
    return v if hasattr(v, "__rich_console__") else Text(str(v))


def kv_table(title: str, rows: list[tuple[str, object]]) -> None:
    t = Table(title=Text(title, style=f"bold {ORANGE}"), title_justify="left", box=box.ROUNDED,
              border_style=BLOOD, show_header=False, padding=(0, 1))
    t.add_column(style=f"bold {ORANGE}", no_wrap=True)
    t.add_column(style=BONE, overflow="fold")
    for k, v in rows:
        t.add_row(k, _cell(v))
    console.print(t)


def data_table(title: str, columns: list[str], rows: list[tuple], col_styles: list[str] | None = None) -> None:
    t = Table(title=Text(title, style=f"bold {ORANGE}"), title_justify="left", box=box.ROUNDED,
              border_style=BLOOD, header_style=f"bold {ORANGE}", padding=(0, 1))
    for i, c in enumerate(columns):
        t.add_column(c, style=(col_styles[i] if col_styles else BONE), overflow="fold")
    for r in rows:
        t.add_row(*[_cell(x) for x in r])
    console.print(t)


def mini_panel(title: str, rows: list[tuple[str, object]], height: int | None = None) -> Panel:
    g = Table.grid(padding=(0, 1), expand=True)
    g.add_column(style=f"bold {ORANGE}", no_wrap=True)
    g.add_column(style=BONE, overflow="ellipsis", no_wrap=True, ratio=1)
    for k, v in rows:
        g.add_row(k, _cell(v))
    return Panel(g, title=Text(f" {title} ", style=f"bold {ORANGE}"), title_align="left",
                 border_style=BLOOD, box=box.ROUNDED, padding=(0, 1), height=height)


def panel_grid(items: list[tuple[str, list[tuple[str, object]]]]) -> None:
    cols = 2 if console.width >= 100 else 1
    grid = Table.grid(expand=True, padding=(0, 1))
    for _ in range(cols):
        grid.add_column(ratio=1)
    for i in range(0, len(items), cols):
        chunk = items[i:i + cols]
        h = max(len(rows) for _, rows in chunk) + 2
        grid.add_row(*[mini_panel(title, rows, height=h) for title, rows in chunk])
    console.print(grid)


def info_panel(content, title: str = "", color: str = ORANGE) -> Panel:
    return Panel(content, title=Text(f" {title} ", style=f"bold {color}") if title else None,
                 title_align="left", border_style=BLOOD, box=box.ROUNDED, padding=(0, 2))


def offer_save(name: str, data) -> None:
    if not confirm("Sauvegarder le rapport dans reports/ ?", default=False):
        return
    folder = Path(__file__).resolve().parent.parent / "reports"
    folder.mkdir(exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:80]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if isinstance(data, str):
        path = folder / f"{safe}_{stamp}.txt"
        path.write_text(data, encoding="utf-8")
    else:
        path = folder / f"{safe}_{stamp}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    ok(f"Rapport enregistré : {path}")
