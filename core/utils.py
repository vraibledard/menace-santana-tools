# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
from __future__ import annotations

import ipaddress
import random
import re
from urllib.parse import urlparse

_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}$")


def clean_domain(raw: str) -> str | None:
    """'https://WWW.Example.com:443/page' -> 'www.example.com' (None si invalide)."""
    raw = (raw or "").strip().lower()
    if not raw:
        return None
    if "://" not in raw:
        raw = "//" + raw
    host = (urlparse(raw).hostname or "").strip(".")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    return host if _DOMAIN_RE.match(host) else None


def normalize_url(raw: str) -> str | None:
    """Ajoute https:// si besoin. None si l'URL est invalide."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "https://" + raw
    p = urlparse(raw)
    return raw if p.scheme in ("http", "https") and p.hostname else None


def is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


def random_username(suffix: bool = True) -> str:
    adj = ["Blood", "Grim", "Hollow", "Cursed", "Rotten", "Crimson", "Wicked", "Night", "Bone", "Dread"]
    noun = ["Reaper", "Wraith", "Banshee", "Ghoul", "Vampire", "Zombie", "Specter", "Witch", "Raven", "Phantom"]
    name = random.choice(adj) + random.choice(noun)
    return name + (str(random.randint(13, 99)) if suffix else "")
