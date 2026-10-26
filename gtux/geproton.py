"""Установка GE-Proton: свежий релиз с GitHub -> папка compatibilitytools.d выбранного Steam.

Источник: https://github.com/GloriousEggroll/proton-ge-custom/releases (README проекта: распаковать
архив в ~/.steam/root/compatibilitytools.d и перезапустить Steam). У каждого релиза есть
GE-Proton<версия>.sha512sum — архив сверяется с ним до распаковки. Root не нужен.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from gtux import __version__

log = logging.getLogger("gtux.geproton")

LATEST = "https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest"
USER_AGENT = f"gtux/{__version__}"
NAME = re.compile(r"GE-Proton\d+-\d+")


class GEError(Exception):
    pass


def _get(url: str, timeout: int = 60):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=timeout)


def latest_release() -> dict:
    """{"tag": "GE-Proton11-11", "name": имя архива, "archive": url, "sha512": url}."""
    with _get(LATEST, timeout=30) as resp:
        data = json.load(resp)
    tag = data.get("tag_name", "")
    if not NAME.fullmatch(tag):
        raise GEError(f"unexpected release name: {tag!r}")
    assets = {a["name"]: a["browser_download_url"] for a in data.get("assets", [])}
    # с 2026 года рядом лежат сборки для aarch64; старые релизы — без суффикса архитектуры
    for archive, checksum in ((f"{tag}-x86_64.tar.gz", f"{tag}-x86_64.sha512sum"), (f"{tag}.tar.gz", f"{tag}.sha512sum")):
        if archive in assets and checksum in assets:
            return {"tag": tag, "archive": assets[archive], "sha512": assets[checksum], "name": archive}
    raise GEError(f"no x86_64 archive in {tag}")


def expected_sha512(text: str, name: str) -> str:
    """Строка формата sha512sum: «<хеш>  <имя файла>»."""
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == name and re.fullmatch(r"[0-9a-f]{128}", parts[0]):
            return parts[0]
    raise GEError(f"no checksum for {name}")


def _safe_extract(tar: tarfile.TarFile, dest: Path, top: str) -> None:
    """Только файлы внутри одной папки top: без абсолютных путей, «..» и устройств."""
    for m in tar.getmembers():
        parts = Path(m.name).parts
        if not parts or parts[0] != top or ".." in parts or Path(m.name).is_absolute():
            raise GEError(f"unexpected path in archive: {m.name}")
        if not (m.isfile() or m.isdir() or m.issym() or m.islnk()):
            raise GEError(f"unexpected file type in archive: {m.name}")
    if hasattr(tarfile, "data_filter"):
        tar.extractall(dest, filter="data")
    else:  # Python 3.11 без фильтров: пути уже проверены выше
        tar.extractall(dest)  # noqa: S202


def install(target: Path, progress=lambda done, total: None, release: dict | None = None) -> Path:
    """Ставит последний GE-Proton в target (compatibilitytools.d). Возвращает папку сборки."""
    release = release or latest_release()
    tag = release["tag"]
    # папка внутри архива называется как архив: GE-Proton11-11-x86_64 (проверено на релизе 11-11),
    # у старых релизов — просто GE-Proton9-27
    top = release["name"].removesuffix(".tar.gz")
    final = target / top
    for existing in (final, target / tag):
        if existing.exists():
            log.info("%s already installed in %s", tag, target)
            return existing
    target.mkdir(parents=True, exist_ok=True)
    remove_partial(target)
    with _get(release["sha512"], timeout=30) as resp:
        want = expected_sha512(resp.read().decode("utf-8", "replace"), release["name"])
    # временная папка на том же диске, что и target: переименование в конце атомарное
    with tempfile.TemporaryDirectory(dir=target, prefix=".gtux-") as tmp:
        archive = Path(tmp) / release["name"]
        digest = hashlib.sha512()
        with _get(release["archive"], timeout=60) as resp, open(archive, "wb") as out:
            total, done = int(resp.headers.get("Content-Length") or 0), 0
            while chunk := resp.read(1 << 20):
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                progress(done, total)
        if digest.hexdigest() != want:
            raise GEError("checksum mismatch: the download is damaged, nothing was installed")
        with tarfile.open(archive) as tar:
            _safe_extract(tar, Path(tmp), top)
        os.replace(Path(tmp) / top, final)
    log.info("installed %s to %s", tag, target)
    return final


def remove_partial(target: Path) -> None:
    """Остатки прерванной установки (папки .gtux-*), если процесс убили."""
    for p in target.glob(".gtux-*"):
        shutil.rmtree(p, ignore_errors=True)
