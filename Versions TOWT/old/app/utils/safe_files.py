"""Safe file serving helper.

Ensures FileResponse() only serves files located inside the configured
upload roots. Protects against DB-injected/path-traversal file_path
values that could otherwise expose /etc/passwd or SSH keys.
"""
import os
from fastapi import HTTPException
from fastapi.responses import FileResponse


# Roots under which served files must live. Add more as new modules
# start persisting uploads.
ALLOWED_UPLOAD_ROOTS = (
    "/app/uploads",
    "/app/data",
    "/app/app/static/uploads",
    "app/static/uploads",
    "/tmp",  # transient generated PDFs (crossing books, closure docs)
)


def _is_within(path: str, root: str) -> bool:
    abs_path = os.path.abspath(path)
    abs_root = os.path.abspath(root)
    try:
        return os.path.commonpath([abs_path, abs_root]) == abs_root
    except ValueError:
        # Different drives / unrelated paths
        return False


def safe_file_response(path: str, filename: str | None = None, **kwargs) -> FileResponse:
    """Return FileResponse(path) only if path is inside an allowed root.

    Raises HTTPException(404) for missing files or attempts to escape
    the allowed roots. 404 (not 403) to avoid leaking whether the file
    exists outside the allowed root.
    """
    if not path or not isinstance(path, str):
        raise HTTPException(404, "File not found")
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    if not any(_is_within(path, root) for root in ALLOWED_UPLOAD_ROOTS):
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=filename, **kwargs)
