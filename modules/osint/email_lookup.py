# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
from __future__ import annotations

import hashlib
import os
import re
import urllib.parse

from core import net, ui

try:
    import dns.exception
    import dns.resolver
except ImportError:
    dns = None

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")

_DISPOSABLE = {
    "mailinator.com", "yopmail.com", "guerrillamail.com", "sharklasers.com",
    "10minutemail.com", "tempmail.com", "temp-mail.org", "trashmail.com",
    "maildrop.cc", "getnada.com", "dispostable.com", "mintemail.com",
    "discard.email", "mohmal.com", "emailondeck.com", "spam4.me",
    "grr.la", "throwawaymail.com", "mailnesia.com", "fakeinbox.com",
}

_FREE = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "hotmail.fr",
    "live.com", "live.fr", "yahoo.com", "yahoo.fr", "ymail.com", "aol.com",
    "icloud.com", "me.com", "protonmail.com", "proton.me", "pm.me",
    "gmx.com", "gmx.de", "gmx.fr", "web.de", "free.fr", "orange.fr",
    "laposte.net", "wanadoo.fr", "sfr.fr", "mail.ru", "yandex.ru", "qq.com", "163.com",
}

_PROVIDERS = {
    "google.com": "Google Workspace",
    "googlemail.com": "Google Workspace",
    "outlook.com": "Microsoft 365",
    "protection.outlook.com": "Microsoft 365",
    "protonmail.ch": "Proton",
    "proton.me": "Proton",
    "zoho.com": "Zoho",
    "zohomail.com": "Zoho",
    "mimecast.com": "Mimecast",
    "pphosted.com": "Proofpoint",
    "messagelabs.com": "Broadcom/Symantec",
    "barracudanetworks.com": "Barracuda",
    "ovh.net": "OVH",
    "ionos.com": "IONOS",
    "one.com": "One.com",
}

TOOL = {
    "name": "Email lookup",
    "order": 4,
}


def _resolver():
    res = dns.resolver.Resolver()
    res.lifetime = 6.0
    res.timeout = 6.0
    return res


def _mx(domain: str) -> list[tuple[int, str]]:
    try:
        return sorted(
            (int(r.preference), str(r.exchange).rstrip("."))
            for r in _resolver().resolve(domain, "MX")
        )
    except Exception:
        return []


def _txt(name: str) -> list[str]:
    try:
        answers = _resolver().resolve(name, "TXT")
    except Exception:
        return []
    out = []
    for rec in answers:
        try:
            out.append(b"".join(rec.strings).decode("utf-8", "replace"))
        except Exception:
            out.append(str(rec))
    return out


def _has_a(domain: str) -> bool:
    try:
        _resolver().resolve(domain, "A")
        return True
    except Exception:
        return False


