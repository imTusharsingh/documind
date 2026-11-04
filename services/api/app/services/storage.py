"""Durable storage for uploaded PDFs.

Files are written to a temporary name and moved into place only after the
size limit has been satisfied. A failed or oversized upload never leaves a
partial file that looks like a valid document.
"""

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

_PDF_MAGIC = b"%PDF-"
_CHUNK_SIZE = 1024 * 1024
_HEADER_BYTES = 1024


class InvalidUploadError(Exception):
    """Raised when an upload is not an acceptable PDF."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UploadTooLargeError(Exception):
    """Raised when an upload exceeds the configured size limit."""

    def __init__(self, max_mb: int) -> None:
        self.max_mb = max_mb
        super().__init__(f"The file exceeds the {max_mb} MB upload limit.")


@dataclass(frozen=True)
class SavedUpload:
    path: Path
    size_bytes: int


def safe_filename(raw_name: str | None) -> str:
    """Reduce a client filename to a bare, length-limited name."""
    if not raw_name:
        raise InvalidUploadError("A file name is required.")

    name = Path(raw_name.replace("\\", "/")).name.strip()
    if not name:
        raise InvalidUploadError("A file name is required.")
    if not name.lower().endswith(".pdf"):
        raise InvalidUploadError("Only PDF files are supported.")

    if len(name) > 255:
        name = f"{name[:-4][:251]}.pdf"

    return name


def storage_path_for(upload_dir: str, document_id: uuid.UUID) -> Path:
    """Return the destination path for a document's PDF.

    The database id, not the client filename, determines the path. That
    prevents path traversal and collisions between same-named uploads.
    """
    return Path(upload_dir) / f"{document_id}.pdf"


async def save_upload(
    upload: UploadFile,
    destination: Path,
    max_bytes: int,
    max_mb: int,
) -> SavedUpload:
    """Stream an upload to disk, validating signature and size.

    Reading in chunks means a large upload is rejected while it is being
    written, without buffering the whole file in memory and without
    trusting the client's Content-Length header.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".part")
    total = 0

    try:
        with temporary.open("wb") as target:
            header = await upload.read(_HEADER_BYTES)
            if _PDF_MAGIC not in header:
                raise InvalidUploadError("The uploaded file is not a valid PDF.")

            target.write(header)
            total = len(header)

            while chunk := await upload.read(_CHUNK_SIZE):
                total += len(chunk)
                if total > max_bytes:
                    raise UploadTooLargeError(max_mb)
                target.write(chunk)

        if total == 0:
            raise InvalidUploadError("The uploaded file is empty.")

        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    return SavedUpload(path=destination, size_bytes=total)


def remove_file(path: Path) -> None:
    """Delete a stored file, tolerating an already-missing file."""
    path.unlink(missing_ok=True)
