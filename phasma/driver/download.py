#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import platform
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

DRIVER_PATH = Path(__file__).parent

BASE_URL = "https://github.com/MohammadRaziei/phasma/releases/download/drivers"

DRIVER_VERSION = "2.1.1"

FILES = {
    ("windows", "64bit", "2.1.1"): (
        "phantomjs-2.1.1-windows.zip",
        "d9fb05623d6b26d3654d008eab3adafd1f6350433dfd16138c46161f42c7dcc8",
    ),
    ("darwin", "64bit", "2.1.1"): (
        "phantomjs-2.1.1-macosx.zip",
        "538cf488219ab27e309eafc629e2bcee9976990fe90b1ec334f541779150f8c1",
    ),
    ("linux", "64bit", "2.1.1"): (
        "phantomjs-2.1.1-linux-x86_64.tar.bz2",
        "86dd9a4bf4aee45f1a84c9f61cf1947c1d6dce9b9e8d2a907105da7852460d2f",
    ),
    ("linux", "32bit", "2.1.1"): (
        "phantomjs-2.1.1-linux-i686.tar.bz2",
        "80e03cfeb22cc4dfe4e73b68ab81c9fdd7c78968cfd5358e6af33960464f15e3",
    ),
}

ARCHIVE_SUFFIXES = (
    ".tar.bz2",
    ".zip",
)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_target(os_name: str, arch: str, version: str):
    key = (os_name, arch, version)
    if key not in FILES:
        raise RuntimeError(f"Unsupported platform/version: {key}")
    return FILES[key]


def download(url: str, dst: Path):
    urllib.request.urlretrieve(url, dst)


def extract(archive: Path, dst: Path):
    logger.info(f"Extracting: {archive.name}")
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(dst)
    elif archive.suffixes[-2:] == [".tar", ".bz2"]:
        with tarfile.open(archive) as t:
            t.extractall(dst)
    else:
        raise RuntimeError("Unknown archive format")


def find_binary(root: Path) -> Path:
    for p in root.rglob("phantomjs*"):
        if p.is_file() and os.access(p, os.X_OK):
            return p
    raise RuntimeError("phantomjs binary not found")


def download_and_extract(
    *,
    url: str,
    archive: Path,
    checksum: str,
    extract_dir: Path,
    force: bool,
):
    if force and archive.exists():
        archive.unlink()

    dest = extract_dir / "phantomjs"

    is_ok = (dest / "bin").exists()

    if is_ok:
        logger.info("Path exists: %s", dest)
        if force:
            shutil.rmtree(dest)
        else:
            return is_ok

    logger.info("Downloading %s to %s", url, archive)
    download(url, archive)

    logger.info("Verifying checksum")
    if sha256(archive) != checksum:
        raise RuntimeError("Checksum mismatch")


    if dest.exists():
        shutil.rmtree(dest)

    logger.info("Extracting")
    extract(archive, extract_dir)

    name = os.path.basename(archive)
    for suf in ARCHIVE_SUFFIXES:
        if name.endswith(suf):
            name = name[:-len(suf)]
    extract_path = extract_dir / name

    try:
        os.rename(extract_path, dest)
    except OSError as e:
        msg = f"{e!s}\nlist of files at {extract_dir}:\n{os.listdir(extract_dir)}"
        logger.error(msg)
        raise OSError(msg)

    os.remove(archive)

    return (dest / "bin").exists()


def download_driver(
    dest: Path | None = None,
    version: str = "2.1.1",
    os_name: str | None = None,
    arch: str | None = None,
    force: bool = False,
) -> bool:
    if dest is None:
        dest = DRIVER_PATH
    if os_name is None:
        os_name = platform.system().lower()
    if arch is None:
        arch = platform.architecture()[0]
        if arch not in ("32bit", "64bit"):
            machine = platform.machine().lower()
            arch = "64bit" if "64" in machine else "32bit"

    dest.mkdir(parents=True, exist_ok=True)

    filename, checksum = detect_target(os_name, arch, version)
    url = f"{BASE_URL}/{filename}"
    archive = dest / filename

    binary = download_and_extract(
        url=url,
        archive=archive,
        checksum=checksum,
        extract_dir=dest,
        force=force,
    )

    return binary


def setup_logging(quiet: bool = False):
    """
    Configure global logging settings.

    :param quiet: If True, only warnings and errors are shown.
    """
    level = logging.WARNING if quiet else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # overwrite any existing logging config
    )

def main():
    parser = argparse.ArgumentParser(description="Download PhantomJS driver")
    parser.add_argument("--dest", default=DRIVER_PATH.as_posix())
    parser.add_argument("--version", default=DRIVER_VERSION)
    parser.add_argument("--os", default=None, help="Operating system (e.g., Linux, Windows, Darwin)")
    parser.add_argument("--arch", default=None, help="Architecture (e.g., 32bit, 64bit)")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--quiet", action="store_true")

    args = parser.parse_args()

    setup_logging(quiet=args.quiet)


    # Detect OS and arch if not provided
    os_name = args.os or platform.system()
    arch = args.arch or platform.architecture()[0]

    # Normalize architecture string (some systems return '32bit' or '64bit' already)
    if arch not in ("32bit", "64bit"):
        # Fallback: try to guess from machine
        machine = platform.machine().lower()
        if "64" in machine:
            arch = "64bit"
        else:
            arch = "32bit"

    logger.info("Target: OS=%s, Arch=%s, Version=%s", os_name, arch, args.version)

    download_driver(
        dest=Path(args.dest),
        version=args.version,
        os_name=os_name,
        arch=arch,
        force=args.force,
    )


if __name__ == "__main__":
    main()
