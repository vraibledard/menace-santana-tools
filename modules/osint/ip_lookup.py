# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
import requests
from rich.table import Table
from core import ui
from core.theme import ORANGE

TOOL = {
    "name": "Ip Lookup / Domaine",
    "order": 2,
}


def run() -> None:
    ip = ui.ask("Adresse IP / Domaine")
    ui.loading("Interrogation", 0.5)
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,reverse,proxy,hosting,query"},
            timeout=10,
        ).json()
    except Exception as e:
        ui.console.print(f"[red]Erreur réseau : {e}[/]")
        return
    if r.get("status") != "success":
        ui.console.print(f"[red]Échec : {r.get('message')}[/]")
        return

    t = Table(show_header=False, border_style=ORANGE)
    for k, v in [
        ("IP", r["query"]), ("Pays", r["country"]), ("Région", r["regionName"]),
        ("Ville", r["city"]), ("Code postal", r["zip"]),
        ("Coordonnées", f'{r["lat"]}, {r["lon"]}'), ("Fuseau", r["timezone"]),
        ("FAI", r["isp"]), ("Organisation", r["org"]), ("ASN", r["as"]),
        ("Reverse DNS", r["reverse"] or "-"),
        ("Proxy/VPN", r["proxy"]), ("Hébergeur/DC", r["hosting"]),
    ]:
        t.add_row(f"[bold {ORANGE}]{k}[/]", str(v))
    ui.console.print(t)
    ui.console.print(f"[dim]Carte : https://www.openstreetmap.org/?mlat={r['lat']}&mlon={r['lon']}[/]")