"""
Build the search index from every PDF in data/pdfs.

Run from the project root:
    python -m backend.build_index

This command:
    1. Checks that the PDF directory exists.
    2. Finds all PDF files.
    3. Validates that PDFs are not empty/corrupted.
    4. Builds the search index.
    5. Prints a summary of indexed documents and chunks.
"""

from __future__ import annotations

from pathlib import Path

from . import config
from .search.index import build_index


MIN_PDF_SIZE = 10_000


def is_valid_pdf(path: Path) -> bool:
    """Return True if the file exists and has a valid PDF header."""

    if not path.is_file():
        return False

    if path.stat().st_size < MIN_PDF_SIZE:
        return False

    try:
        with path.open("rb") as file:
            return file.read(5) == b"%PDF-"
    except OSError:
        return False


def find_pdf_files() -> tuple[list[Path], list[Path]]:
    """
    Find valid and invalid PDF files in the configured PDF directory.

    Returns:
        A tuple containing:
            - valid PDF files
            - invalid PDF files
    """

    if not config.PDF_DIR.exists():
        return [], []

    valid_files = []
    invalid_files = []

    for path in sorted(config.PDF_DIR.glob("*.pdf")):
        if is_valid_pdf(path):
            valid_files.append(path)
        else:
            invalid_files.append(path)

    return valid_files, invalid_files


def print_document_summary(documents: dict) -> None:
    """Print information about indexed documents."""

    if not documents:
        return

    print("\nIndexed documents:")
    print("-" * 72)

    for document in documents.values():
        drug_id = document.get("drug_id", "unknown")
        pages = document.get("pages", 0)
        chunks = document.get("num_chunks", 0)
        filename = document.get("filename", "unknown")

        print(
            f"  {drug_id:12} "
            f"{pages:>4} pages  "
            f"{chunks:>4} chunks  "
            f"({filename})"
        )

    print("-" * 72)


def main() -> None:
    """Build the search index and display the indexing results."""

    print("\n" + "=" * 72)
    print("Medicine Search Index Builder")
    print("=" * 72)

    print(f"\nPDF directory: {config.PDF_DIR}")
    print(f"Index file:    {config.INDEX_FILE}")

    # Check whether the PDF directory exists.
    if not config.PDF_DIR.exists():
        print("\nNo PDF directory found.")
        print(f"Create it at: {config.PDF_DIR}")
        print("\nYou can download the sample PDFs using:")
        print("  python -m backend.fetch_sample_pdfs")
        return

    # Find PDF files before building the index.
    valid_pdfs, invalid_pdfs = find_pdf_files()

    print(f"\nFound {len(valid_pdfs)} valid PDF(s).")

    # Report invalid PDFs but don't stop the entire process.
    if invalid_pdfs:
        print(f"Found {len(invalid_pdfs)} invalid PDF(s):")

        for pdf in invalid_pdfs:
            print(f"  - {pdf.name}")

        print("\nInvalid files will not be considered valid input.")

    if not valid_pdfs:
        print("\nNo valid PDFs found.")
        print("Put medicine PDFs in data/pdfs and run this command again.")
        print("\nTip:")
        print("  python -m backend.fetch_sample_pdfs")
        return

    # Build the search index.
    print("\nBuilding search index...")

    try:
        index = build_index()
    except Exception as error:
        print("\nIndex building failed.")
        print(f"Error: {error}")
        return

    # Read indexed data safely.
    documents = index.get("documents", {})
    chunks = index.get("chunks", [])

    if not documents:
        print("\nNo documents were indexed.")
        print("Check the PDF files and try again.")
        return

    print("\nIndex built successfully!")
    print(f"Documents indexed : {len(documents)}")
    print(f"Total chunks      : {len(chunks)}")

    print_document_summary(documents)

    print(f"\nIndex written to:")
    print(f"  {config.INDEX_FILE}")

    print("\nYou can now start the API with:")
    print("  uvicorn backend.api.main:app --port 8000")

    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()