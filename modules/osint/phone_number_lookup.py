# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
from __future__ import annotations

import os
import urllib.parse

from core import net, ui

try:
    import phonenumbers
    from phonenumbers import carrier as pn_carrier
    from phonenumbers import geocoder as pn_geocoder
    from phonenumbers import timezone as pn_timezone
except ImportError:  # lib absente : géré dans run()
    phonenumbers = None

TOOL = {
    "name": "Phone Number lookup",
    "order": 3,
}

_TYPE_LABELS = {
    "FIXED_LINE": ("good", "Fixe"),
    "MOBILE": ("good", "Mobile"),
    "FIXED_LINE_OR_MOBILE": ("warn", "Fixe ou mobile (indéterminé)"),
    "TOLL_FREE": ("warn", "Numéro gratuit"),
    "PREMIUM_RATE": ("warn", "Numéro surtaxé"),
    "SHARED_COST": ("warn", "Coût partagé"),
    "VOIP": ("warn", "VoIP"),
    "PERSONAL_NUMBER": ("warn", "Numéro personnel"),
    "PAGER": ("warn", "Pager"),
    "UAN": ("warn", "UAN"),
    "VOICEMAIL": ("warn", "Messagerie vocale"),
    "UNKNOWN": ("bad", "Inconnu"),
}

_TYPES = (
    {getattr(phonenumbers.PhoneNumberType, k): v for k, v in _TYPE_LABELS.items()}
    if phonenumbers
    else {}
)


def _fill(data: dict, num) -> None:
    """Remplit le dict de résultats à partir d'un numéro déjà parsé."""
    e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    data["e164"] = e164
    data["valid"] = phonenumbers.is_valid_number(num)
    data["possible"] = phonenumbers.is_possible_number(num)
    data["national"] = phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.NATIONAL
    )
    data["intl"] = phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )
    data["rfc"] = phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.RFC3966
    )
    data["cc"] = num.country_code
    data["region"] = phonenumbers.region_code_for_number(num) or "—"
    data["carrier"] = pn_carrier.name_for_number(num, "en") or "—"
    data["geo"] = pn_geocoder.description_for_number(num, "fr") or "—"
    data["tz"] = ", ".join(pn_timezone.time_zones_for_number(num)) or "—"
    data["type"] = _TYPES.get(phonenumbers.number_type(num), ("bad", "Inconnu"))
    data["len"] = len(phonenumbers.national_significant_number(num))


def _online(e164: str, key: str) -> dict:
    """Vérification en ligne via numverify (clé requise)."""
    import requests

    try:
        resp = requests.get(
            "https://apilayer.net/api/validate",
            params={"access_key": key, "number": e164, "format": 1},
            timeout=12,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise net.NetError(f"numverify injoignable : {exc}") from exc


def run() -> None:
    if phonenumbers is None:
        ui.kv_table(
            "Résultat",
            [
                ("Statut", ui.verdict("bad", "dépendance manquante")),
                ("Correctif", "pip install phonenumbers"),
            ],
        )
        return

    raw = (ui.ask("Numéro (+33 6 …, 06 …)") or "").strip()
    if not raw:
        ui.kv_table("Résultat", [("Statut", ui.verdict("bad", "aucune saisie"))])
        return

    region = None
    if not raw.startswith("+"):
        region = (ui.ask("Région par défaut (ex FR)") or "FR").strip().upper()

    data: dict = {}
    with ui.working("Analyse"):
        try:
            num = phonenumbers.parse(raw, region)
        except phonenumbers.NumberParseException as exc:
            data["error"] = f"illisible — {exc}"
        else:
            _fill(data, num)
            key = os.environ.get("NUMVERIFY_KEY", "").strip()
            if key and data["possible"]:
                data["online"] = _online(data["e164"], key)

    if "error" in data:
        ui.kv_table(
            "Résultat",
            [("Saisie", raw), ("Statut", ui.verdict("bad", data["error"]))],
        )
        return

    if data["valid"]:
        statut = ("good", "numéro valide")
    elif data["possible"]:
        statut = ("warn", "plausible, attribution non confirmée")
    else:
        statut = ("bad", "invalide")

    ui.kv_table(
        "Résultat",
        [
            ("Saisie", raw),
            ("Statut", ui.verdict(*statut)),
            ("Type de ligne", ui.verdict(*data["type"])),
            ("E.164", data["e164"]),
            ("International", data["intl"]),
            ("National", data["national"]),
            ("RFC 3966", data["rfc"]),
            ("Indicatif", f"+{data['cc']}"),
            ("Région", data["region"]),
            ("Opérateur", data["carrier"]),
            ("Zone", data["geo"]),
            ("Fuseaux", data["tz"]),
            ("Longueur nationale", str(data["len"])),
        ],
    )

    online = data.get("online") or {}
    if online:
        ui.kv_table(
            "Vérification en ligne",
            [
                ("Opérateur", str(online.get("carrier") or "—")),
                ("Pays", str(online.get("country_name") or "—")),
                ("Localité", str(online.get("location") or "—")),
                ("Type", str(online.get("line_type") or "—")),
            ],
        )

    digits = data["e164"].lstrip("+")
    q = urllib.parse.quote(data["e164"])
    ui.kv_table(
        "Empreinte",
        [
            ("WhatsApp", f"https://wa.me/{digits}"),
            ("Telegram", f"https://t.me/+{digits}"),
            ("Google", f"https://www.google.com/search?q=%22{q}%22"),
            ("Truecaller", f"https://www.truecaller.com/search/{data['region'].lower()}/{digits}"),
            ("Sync.me", f"https://sync.me/search/?number={digits}"),
        ],
    )

    ui.offer_save(
        "phone_" + digits,
        {
            "saisie": raw,
            "e164": data["e164"],
            "valide": data["valid"],
            "type": data["type"][1],
            "operateur": data["carrier"],
            "region": data["region"],
            "zone": data["geo"],
            "fuseaux": data["tz"],
        },
    )