# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

UA = "Mozilla/5.0 (compatible; MenaceToolkit/1.0)"


class NetError(Exception):
    """Erreur réseau lisible (affichée telle quelle à l'utilisateur)."""


@dataclass
class Response:
    status: int
    headers: Any      # email.message.Message : .get() insensible à la casse
    body: bytes
    url: str          # URL finale (après redirections)

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        try:
            return json.loads(self.body)
        except ValueError as e:
            raise NetError("Réponse JSON invalide.") from e


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url: str, *, method: str = "GET", headers: dict | None = None, data: bytes | None = None,
          timeout: float = 15, follow: bool = True, max_bytes: int = 2_000_000) -> Response:
    """Requête HTTP. Ne lève pas d'erreur sur les codes 4xx/5xx (voir .status)."""
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": UA, **(headers or {})})
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as r:
            return Response(r.status, r.headers, r.read(max_bytes), r.geturl())
    except urllib.error.HTTPError as e:
        try:
            body = e.read(max_bytes)
        except Exception:
            body = b""
        return Response(e.code, e.headers, body, e.geturl() or url)
    except urllib.error.URLError as e:
        raise NetError(f"Connexion impossible : {e.reason}") from e
    except (TimeoutError, socket.timeout) as e:
        raise NetError("Délai dépassé (le serveur ne répond pas).") from e
    except (ValueError, OSError) as e:
        raise NetError(f"Requête impossible : {e}") from e


def get_json(url: str, **kw) -> tuple[int, Any]:
    """Retourne (status, données) ; données = None si la réponse n'est pas du JSON."""
    r = fetch(url, **kw)
    try:
        return r.status, r.json()
    except NetError:
        return r.status, None


# ───────────── DNS over HTTPS (Cloudflare) ─────────────
TYPE_NUM = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "PTR": 12, "MX": 15, "TXT": 16, "AAAA": 28, "CAA": 257}


def doh(name: str, rtype: str = "A") -> tuple[int, list[dict]]:
    """Résolution DNS via HTTPS. Retourne (code DNS, réponses du type demandé). Code 3 = NXDOMAIN."""
    qs = urllib.parse.urlencode({"name": name, "type": rtype})
    r = fetch(f"https://cloudflare-dns.com/dns-query?{qs}", headers={"Accept": "application/dns-json"}, timeout=10)
    if r.status != 200:
        raise NetError(f"Résolveur DNS indisponible (HTTP {r.status}).")
    data = r.json()
    want = TYPE_NUM.get(rtype)
    return data.get("Status", 0), [a for a in data.get("Answer", []) if a.get("type") == want]


def txt_value(data: str) -> str:
    """Un enregistrement TXT arrive sous la forme "abc" "def" → abcdef."""
    return re.sub(r'"\s+"', "", str(data)).strip('"')