def _gravatar(normalized: str) -> bool:
    import requests

    digest = hashlib.md5(normalized.encode()).hexdigest()
    try:
        resp = requests.get(
            f"https://gravatar.com/avatar/{digest}",
            params={"d": "404", "s": "200"},
            timeout=10,
            allow_redirects=True,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _hibp(email: str, key: str) -> dict:
    import requests

    try:
        resp = requests.get(
            "https://haveibeenpwned.com/api/v3/breachedaccount/"
            + urllib.parse.quote(email, safe=""),
            params={"truncateResponse": "false"},
            headers={"hibp-api-key": key, "User-Agent": "menace-santana"},
            timeout=15,
        )
    except Exception as exc:
        raise net.NetError(f"haveibeenpwned injoignable : {exc}") from exc
    if resp.status_code == 404:
        return {"count": 0, "breaches": []}
    if resp.status_code != 200:
        return {"count": -1, "breaches": [], "code": resp.status_code}
    items = resp.json()
    return {"count": len(items), "breaches": items}


def _provider(mx: list[tuple[int, str]]) -> str:
    for _, host in mx:
        for suffix, label in _PROVIDERS.items():
            if host == suffix or host.endswith("." + suffix):
                return label
    return "—"


def run() -> None:
    if dns is None:
        ui.kv_table(
            "Résultat",
            [
                ("Statut", ui.verdict("bad", "dépendance manquante")),
                ("Correctif", "pip install dnspython requests"),
            ],
        )
        return

    raw = (ui.ask("Adresse email") or "").strip()
    if not raw:
        ui.kv_table("Résultat", [("Statut", ui.verdict("bad", "aucune saisie"))])
        return

    if not _RE_EMAIL.match(raw):
        ui.kv_table(
            "Résultat",
            [("Saisie", raw), ("Statut", ui.verdict("bad", "syntaxe invalide"))],
        )
        return

    local, domain = raw.rsplit("@", 1)
    normalized = f"{local.lower()}@{domain.lower()}"
    data: dict = {"saisie": raw, "normalized": normalized, "domain": domain.lower()}

    with ui.working("Analyse"):
        mx = _mx(data["domain"])
        data["mx"] = mx
        data["a"] = _has_a(data["domain"])
        data["spf"] = [t for t in _txt(data["domain"]) if t.lower().startswith("v=spf1")]
        data["dmarc"] = [t for t in _txt(f"_dmarc.{data['domain']}") if t.lower().startswith("v=dmarc1")]
        data["gravatar"] = _gravatar(normalized)

        key = os.environ.get("HIBP_API_KEY", "").strip()
        if key:
            data["hibp"] = _hibp(normalized, key)

    domain = data["domain"]
    if domain in _DISPOSABLE:
        domaine_verdict = ("warn", "jetable")
    elif domain in _FREE:
        domaine_verdict = ("good", "grand public")
    elif mx:
        domaine_verdict = ("good", "domaine privé")
    else:
        domaine_verdict = ("bad", "sans MX")

    if mx and data["a"]:
        statut = ("good", "domaine délivrable")
    elif mx:
        statut = ("warn", "MX présent, pas de A")
    else:
        statut = ("bad", "aucun MX — adresse probablement morte")

    ui.kv_table(
        "Résultat",
        [
            ("Saisie", raw),
            ("Normalisé", normalized),
            ("Statut", ui.verdict(*statut)),
            ("Domaine", ui.verdict(*domaine_verdict)),
            ("Partie locale", local),
            ("Alias (+tag)", "oui" if "+" in local else "non"),
            ("Hébergeur mail", _provider(mx)),
            ("SPF", ui.verdict("good", "présent") if data["spf"] else ui.verdict("warn", "absent")),
            ("DMARC", ui.verdict("good", "présent") if data["dmarc"] else ui.verdict("warn", "absent")),
            ("Gravatar", ui.verdict("good", "profil existant") if data["gravatar"] else ui.verdict("warn", "aucun")),
        ],
    )

    if mx:
        ui.kv_table("Enregistrements MX", [(str(pref), host) for pref, host in mx[:8]])

    if data["spf"]:
        ui.kv_table("SPF", [("brut", t[:120]) for t in data["spf"]])
    if data["dmarc"]:
        ui.kv_table("DMARC", [("brut", t[:120]) for t in data["dmarc"]])

    hibp = data.get("hibp") or {}
    if hibp.get("count", -1) == 0:
        ui.kv_table("Fuites", [("État", ui.verdict("good", "aucune fuite connue"))])
    elif hibp.get("count", 0) > 0:
        lignes = [
            (b.get("Name", "?"), f"{b.get('BreachDate', '?')} — {b.get('PwnCount', '?')} comptes")
            for b in hibp["breaches"][:10]
        ]
        ui.kv_table("Fuites", [("Total", str(hibp["count"]))] + lignes)
    elif hibp.get("code"):
        ui.kv_table("Fuites", [("État", ui.verdict("warn", f"API HTTP {hibp['code']}"))])

    q = urllib.parse.quote(normalized)
    digest = hashlib.md5(normalized.encode()).hexdigest()
    ui.kv_table(
        "Empreinte",
        [
            ("Google", f"https://www.google.com/search?q=%22{q}%22"),
            ("GitHub", f"https://github.com/search?q={q}&type=users"),
            ("X", f"https://x.com/search?q={q}"),
            ("Gravatar", f"https://gravatar.com/{digest}"),
            ("HIBP", f"https://haveibeenpwned.com/account/{q}"),
            ("Epieos", f"https://epieos.com/?q={q}&t=email"),
        ],
    )

    ui.offer_save(
        "email_" + normalized.replace("@", "_at_").replace(".", "_"),
        {
            "saisie": raw,
            "normalise": normalized,
            "domaine": domain,
            "mx": [host for _, host in mx],
            "spf": data["spf"],
            "dmarc": data["dmarc"],
            "gravatar": data["gravatar"],
            "fuites": hibp.get("count"),
        },
    )