"""File upload validation utilities.

Uses magic bytes (file signatures) to validate file types,
without requiring the python-magic library.
"""

# Map of magic byte signatures to MIME types
MAGIC_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'%PDF': 'application/pdf',
    b'PK\x03\x04': 'application/zip',  # docx, xlsx are ZIP-based
    b'RIFF': 'image/webp',  # RIFF....WEBP
    b'\xd0\xcf\x11\xe0': 'application/msword',  # .doc/.xls (OLE2)
    b'\x00\x00\x00': 'image/heic',  # HEIC/HEIF (simplified check)
}

# Extension to expected MIME type families
EXT_TO_MIME_FAMILY = {
    '.pdf': {'application/pdf'},
    '.jpg': {'image/jpeg'},
    '.jpeg': {'image/jpeg'},
    '.png': {'image/png'},
    '.gif': {'image/gif'},
    '.webp': {'image/webp'},
    '.heic': {'image/heic', 'image/heif'},
    '.doc': {'application/msword', 'application/zip'},
    '.docx': {'application/zip'},  # OOXML is ZIP
    '.xls': {'application/msword', 'application/zip'},  # OLE2 or ZIP
    '.xlsx': {'application/zip'},
    '.csv': {'text/plain', 'text/csv'},
    '.txt': {'text/plain', 'text/csv'},
}


def detect_mime_from_bytes(content: bytes) -> str | None:
    """Detect MIME type from file content using magic bytes."""
    if not content:
        return None

    header = content[:16]

    for sig, mime in MAGIC_SIGNATURES.items():
        if header.startswith(sig):
            # Special case: RIFF containers need WEBP check
            if sig == b'RIFF' and len(content) >= 12:
                if content[8:12] != b'WEBP':
                    return None
            return mime

    # Text-based files (CSV, TXT)
    try:
        content[:1024].decode('utf-8')
        return 'text/plain'
    except (UnicodeDecodeError, ValueError):
        pass

    return None


def validate_file_content(content: bytes, extension: str) -> bool:
    """Validate that file content matches its extension.

    Returns True if the content appears to match the expected type,
    or if we can't determine the type (fail-open for unknown types).
    """
    ext = extension.lower()
    if ext not in EXT_TO_MIME_FAMILY:
        return True  # Unknown extension, already validated by ALLOWED_EXTENSIONS

    detected = detect_mime_from_bytes(content)
    if detected is None:
        return False  # Can't detect type = suspicious

    expected_mimes = EXT_TO_MIME_FAMILY[ext]
    return detected in expected_mimes


# Global upload size limit (MB). Individual routers may reduce it further.
MAX_UPLOAD_SIZE_MB = 25

ALLOWED_EXTENSIONS = set(EXT_TO_MIME_FAMILY.keys())


def validate_upload(filename: str, content: bytes) -> tuple[bool, str | None]:
    """Full upload validation: extension allow-list + magic-bytes check.

    Returns (ok, error_message). error_message is None on success.
    """
    import os as _os
    if not filename:
        return False, "Nom de fichier vide"
    ext = _os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extension non autorisée ({ext or 'aucune'})"
    if not validate_file_content(content, ext):
        return False, "Contenu du fichier incohérent avec son extension"
    return True, None
