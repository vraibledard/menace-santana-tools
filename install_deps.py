# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Paquets indispensables pour lancer main.py
ALWAYS = ["rich"]

# nom d'import -> nom du paquet pip (quand ils sont différents)
PIP_NAMES = {
    "discord": "discord.py", "websocket": "websocket-client", "PIL": "pillow",
    "cv2": "opencv-python", "bs4": "beautifulsoup4", "yaml": "pyyaml",
    "dotenv": "python-dotenv", "win32api": "pywin32", "win32con": "pywin32",
    "win32gui": "pywin32", "Crypto": "pycryptodome", "sklearn": "scikit-learn",
    "serial": "pyserial", "dateutil": "python-dateutil", "attr": "attrs",
    "OpenSSL": "pyopenssl", "magic": "python-magic",
    "googleapiclient": "google-api-python-client",
}

SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules", "site-packages", "reports"}
STDLIB = getattr(sys, "stdlib_module_names", set())


def imported_names() -> set[str]:
    """Tous les modules importés dans les .py du projet."""
    found: set[str] = set()
    for f in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in f.relative_to(ROOT).parts):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return found


def find_missing() -> dict[str, str]:
    """Retourne {nom_d_import: nom_pip} pour tout ce qui n'est pas installé."""
    # Seulement la racine : core/, modules/, main.py... (pas modules/discord !)
    local = {p.stem for p in ROOT.iterdir() if p.suffix == ".py" or p.is_dir()}
    missing: dict[str, str] = {}
    for name in sorted(imported_names() | set(ALWAYS)):
        if name in STDLIB or name in local or name == "__future__":
            continue
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            spec = None
        if spec is None:
            missing[name] = PIP_NAMES.get(name, name)
    return missing


def main() -> int:
    os.system("")  # active les couleurs ANSI sous Windows
    missing = find_missing()
    if not missing:
        return 0

    packages = sorted(set(missing.values()))
    print(f"\033[93m[*]\033[0m Installation des dépendances manquantes : {', '.join(packages)}\n")

    for pkg in packages:
        print(f"    → {pkg} ...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-q", pkg],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("\033[92mOK\033[0m")
        else:
            print("\033[91mÉCHEC\033[0m")
            print(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "")
            if pkg in ALWAYS:  # sans rich, impossible de lancer le menu
                return 1
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
