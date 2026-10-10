#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Web Time Capsule / Webseiten-Zeitkapsel 3.1.0

Crawls publicly accessible website pages and can submit them to the Wayback
Machine. Failures and redirects are logged separately.
Durchsucht öffentliche Webseiten und kann sie an die Wayback Machine übergeben.
Fehler und Weiterleitungen werden getrennt protokolliert.
Standard library only; no additional Python packages required.
"""
from __future__ import annotations

import argparse
import csv
import getpass
import html
import ipaddress
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

VERSION = "3.1.0"
USER_AGENT = f"WebTimeCapsule/{VERSION} (public-page crawler; polite request rate)"
WAYBACK_SAVE = "https://web.archive.org/save/"
URL_FILE_DEFAULT = "archiv_urls.txt"
LOG_FILE_DEFAULT = "wayback_archiv_log.csv"
ERROR_FILE_DEFAULT = "website_fehler_details.txt"
CRAWL_FAILED_FILE_DEFAULT = "website_fehlgeschlagen.txt"
CRAWL_REDIRECT_FILE_DEFAULT = "website_weiterleitungen.csv"
ARCHIVE_FAILED_FILE_DEFAULT = "archiv_fehlgeschlagen.txt"
ARCHIVE_REDIRECT_FILE_DEFAULT = "archiv_weiterleitungen.csv"
PENDING_FILE_DEFAULT = "archiv_ausstehend.txt"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
REDIRECT_CODES = {301, 302, 303, 307, 308}
DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".csv",
    ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp", ".epub"
}
ASSET_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".bmp", ".tif", ".tiff",
    ".mp3", ".mp4", ".mov", ".avi", ".wmv", ".wav", ".ogg", ".webm",
    ".css", ".js", ".mjs", ".map", ".woff", ".woff2", ".ttf", ".eot", ".svg"
}
SKIP_QUERY_KEYS = {"phpsessid", "sessionid", "sid", "jsessionid", "csrf", "_csrf", "token"}


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Lässt 3xx-Antworten sichtbar, statt automatisch zum Ziel zu springen."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def ask_yes_no(question: str, default: bool = False) -> bool:
    """Einfache Ja/Nein-Frage. Der Standard gilt bei leerer Eingabe."""
    hint = "J/n" if default else "j/N"
    try:
        answer = input(f"{question} ({hint}): ").strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in {"j", "ja", "y", "yes"}


def host_of(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def is_safe_public_host(host: str) -> bool:
    """Verhindert versehentliche Zugriffe auf offensichtliche lokale Ziele."""
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".test")):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True


def prepare_start_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Bitte zuerst eine Website-Adresse eingeben.")
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Bitte eine gültige öffentliche http://- oder https://-Adresse eingeben.")
    if parsed.username or parsed.password:
        raise ValueError("Bitte keine Login-Daten in die URL schreiben.")
    if not is_safe_public_host(parsed.hostname.lower()):
        raise ValueError("Bitte eine öffentliche Website-Adresse eingeben.")
    normalized = normalize_url(raw, raw, allowed_hosts=None)
    if not normalized:
        raise ValueError("Die Startadresse ist ungültig.")
    return normalized


def normalize_url(raw_url: str, base_url: str, allowed_hosts: Optional[set[str]] = None,
                  allowed_suffix: Optional[str] = None) -> Optional[str]:
    raw_url = html.unescape((raw_url or "").strip())
    if not raw_url or raw_url.startswith(("#", "javascript:", "mailto:", "tel:", "data:", "blob:", "about:")):
        return None
    try:
        joined = urllib.parse.urljoin(base_url, raw_url)
        p = urllib.parse.urlsplit(joined)
    except ValueError:
        return None
    if p.scheme.lower() not in {"http", "https"} or not p.hostname or p.username or p.password:
        return None
    host = (p.hostname or "").lower().rstrip(".")
    if not is_safe_public_host(host):
        return None
    if allowed_hosts is not None and host not in allowed_hosts:
        if not (allowed_suffix and (host == allowed_suffix or host.endswith("." + allowed_suffix))):
            return None
    query = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
    query = [(k, v) for k, v in query if not k.lower().startswith("utm_") and k.lower() not in SKIP_QUERY_KEYS]
    query.sort()
    path = p.path or "/"
    try:
        port = p.port
    except ValueError:
        return None
    netloc = host
    if port and not ((p.scheme.lower() == "https" and port == 443) or (p.scheme.lower() == "http" and port == 80)):
        netloc = f"{host}:{port}"
    normalized = p._replace(netloc=netloc, path=path, query=urllib.parse.urlencode(query, doseq=True), fragment="")
    return urllib.parse.urlunsplit(normalized)


def header_value(headers: dict, wanted: str) -> str:
    for key, value in headers.items():
        if key.lower() == wanted.lower():
            return str(value)
    return ""


def request_bytes(url: str, timeout: int = 20, headers: Optional[dict] = None,
                  follow_redirects: bool = True, limit_bytes: int = MAX_RESPONSE_BYTES) -> tuple[int, dict, bytes, str]:
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml,text/xml,application/pdf,*/*;q=0.4",
    }
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, headers=request_headers)
    opener = urllib.request.build_opener() if follow_redirects else urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(req, timeout=timeout) as response:
            body = response.read(max(1, limit_bytes + 1))
            return response.status, dict(response.headers.items()), body[:limit_bytes], response.geturl()
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(min(500_000, max(1, limit_bytes + 1)))
        except Exception:
            body = b""
        return exc.code, dict(exc.headers.items()) if exc.headers else {}, body[:limit_bytes], exc.geturl()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, {}, b"", str(exc)


def decode_body(body: bytes, headers: dict) -> str:
    charset = None
    content_type = header_value(headers, "Content-Type")
    match = re.search(r"charset\s*=\s*[\"']?([^;\s\"']+)", content_type, re.I)
    if match:
        charset = match.group(1)
    if charset:
        try:
            return body.decode(charset, errors="replace")
        except LookupError:
            pass
    for encoding in ("utf-8", "cp1252", "iso-8859-1"):
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def looks_like_document(url: str) -> bool:
    return Path(urllib.parse.urlsplit(url).path.lower()).suffix in DOCUMENT_EXTENSIONS


def looks_like_asset(url: str) -> bool:
    return Path(urllib.parse.urlsplit(url).path.lower()).suffix in ASSET_EXTENSIONS


def looks_like_html_url(url: str) -> bool:
    suffix = Path(urllib.parse.urlsplit(url).path.lower()).suffix
    if suffix in DOCUMENT_EXTENSIONS or suffix in ASSET_EXTENSIONS:
        return False
    return suffix in {"", ".html", ".htm", ".xhtml", ".php", ".asp", ".aspx", ".jsp", ".shtml", ".cgi", ".pl", ".do", ".action"}


def full_redirect_target(url: str, headers: dict) -> str:
    location = header_value(headers, "Location")
    if not location:
        return ""
    return urllib.parse.urljoin(url, location.strip())


def same_site_alias(url_a: str, url_b: str) -> bool:
    """Returns true only for the same host or its plain www alias."""
    a = host_of(url_a)
    b = host_of(url_b)
    return a.removeprefix("www.") == b.removeprefix("www.") and bool(a and b)


def page_identity(url: str) -> tuple[str, str, tuple[tuple[str, str], ...], Optional[int]]:
    """Compare logical page identity without mistaking a redirect to / for success."""
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower().removeprefix("www.")
    path = p.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    query = tuple(sorted(urllib.parse.parse_qsl(p.query, keep_blank_values=True)))
    try:
        port = p.port
    except ValueError:
        port = None
    if port in (80, 443):
        port = None
    return host, path, query, port


def same_page(url_a: str, url_b: str) -> bool:
    try:
        return page_identity(url_a) == page_identity(url_b)
    except ValueError:
        return url_a == url_b


def original_from_snapshot(snapshot_url: str) -> str:
    """Extract the original URL from a Wayback snapshot link, if available."""
    if not snapshot_url:
        return ""
    try:
        path = urllib.parse.urlsplit(snapshot_url).path
    except ValueError:
        return ""
    match = re.match(r"^/web/(?:\d{1,14}|id_?)/(.+)$", path)
    if not match:
        return ""
    original = match.group(1)
    if original.startswith(("http://", "https://")):
        return original
    return ""


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = dict(attrs)
        tag = tag.lower()
        if tag in {"a", "area", "link"} and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"])
        elif tag in {"iframe", "frame", "script", "img", "source"} and attrs_dict.get("src"):
            self.links.append(attrs_dict["src"])


class SiteCrawler:
    def __init__(self, start_url: str, max_pages: int, delay: float, include_subdomains: bool = False,
                 include_redirects: bool = False):
        self.start_url = prepare_start_url(start_url)
        self.max_pages = max(1, max_pages)
        self.delay = max(1.0, delay)
        self.include_subdomains = include_subdomains
        self.include_redirects = include_redirects
        start_host = host_of(self.start_url)
        aliases = {start_host}
        if start_host.startswith("www."):
            aliases.add(start_host[4:])
        elif len(start_host.split(".")) == 2:
            aliases.add("www." + start_host)
        self.allowed_hosts = aliases
        self.allowed_suffix = None
        if self.include_subdomains:
            self.allowed_suffix = start_host[4:] if start_host.startswith("www.") else start_host
        self.urls: set[str] = {self.start_url}
        self.visited: set[str] = set()
        self.robot_parsers: dict[str, urllib.robotparser.RobotFileParser] = {}
        self.errors: list[str] = []
        self.failed_urls: set[str] = set()
        self.redirects: dict[str, dict[str, str]] = {}
        self.pages_read = 0
        self.documents = 0

    def _in_scope(self, url: str) -> bool:
        host = host_of(url)
        if host in self.allowed_hosts:
            return True
        return bool(self.allowed_suffix and (host == self.allowed_suffix or host.endswith("." + self.allowed_suffix)))

    def _normalize(self, url: str, base_url: str) -> Optional[str]:
        return normalize_url(url, base_url, self.allowed_hosts, self.allowed_suffix)

    def _robots_url(self, host: str) -> str:
        scheme = urllib.parse.urlsplit(self.start_url).scheme or "https"
        return f"{scheme}://{host}/robots.txt"

    def _robots(self, host: str) -> urllib.robotparser.RobotFileParser:
        if host in self.robot_parsers:
            return self.robot_parsers[host]
        parser = urllib.robotparser.RobotFileParser()
        robots_url = self._robots_url(host)
        parser.set_url(robots_url)
        status, headers, body, _ = request_bytes(robots_url, timeout=12)
        if status == 200:
            parser.parse(decode_body(body, headers).splitlines())
            print(f"  robots.txt gelesen: {host}")
        else:
            parser.parse([])
            if status not in (404, 410):
                print(f"  Hinweis: robots.txt nicht abrufbar (HTTP {status or 'Verbindungsfehler'}): {host}")
        self.robot_parsers[host] = parser
        return parser

    def _allowed_by_robots(self, url: str) -> bool:
        try:
            return self._robots(host_of(url)).can_fetch(USER_AGENT, url)
        except Exception:
            return True

    def _discover_sitemaps(self, host: str) -> set[str]:
        found: set[str] = set()
        robots_url = self._robots_url(host)
        status, headers, body, _ = request_bytes(robots_url, timeout=12)
        if status == 200:
            for line in decode_body(body, headers).splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap = self._normalize(line.split(":", 1)[1].strip(), robots_url)
                    if sitemap:
                        found.add(sitemap)
        for path in ("/sitemap.xml", "/sitemap_index.xml"):
            sitemap = self._normalize(path, robots_url)
            if sitemap:
                found.add(sitemap)
        return found

    def _parse_sitemap(self, url: str, visited_maps: set[str], depth: int = 0) -> set[str]:
        results: set[str] = set()
        if url in visited_maps or depth > 3 or not self._in_scope(url):
            return results
        visited_maps.add(url)
        status, headers, body, _ = request_bytes(url, timeout=18)
        if status != 200:
            return results
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            return results
        for parent in root.iter():
            parent_tag = parent.tag.split("}")[-1].lower()
            for node in list(parent):
                if node.tag.split("}")[-1].lower() != "loc" or not node.text:
                    continue
                loc = self._normalize(node.text.strip(), url)
                if not loc:
                    continue
                if parent_tag == "sitemap":
                    results.update(self._parse_sitemap(loc, visited_maps, depth + 1))
                else:
                    results.add(loc)
        return results

    def _process_url(self, url: str, queue: deque[str]) -> None:
        if looks_like_asset(url):
            return
        if looks_like_document(url):
            self.urls.add(url)
            self.documents += 1
            return
        if not looks_like_html_url(url):
            return
        if not self._allowed_by_robots(url):
            self.urls.discard(url)
            self.errors.append(f"ROBOTS disallow: {url}")
            print(f"  [durch robots.txt ausgeschlossen] {url}")
            return

        status, headers, body, final_url = request_bytes(url, follow_redirects=False)
        self.pages_read += 1
        if status in REDIRECT_CODES:
            target = full_redirect_target(url, headers)
            self.redirects[url] = {"target": target, "status": str(status), "source": "Website"}
            print(f"  [WEITERLEITUNG {status}] {url} -> {target or '(kein Ziel angegeben)'}")
            if not self.include_redirects:
                self.urls.discard(url)
            target_normalized = self._normalize(target, url) if target else None
            if target_normalized:
                self.urls.add(target_normalized)
                if looks_like_html_url(target_normalized) and target_normalized not in self.visited:
                    queue.append(target_normalized)
            elif not target:
                self.failed_urls.add(url)
                self.errors.append(f"Weiterleitung {status} ohne Location-Header: {url}")
            return

        print(f"  [{status or 'NETZWERKFEHLER'}] {url}")
        if status != 200:
            details = final_url if status == 0 else ""
            self.errors.append(f"HTTP/Netzwerk {status}: {url} {details}".strip())
            self.failed_urls.add(url)
            return

        ctype = header_value(headers, "Content-Type").lower()
        if "html" not in ctype and "xhtml" not in ctype:
            if looks_like_document(url):
                self.documents += 1
            return
        parser = LinkParser()
        try:
            parser.feed(decode_body(body, headers))
        except Exception as exc:
            self.errors.append(f"HTML-Parserfehler bei {url}: {exc}")
            self.failed_urls.add(url)
            return
        for raw in parser.links:
            candidate = self._normalize(raw, url)
            if not candidate or looks_like_asset(candidate):
                continue
            self.urls.add(candidate)
            if looks_like_document(candidate):
                self.documents += 1
            elif looks_like_html_url(candidate) and candidate not in self.visited:
                queue.append(candidate)

    def _drain_queue(self, queue: deque[str]) -> None:
        while queue and self.pages_read < self.max_pages:
            url = queue.popleft()
            if url in self.visited or not self._in_scope(url):
                continue
            self.visited.add(url)
            self._process_url(url, queue)
            time.sleep(self.delay)

    def _retry_failed_crawl_urls(self, queue: deque[str]) -> None:
        if not self.failed_urls:
            return
        failed = sorted(self.failed_urls)
        print(f"\n{len(failed)} URL(s) konnten bei der Suche nicht erfolgreich abgerufen werden.")
        print(f"Die Liste steht in {CRAWL_FAILED_FILE_DEFAULT}.")
        if not ask_yes_no("Möchtest du diese URLs jetzt einmal erneut prüfen?", default=False):
            return
        for url in failed:
            self.failed_urls.discard(url)
            self.visited.add(url)
            print(f"\n[ERNEUTER VERSUCH] {url}")
            self._process_url(url, queue)
            time.sleep(self.delay)
        self._drain_queue(queue)

    def _write_crawl_reports(self) -> None:
        failed_path = Path(CRAWL_FAILED_FILE_DEFAULT)
        if self.failed_urls:
            failed_path.write_text("# URLs, die beim Durchsuchen fehlgeschlagen sind; eine Zeile pro URL.\n" + "\n".join(sorted(self.failed_urls)) + "\n", encoding="utf-8")
        elif failed_path.exists():
            failed_path.unlink()

        error_path = Path(ERROR_FILE_DEFAULT)
        if self.errors:
            error_path.write_text("\n".join(self.errors) + "\n", encoding="utf-8")
        elif error_path.exists():
            error_path.unlink()

        write_redirect_csv(Path(CRAWL_REDIRECT_FILE_DEFAULT), [
            {"original_url": source, "target_url": info.get("target", ""), "status": info.get("status", ""), "source": info.get("source", "Website"),
             "message": "Weiterleitende Quelladresse wird standardmäßig nicht in die Archiv-URL-Liste aufgenommen." if not self.include_redirects else "Weiterleitung erkannt; Aufnahme der Quelladresse wurde aktiviert."}
            for source, info in sorted(self.redirects.items())
        ])
        if self.redirects:
            print(f"Weiterleitungen separat gespeichert: {Path(CRAWL_REDIRECT_FILE_DEFAULT).resolve()}")
        if self.failed_urls:
            print(f"Fehlgeschlagene Seiten separat gespeichert: {failed_path.resolve()}")
        if self.errors:
            print(f"Fehlerdetails: {error_path.resolve()}")

    def crawl(self) -> list[str]:
        print(f"\nStartadresse: {self.start_url}")
        print("Es werden nur öffentliche Seiten im gewählten Website-Bereich gesucht.")
        if self.include_subdomains:
            print("Unterdomains: eingeschlossen")
        else:
            print("Unterdomains: nicht eingeschlossen (www-Alias ausgenommen)")
        queue: deque[str] = deque([self.start_url])
        sitemap_seen: set[str] = set()
        sitemap_hosts = sorted(self.allowed_hosts)
        if self.allowed_suffix:
            sitemap_hosts = sorted(set(sitemap_hosts + [self.allowed_suffix]))
        for host in sitemap_hosts:
            for sitemap_url in self._discover_sitemaps(host):
                sitemap_urls = self._parse_sitemap(sitemap_url, sitemap_seen)
                if sitemap_urls:
                    print(f"  Sitemap: {len(sitemap_urls)} URL(s) gefunden")
                    for url in sitemap_urls:
                        self.urls.add(url)
                        if looks_like_html_url(url) and url not in self.visited:
                            queue.append(url)
        self._drain_queue(queue)
        if queue:
            print(f"\nSeitenlimit erreicht. {len(queue)} URL(s) wurden nicht mehr geprüft. Erhöhe bei Bedarf das Seitenlimit.")
        self._retry_failed_crawl_urls(queue)
        self._write_crawl_reports()
        results = sorted(self.urls)
        print(f"\nGefunden: {len(results)} URL(s), {self.pages_read} HTML-Aufruf(e), {self.documents} Dokument-Link(s).")
        return results


def write_redirect_csv(path: Path, rows: list[dict]) -> None:
    fields = ["original_url", "target_url", "status", "source", "message"]
    if not rows:
        if path.exists():
            path.unlink()
        return
    # Keine doppelten Zeilen in derselben Berichtsdatei.
    seen = set()
    unique_rows = []
    for row in rows:
        key = tuple(str(row.get(k, "")) for k in fields)
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unique_rows)


def read_url_file(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"URL-Datei nicht gefunden: {path}")
    urls = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url = normalize_url(line, line, allowed_hosts=None)
        if url:
            urls.append(url)
    return sorted(set(urls))


def write_url_file(path: Path, urls: list[str]) -> None:
    path.write_text(
        "# Gesammelte öffentliche URLs. Jede Zeile ist eine URL.\n" + "\n".join(urls) + ("\n" if urls else ""),
        encoding="utf-8"
    )


def prompt_credentials() -> tuple[str, str]:
    access = os.environ.get("IA_ACCESS_KEY", "").strip()
    secret = os.environ.get("IA_SECRET_KEY", "").strip()
    if access and secret:
        print("Internet-Archive-S3-Schlüssel aus Umgebungsvariablen geladen.")
        return access, secret
    print("\nFür die automatische Archivierung brauchst du Internet-Archive-S3-Schlüssel.")
    print("Schlüssel verwalten: https://archive.org/account/s3.php")
    print("Benötigt werden Access Key und Secret Key, nicht dein normales Passwort.")
    print("Die Eingaben werden nicht in einer Datei gespeichert; der Secret Key wird verdeckt eingegeben.")
    access = input("Access Key: ").strip()
    secret = getpass.getpass("Secret Key: ").strip() if access else ""
    return access, secret


def http_json(url: str, method: str = "GET", data: Optional[dict] = None,
              access: str = "", secret: str = "", timeout: int = 40):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if access and secret:
        headers["Authorization"] = f"LOW {access}:{secret}"
    body = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            text = response.read(1_000_000).decode("utf-8", errors="replace")
            try:
                return response.status, json.loads(text), text
            except json.JSONDecodeError:
                return response.status, None, text[:3000]
    except urllib.error.HTTPError as exc:
        raw = exc.read(1_000_000)
        text = raw.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        return exc.code, parsed, text[:3000]
    except Exception as exc:
        return 0, None, str(exc)


def submit_capture(url: str, access: str, secret: str, archive_delay: float) -> tuple[str, str, str, str]:
    # Eine Pause hält die automatische Verarbeitung bewusst zurück.
    time.sleep(max(10.0, archive_delay))
    status, payload, detail = http_json(
        WAYBACK_SAVE,
        method="POST",
        data={"url": url, "capture_all": "on", "if_not_archived_within": "86400"},
        access=access,
        secret=secret,
    )
    if status in (401, 403):
        return "AUTH_ERROR", "", "Zugriff abgelehnt. Prüfe die S3-Schlüssel. " + detail, ""
    if status == 429:
        return "RATE_LIMIT", "", "Die Wayback Machine meldet zu viele Anfragen (HTTP 429). Bitte später erneut versuchen. " + detail, ""
    if status < 200 or status >= 300 or not isinstance(payload, dict):
        return f"HTTP_{status}", "", detail, ""

    job_id = str(payload.get("job_id", "")).strip()
    snapshot = str(payload.get("url", "")).strip()
    if not job_id:
        actual = str(payload.get("original_url", "")).strip() or original_from_snapshot(snapshot)
        if actual and not same_page(url, actual):
            return "REDIRECTED", snapshot, f"Die API meldet als Ziel {actual}, nicht die angeforderte Unterseite. Nicht als Erfolg gewertet.", actual
        return "PENDING", snapshot, "Die API hat keinen Statusauftrag zurückgegeben; Ergebnis ist noch unbestätigt. " + json.dumps(payload, ensure_ascii=False), actual

    for _ in range(30):
        time.sleep(4)
        poll_status, poll_payload, poll_detail = http_json(
            f"https://web.archive.org/save/status/{urllib.parse.quote(job_id, safe='')}",
            access=access, secret=secret, timeout=30
        )
        if poll_status in (401, 403):
            return "AUTH_ERROR", snapshot, poll_detail, ""
        if poll_status == 429:
            time.sleep(20)
            continue
        if not isinstance(poll_payload, dict):
            continue
        state = str(poll_payload.get("status", "")).lower()
        snapshot = str(poll_payload.get("url", snapshot)).strip()
        if state == "success":
            timestamp = str(poll_payload.get("timestamp", "")).strip()
            actual = str(poll_payload.get("original_url", "")).strip() or original_from_snapshot(snapshot) or url
            if timestamp.isdigit():
                snapshot = f"https://web.archive.org/web/{timestamp}/{actual}"
            if not same_page(url, actual):
                return "REDIRECTED", snapshot, (
                    f"Die Wayback Machine meldet als archivierte Adresse {actual}, nicht die angeforderte URL. "
                    "Mögliche Weiterleitung oder kanonische URL; deshalb nicht als erfolgreicher Treffer gewertet."
                ), actual
            return "SUCCESS", snapshot, str(poll_payload.get("message", "Archivierung abgeschlossen")), actual
        if state == "error":
            message = str(poll_payload.get("message", poll_payload.get("status_ext", "Archivierung fehlgeschlagen")))
            actual = str(poll_payload.get("original_url", "")).strip() or original_from_snapshot(snapshot)
            if actual and not same_page(url, actual):
                return "REDIRECTED", snapshot, f"Die API meldet die andere Adresse {actual}: {message}", actual
            return "FAILED", snapshot, message, actual
    return "PENDING", snapshot, f"Job {job_id} ist noch nicht abgeschlossen. Später in der Wayback Machine prüfen.", original_from_snapshot(snapshot)


def detect_live_redirect(url: str) -> tuple[int, str]:
    """Prüft die Live-Adresse ohne den Redirect automatisch zu verfolgen."""
    status, headers, _, _ = request_bytes(url, timeout=15, follow_redirects=False, limit_bytes=0)
    if status in REDIRECT_CODES:
        return status, full_redirect_target(url, headers)
    return status, ""


def initialize_log(path: Path) -> None:
    fields = ["attempt", "original_url", "status", "snapshot_url", "captured_url", "message"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=fields, delimiter=";").writeheader()


def append_log(path: Path, row: dict) -> None:
    fields = ["attempt", "original_url", "status", "snapshot_url", "captured_url", "message"]
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=fields, delimiter=";", extrasaction="ignore").writerow(row)


def retryable_archive_status(status: str) -> bool:
    if status in {"FAILED", "PENDING"}:
        return True
    if status.startswith("HTTP_"):
        try:
            code = int(status.split("_", 1)[1])
        except ValueError:
            return True
        return code == 0 or code in {408, 425} or code >= 500
    return False


def run_archive_batch(urls: list[str], log_path: Path, access: str, secret: str,
                      archive_delay: float, attempt: int) -> tuple[list[dict], list[str], str]:
    rows: list[dict] = []
    remaining: list[str] = []
    abort_reason = ""
    for index, url in enumerate(urls, 1):
        print(f"\n[Versuch {attempt} | {index}/{len(urls)}] {url}")
        state, snapshot, message, captured = submit_capture(url, access, secret, archive_delay)
        row = {
            "attempt": attempt,
            "original_url": url,
            "status": state,
            "snapshot_url": snapshot,
            "captured_url": captured,
            "message": message,
        }
        rows.append(row)
        append_log(log_path, row)
        print(f"  Status: {state}")
        if snapshot:
            print(f"  Wayback: {snapshot}")
        if captured and not same_page(url, captured):
            print(f"  ACHTUNG: andere Zieladresse gemeldet: {captured}")
        if message:
            print(f"  Info: {message[:350]}")
        if state in {"AUTH_ERROR", "RATE_LIMIT"}:
            abort_reason = state
            remaining = urls[index:]
            break
    return rows, remaining, abort_reason


def write_text_url_list(path: Path, heading: str, urls: list[str]) -> None:
    if urls:
        path.write_text(heading + "\n" + "\n".join(sorted(set(urls))) + "\n", encoding="utf-8")
    elif path.exists():
        path.unlink()


def archive_urls(urls: list[str], log_path: Path, archive_delay: float) -> None:
    access, secret = prompt_credentials()
    if not access or not secret:
        print("\nABBRUCH: Ohne beide gültigen Schlüssel wurde nichts archiviert.")
        print("Schlüssel verwalten: https://archive.org/account/s3.php")
        return

    urls = sorted(set(urls))
    if not urls:
        print("Es wurden keine gültigen URLs übergeben.")
        return

    # Verhindert, dass Ausgabelisten aus einem älteren Durchlauf fälschlich weiterbestehen.
    for stale in (Path(ARCHIVE_FAILED_FILE_DEFAULT), Path(PENDING_FILE_DEFAULT)):
        if stale.exists():
            stale.unlink()

    precheck = ask_yes_no(
        "Vor dem Speichern prüfen, ob die Live-Adresse weiterleitet? Umgeleitete URLs werden übersprungen und separat gelistet",
        default=True,
    )
    initialize_log(log_path)
    redirect_rows: list[dict] = []
    latest: dict[str, dict] = {}
    capture_queue: list[str] = []

    if precheck:
        print("\nPrüfe Live-Weiterleitungen, bevor Seiten an die Wayback Machine gesendet werden ...")
        checked: set[str] = set()
        queue = deque(urls)
        while queue:
            url = queue.popleft()
            if url in checked:
                continue
            checked.add(url)
            status, target = detect_live_redirect(url)
            if status in REDIRECT_CODES and target:
                print(f"  [ÜBERSPRUNGEN: WEITERLEITUNG {status}] {url} -> {target}")
                message = "Nicht an Wayback gesendet, damit eine Weiterleitung nicht fälschlich als die gewünschte Unterseite gilt."
                row = {"attempt": 0, "original_url": url, "status": "REDIRECTED_SKIPPED", "snapshot_url": "", "captured_url": target, "message": message}
                append_log(log_path, row)
                latest[url] = row
                redirect_rows.append({"original_url": url, "target_url": target, "status": str(status), "source": "Live-Prüfung", "message": message})
                # Ziel nur automatisch ergänzen, wenn es dieselbe Website bzw. ihr www-Alias ist.
                if same_site_alias(url, target) and target not in checked:
                    queue.append(target)
            else:
                capture_queue.append(url)
            time.sleep(1.0)
    else:
        capture_queue = list(urls)

    all_attempt_rows: list[dict] = []
    abort = ""
    unattempted: list[str] = []
    if capture_queue:
        print(f"\nEs werden {len(capture_queue)} URL(s) an die Wayback Machine übergeben.")
        print("Zwischen Archivierungsaufträgen liegt eine Pause von mindestens 10 Sekunden.")
        rows_first, unattempted, abort = run_archive_batch(capture_queue, log_path, access, secret, archive_delay, 1)
        all_attempt_rows.extend(rows_first)
        for row in rows_first:
            latest[row["original_url"]] = row
            if row["status"] == "REDIRECTED":
                redirect_rows.append({
                    "original_url": row["original_url"], "target_url": row.get("captured_url", ""),
                    "status": "Wayback", "source": "Wayback-Antwort", "message": row.get("message", "")
                })

        retry_urls = sorted(url for url, row in latest.items() if retryable_archive_status(row["status"]))
        if abort:
            if unattempted:
                write_text_url_list(Path(PENDING_FILE_DEFAULT), "# Noch nicht gesendete URLs. Ursache: Authentifizierung oder Rate-Limit.", unattempted)
            if abort == "AUTH_ERROR":
                print("\nAbbruch: Die Authentifizierung ist fehlgeschlagen. Prüfe die Schlüssel, bevor du erneut startest.")
            elif abort == "RATE_LIMIT":
                print("\nAbbruch: Die Wayback Machine begrenzt gerade Anfragen. Bitte später weitermachen.")
            # Keine automatische Wiederholung, solange Anmeldedaten/Rate-Limit das Problem sind.
            retry_urls = []
        if retry_urls:
            write_text_url_list(Path(ARCHIVE_FAILED_FILE_DEFAULT), "# Fehlgeschlagene Archivierungsversuche; eine URL pro Zeile.", retry_urls)
            print(f"\n{len(retry_urls)} URL(s) konnten nicht bestätigt archiviert werden.")
            print(f"Fehlerliste: {Path(ARCHIVE_FAILED_FILE_DEFAULT).resolve()}")
            if ask_yes_no("Möchtest du die fehlgeschlagenen Archivierungen jetzt einmal erneut versuchen?", default=False):
                rows_retry, still_unattempted, retry_abort = run_archive_batch(retry_urls, log_path, access, secret, archive_delay, 2)
                all_attempt_rows.extend(rows_retry)
                for row in rows_retry:
                    latest[row["original_url"]] = row
                    if row["status"] == "REDIRECTED":
                        redirect_rows.append({
                            "original_url": row["original_url"], "target_url": row.get("captured_url", ""),
                            "status": "Wayback", "source": "Wiederholungsversuch", "message": row.get("message", "")
                        })
                if still_unattempted:
                    write_text_url_list(Path(PENDING_FILE_DEFAULT), "# Noch nicht gesendete URLs. Ursache: Authentifizierung oder Rate-Limit.", still_unattempted)
                elif Path(PENDING_FILE_DEFAULT).exists():
                    Path(PENDING_FILE_DEFAULT).unlink()
                if retry_abort == "AUTH_ERROR":
                    print("\nWiederholung abgebrochen: Authentifizierung prüfen.")
                elif retry_abort == "RATE_LIMIT":
                    print("\nWiederholung abgebrochen: Bitte später erneut versuchen.")
            else:
                print("Die Fehlerliste bleibt gespeichert. Du kannst sie später über das Menü erneut verwenden.")
    else:
        print("\nKeine URLs zur Archivierung übrig; alle geprüften Quelladressen haben weitergeleitet.")

    # Die Fehlerliste zeigt immer den letzten bekannten Status pro URL. Erfolgreiche
    # URLs und erkannte Weiterleitungen gehören nicht in diese Liste.
    unresolved = sorted(
        url for url, row in latest.items()
        if row.get("status") not in {"SUCCESS", "REDIRECTED", "REDIRECTED_SKIPPED"}
    )
    write_text_url_list(
        Path(ARCHIVE_FAILED_FILE_DEFAULT),
        "# Noch nicht erfolgreich abgeschlossene Archivierungsversuche; eine URL pro Zeile.",
        unresolved,
    )
    if unresolved:
        print(f"\nNoch ungeklärt/fehlgeschlagen: {len(unresolved)} URL(s) in {Path(ARCHIVE_FAILED_FILE_DEFAULT).resolve()}")
    elif Path(ARCHIVE_FAILED_FILE_DEFAULT).exists():
        Path(ARCHIVE_FAILED_FILE_DEFAULT).unlink()

    write_redirect_csv(Path(ARCHIVE_REDIRECT_FILE_DEFAULT), redirect_rows)
    if redirect_rows:
        print(f"Weiterleitungen/abweichende Archivziele: {Path(ARCHIVE_REDIRECT_FILE_DEFAULT).resolve()}")
    if Path(PENDING_FILE_DEFAULT).exists():
        print(f"Noch nicht gesendete URLs: {Path(PENDING_FILE_DEFAULT).resolve()}")
    print(f"\nErgebnisprotokoll: {log_path.resolve()}")


def main() -> int:
    # Bei einer gebündelten Windows-EXE standardmäßig neben der EXE arbeiten,
    # damit URL-Listen und Protokolle leicht wiedergefunden werden.
    if getattr(sys, "frozen", False):
        try:
            os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
        except OSError:
            pass

    parser = argparse.ArgumentParser(description="Öffentliche Website durchsuchen und Seiten für die Wayback Machine vorbereiten")
    parser.add_argument("--start-url", default=None, help="Startadresse der Website, z. B. https://example.com/")
    parser.add_argument("--max-pages", type=int, default=500, help="Maximale Anzahl geprüfter HTML-Seiten (Standard: 500)")
    parser.add_argument("--delay", type=float, default=1.5, help="Pause zwischen Website-Aufrufen in Sekunden (mind. 1)")
    parser.add_argument("--archive-delay", type=float, default=12.0, help="Pause zwischen Wayback-Aufträgen in Sekunden (mind. 10)")
    parser.add_argument("--include-subdomains", action="store_true", help="Auch passende Unterdomains durchsuchen")
    parser.add_argument("--include-redirects", action="store_true", help="Weiterleitende Quell-URLs in der Sammelliste behalten")
    parser.add_argument("--crawl-only", action="store_true", help="Nur suchen und URL-Liste erstellen")
    parser.add_argument("--archive-only", action="store_true", help="Eine bestehende URL-Liste archivieren")
    parser.add_argument("--url-file", default=URL_FILE_DEFAULT, help=f"Datei mit URL-Liste (Standard: {URL_FILE_DEFAULT})")
    parser.add_argument("--log-file", default=LOG_FILE_DEFAULT, help=f"Protokolldatei (Standard: {LOG_FILE_DEFAULT})")
    args = parser.parse_args()
    url_path = Path(args.url_file)

    if args.archive_only:
        try:
            urls = read_url_file(url_path)
        except (OSError, ValueError) as exc:
            print(f"Fehler: {exc}")
            return 2
        if not urls:
            print("Die URL-Liste enthält keine gültigen öffentlichen HTTP(S)-Adressen.")
            return 2
        print(f"{len(urls)} URL(s) aus {url_path} geladen.")
        archive_urls(urls, Path(args.log_file), args.archive_delay)
        return 0

    raw_start = args.start_url
    if raw_start is None:
        raw_start = input("\nWebsite-Adresse eingeben (z. B. https://example.com): ").strip()
    try:
        start_url = prepare_start_url(raw_start)
    except ValueError as exc:
        print(f"Fehler: {exc}")
        return 2

    crawler = SiteCrawler(start_url, args.max_pages, args.delay, args.include_subdomains, args.include_redirects)
    urls = crawler.crawl()
    write_url_file(url_path, urls)
    print(f"URL-Liste gespeichert: {url_path.resolve()}")
    if args.crawl_only:
        print("Nur-Suchmodus aktiv; es wurden keine Archivierungsaufträge gesendet.")
        return 0
    if not urls:
        print("Es wurden keine URLs für die Archivierung gefunden.")
        return 0
    if not ask_yes_no("Möchtest du diese URLs jetzt an die Wayback Machine senden?", default=False):
        print("Abgebrochen. Du kannst später Option 3 im Startmenü verwenden.")
        return 0
    archive_urls(urls, Path(args.log_file), args.archive_delay)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer. Bereits geschriebene Dateien bleiben erhalten.")
        raise SystemExit(130)
