# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
TITLE = "MENACE SANTANA"
VERSION = "v1.0"
HOST = "menace@santana"          # affiché dans le prompt façon shell
TAGLINE = "« Les morts ne dorment jamais… »"

BLOOD = "#b30000"          # sang séché (bordures)
BLOOD_BRIGHT = "#ff1a1a"   # sang frais (accents, erreurs)
ORANGE = "#ff6a00"         # citrouille (titres)
ORANGE_DARK = "#c44a00"
BONE = "#e8dcc0"           # os (texte principal)
MUTED = "#a8a8a8"          # texte secondaire
ASH = "#6b6b6b"            # cendres (détails)
GOOD = "#5fd75f"           # résultat positif (vert terminal)

# Grande bannière (utilisée si la fenêtre fait au moins 36 lignes)
BANNER = r"""
███╗   ███╗███████╗███╗   ██╗ █████╗  ██████╗███████╗
████╗ ████║██╔════╝████╗  ██║██╔══██╗██╔════╝██╔════╝
██╔████╔██║█████╗  ██╔██╗ ██║███████║██║     █████╗
██║╚██╔╝██║██╔══╝  ██║╚██╗██║██╔══██║██║     ██╔══╝
██║ ╚═╝ ██║███████╗██║ ╚████║██║  ██║╚██████╗███████╗
╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝╚══════╝
""".strip("\n")

# Bannière compacte (2 lignes) pour les fenêtres plus petites
BANNER_COMPACT = [
    "█▀▄▀█  █▀▀  █▄ █  ▄▀█  █▀▀  █▀▀",
    "█ ▀ █  ██▄  █ ▀█  █▀█  █▄▄  ██▄",
]

LOADING_MSGS = [
    "Invocation des esprits", "Réveil des morts", "Ouverture du cercueil",
    "Offrande de sang", "Lecture du grimoire", "Les ombres approchent",
]