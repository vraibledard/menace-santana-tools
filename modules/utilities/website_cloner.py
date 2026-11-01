# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
from __future__ import annotations

import hashlib
import os
import re
import urllib.parse
from pathlib import Path

from core import net, ui

try:
    import requests
except ImportError:  # géré dans run()
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 120 * 1024 * 1024

ATTRS = ("src", "href", "data-src", "poster", "action", "data-bg")
CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.I)
SKIP_SCHEMES = ("data:", "mailto:", "tel:", "javascript:", "about:", "blob:")

TOOL = {
    "name": "Website cloner",
    "order": 1,
}


def _ext(url: str) -> str:
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    return ext if re.fullmatch(r"\.[a-z0-9]{1,6}", ext or "") else ".bin"


def _slug(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.replace(":", "_")
    return re.sub(r"[^a-z0-9._-]", "-", host.lower()) or "site"


def _local(url: str, base: str) -> str:
    if url.startswith(SKIP_SCHEMES) or url.startswith("#"):
        return url
    return urllib.parse.urljoin(base, url)


class Cloner:
    def __init__(self, outdir: Path, session, origin: str) -> None:
        self.out = outdir
        self.s = session
        self.origin = origin
        self.cache: dict[str, str] = {}
        self.pages = 0
        self.assets = 0
        self.octets = 0
        self.echecs: list[str] = []
        self.manifest: dict[str, str] = {}

    def _budget(self, size: int) -> bool:
        return self.octets + size <= MAX_TOTAL

    def _get(self, url: str):
        resp = self.s.get(url, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        return resp

    def asset(self, url: str, ref_dir: Path) -> str:
        """Télécharge une ressource, renvoie le lien relatif local (ou l'URL d'origine)."""
        if url in self.cache:
            return os.path.relpath(self.cache[url], ref_dir).replace(os.sep, "/")

        try:
            resp = self._get(url)
            blob = resp.content
            if len(blob) > MAX_FILE or not self._budget(len(blob)):
                self.echecs.append(f"volume: {url}")
                return url
        except Exception as exc:
            self.echecs.append(f"{url} ({type(exc).__name__})")
            return url

        ctype = resp.headers.get("Content-Type", "")
        if "css" in ctype:
            blob = self._rewrite_css(blob.decode(resp.encoding or "utf-8", "replace"), url).encode("utf-8")

        name = hashlib.sha1(url.encode()).hexdigest()[:12] + _ext(url)
        dest = self.out / "assets" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)

        self.cache[url] = str(dest)
        self.assets += 1
        self.octets += len(blob)
        self.manifest[url] = str(dest.relative_to(self.out))
        return os.path.relpath(dest, ref_dir).replace(os.sep, "/")

    def _rewrite_css(self, css: str, css_url: str) -> str:
        def repl(m: re.Match) -> str:
            raw = m.group(1).strip()
            if raw.startswith(SKIP_SCHEMES):
                return m.group(0)
            link = self.asset(urllib.parse.urljoin(css_url, raw), self.out / "assets")
            return f'url("{link}")'

        return CSS_URL.sub(repl, css)

    def page(self, url: str, depth: int, links: list) -> str:
        """Télécharge et réécrit une page HTML, renvoie son chemin local."""
        resp = self._get(url)
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype:
            raise ValueError("pas du HTML")

        base = resp.url
        html = resp.text
        page_dir = self.out / "pages"
        page_dir.mkdir(parents=True, exist_ok=True)

        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            for base_tag in soup.find_all("base"):
                if base_tag.get("href"):
                    base = urllib.parse.urljoin(base, base_tag["href"])
            for tag in soup.find_all(True):
                for attr in ATTRS:
                    val = tag.get(attr)
                    if not isinstance(val, str) or not val.strip():
                        continue
                    absu = _local(val.strip(), base)
                    if absu.startswith(("#",) + SKIP_SCHEMES):
                        continue
                    if attr == "href" and depth > 0 and absu.startswith(self.origin):
                        links.append(absu)
                        tag[attr] = absu
                    else:
                        tag[attr] = self.asset(absu, page_dir)
                srcset = tag.get("srcset")
                if isinstance(srcset, str):
                    parts = []
                    for cand in srcset.split(","):
                        bits = cand.strip().split()
                        if not bits:
                            continue
                        bits[0] = self.asset(urllib.parse.urljoin(base, bits[0]), page_dir)
                        parts.append(" ".join(bits))
                    tag["srcset"] = ", ".join(parts)
                style = tag.get("style")
                if isinstance(style, str) and "url(" in style:
                    tag["style"] = self._rewrite_css(style, base)
            for st in soup.find_all("style"):
                st.string = self._rewrite_css(st.get_text(), base)
            html = str(soup)
        else:
            html = CSS_URL.sub(lambda m: f'url("{self.asset(urllib.parse.urljoin(base, m.group(1)), page_dir)}")', html)
            for attr in ATTRS:
                html = re.sub(
                    rf'({attr}\s*=\s*["\'])([^"\']+)',
                    lambda m: m.group(1) + self.asset(urllib.parse.urljoin(base, m.group(2)), page_dir),
                    html,
                )

        name = "index" if self.pages == 0 else hashlib.sha1(url.encode()).hexdigest()[:12]
        dest = page_dir / f"{name}.html"
        dest.write_text(html, encoding="utf-8")
        self.pages += 1
        self.octets += len(html.encode())
        self.manifest[url] = str(dest.relative_to(self.out))
        return str(dest)


def run() -> None:
    if requests is None:
        ui.kv_table(
            "Résultat",
            [("Statut", ui.verdict("bad", "dépendance manquante")), ("Correctif", "pip install requests beautifulsoup4")],
        )
        return

    cible = (ui.ask("URL à cloner") or "").strip()
    if not cible:
        ui.kv_table("Résultat", [("Statut", ui.verdict("bad", "aucune saisie"))])
        return
    if "://" not in cible:
        cible = "https://" + cible

    parsed = urllib.parse.urlparse(cible)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        ui.kv_table("Résultat", [("URL", cible), ("Statut", ui.verdict("bad", "URL invalide"))])
        return

    prof = (ui.ask("Profondeur de liens (0 = page seule)") or "0").strip()
    depth = max(0, min(int(prof) if prof.isdigit() else 0, 3))
    max_pages = 1 if depth == 0 else max(1, min(200, depth * 30))

    racine = Path.cwd() / "clones"
    outdir = racine / _slug(cible)

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "fr,en;q=0.8"})
    origin = f"{parsed.scheme}://{parsed.netloc}"

    cloner = Cloner(outdir, session, origin)
    vus: set[str] = {cible}
    file: list[tuple[str, int]] = [(cible, 0)]
    erreur = ""

    with ui.working("Clonage"):
        try:
            while file and cloner.pages < max_pages:
                url, d = file.pop(0)
                liens: list[str] = []
                try:
                    cloner.page(url, max(0, depth - d), liens)
                except Exception as exc:
                    cloner.echecs.append(f"{url} ({type(exc).__name__})")
                    if not erreur:
                        erreur = f"{type(exc).__name__}: {exc}"
                    continue
                for lien in liens:
                    propre = lien.split("#")[0]
                    if propre not in vus and len(vus) < max_pages * 4:
                        vus.add(propre)
                        file.append((propre, d + 1))
        finally:
            session.close()

    if cloner.pages == 0:
        ui.kv_table(
            "Résultat",
            [("URL", cible), ("Statut", ui.verdict("bad", "échec du clonage")), ("Détail", erreur or "voir ci-dessous")],
        )
        if cloner.echecs:
            ui.kv_table("Échecs", [("cible", e) for e in cloner.echecs[:10]])
        return

    (outdir / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
    import json

    (outdir / "manifest.json").write_text(
        json.dumps({"source": cible, "pages": cloner.pages, "ressources": cloner.manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ui.kv_table(
        "Résultat",
        [
            ("Source", cible),
            ("Dossier", str(outdir)),
            ("Entrée", str(outdir / "pages" / "index.html")),
            ("Pages", str(cloner.pages)),
            ("Ressources", str(cloner.assets)),
            ("Volume", f"{cloner.octets / 1024:.0f} Ko"),
            ("Échecs", ui.verdict("warn", str(len(cloner.echecs))) if cloner.echecs else ui.verdict("good", "aucun")),
            ("Rendu", ui.verdict("warn", "statique — JS non exécuté")),
        ],
    )

    if cloner.echecs:
        ui.kv_table("Échecs", [("cible", e) for e in cloner.echecs[:10]])

    ui.offer_save(
        "clone_" + _slug(cible),
        {"source": cible, "dossier": str(outdir), "pages": cloner.pages, "ressources": cloner.assets, "echecs": cloner.echecs},
    )