"""
Download sample medicine PDFs into data/pdfs, then build the search index.

Run from the project root:

    python -m backend.fetch_sample_pdfs

The file names are chosen so their drug id matches the frontend
(rinvoq_pi.pdf -> "rinvoq", etc.), allowing the medicine dropdown
to line up with the indexed documents.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config
from .search.index import build_index


# Public prescribing-information PDFs
SAMPLES = {
    "rinvoq_pi.pdf": "https://www.rxabbvie.com/pdf/rinvoq_pi.pdf",
    "humira_pi.pdf": "https://www.rxabbvie.com/pdf/humira_pi.pdf",
    # Add more public medicine PDFs here as needed.
}


MIN_PDF_SIZE = 10_000
DOWNLOAD_TIMEOUT = 60
MAX_RETRIES = 3


def create_session() -> requests.Session:
    """Create a requests session with automatic retry support."""

    session = requests.Session()

    retry_strategy = Retry(
        total=MAX_RETRIES,
        connect=MAX_RETRIES,
        read=MAX_RETRIES,
        status=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (MedCite sample fetcher)",
            "Accept": "application/pdf",
        }
    )

    return session


def is_valid_pdf(path: Path) -> bool:
    """Check whether a file looks like a valid PDF."""

    if not path.exists():
        return False

    if path.stat().st_size < MIN_PDF_SIZE:
        return False

    try:
        with path.open("rb") as file:
            header = file.read(5)

        return header == b"%PDF-"

    except OSError:
        return False


def download_pdf(
    session: requests.Session,
    name: str,
    url: str,
    destination: Path,
) -> bool:
    """Download one PDF safely using a temporary file."""

    temporary_file = destination.with_suffix(destination.suffix + ".part")

    try:
        print(f"  Downloading {name} ...")

        response = session.get(
            url,
            timeout=DOWNLOAD_TIMEOUT,
            stream=True,
        )

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()

        # Some servers do not correctly return application/pdf,
        # so only reject an explicit non-PDF content type.
        if content_type and "pdf" not in content_type:
            print(
                f"    Warning: server returned Content-Type: {content_type}"
            )

        total_bytes = 0

        with temporary_file.open("wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    total_bytes += len(chunk)

        # Validate before replacing the real file.
        if not is_valid_pdf(temporary_file):
            print("    Failed: downloaded file is not a valid PDF.")
            temporary_file.unlink(missing_ok=True)
            return False

        # Replace the destination only after successful validation.
        temporary_file.replace(destination)

        print(f"    Success: {total_bytes // 1024} KB")
        return True

    except requests.RequestException as error:
        print(f"    Download failed: {error}")

    except OSError as error:
        print(f"    File error: {error}")

    finally:
        temporary_file.unlink(missing_ok=True)

    return False


def main() -> None:
    """Download missing PDFs and rebuild the search index."""

    config.PDF_DIR.mkdir(parents=True, exist_ok=True)

    session = create_session()

    downloaded = []
    already_available = []
    failed = []

    print("\nChecking sample medicine PDFs...\n")

    for name, url in SAMPLES.items():
        destination = config.PDF_DIR / name

        # Reuse an existing valid PDF.
        if is_valid_pdf(destination):
            print(f"  Already available: {name}")
            already_available.append(name)
            continue

        # Remove invalid existing files before downloading.
        if destination.exists():
            print(f"  Existing file is invalid: {name}")
            destination.unlink(missing_ok=True)

        if download_pdf(session, name, url, destination):
            downloaded.append(name)
        else:
            failed.append(name)

        # Small delay between downloads to avoid hitting the server too quickly.
        time.sleep(0.5)

    session.close()

    print("\n----------------------------------------")
    print("Download Summary")
    print("----------------------------------------")
    print(f"Already available : {len(already_available)}")
    print(f"Downloaded        : {len(downloaded)}")
    print(f"Failed            : {len(failed)}")

    if failed:
        print("\nFailed files:")
        for name in failed:
            print(f"  - {name}")

    # Build the index if at least one valid PDF is available.
    valid_pdfs = [
        path
        for path in config.PDF_DIR.glob("*.pdf")
        if is_valid_pdf(path)
    ]

    if not valid_pdfs:
        print("\nNo valid PDFs available.")
        print("Check your network connection or add PDFs manually.")
        sys.exit(1)

    print("\nBuilding search index...")

    try:
        build_index()
    except Exception as error:
        print(f"Failed to build index: {error}")
        sys.exit(1)

    print("\nDone!")
    print(
        "Start the API with: "
        "uvicorn backend.api.main:app --port 8000"
    )


if __name__ == "__main__":
    main()