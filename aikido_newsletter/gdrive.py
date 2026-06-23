"""Optional Google Drive upload of the newsletter PDF.

Auth uses a Google Cloud **service account** with the Drive API enabled — the
right model for unattended CI. Provide the JSON key one of two ways:

  * AIKIDO/GDRIVE_SERVICE_ACCOUNT_JSON  — the key's JSON, inline (good for a
    GitHub Actions secret), or
  * GDRIVE_SERVICE_ACCOUNT_FILE         — a path to the key file.

Then set GDRIVE_FOLDER_ID to the destination folder. Share that folder with the
service account's `client_email` (Editor), or point at a Shared Drive folder and
set shared_drive=True. Scope: drive.file (only files this app creates).

Libraries: google-api-python-client, google-auth.
"""
from __future__ import annotations

import json
import os

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GDriveUploader:
    def __init__(self, *, service_account_json: str | None = None,
                 service_account_file: str | None = None):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "Google Drive upload needs google-api-python-client and google-auth "
                "(pip install google-api-python-client google-auth)."
            ) from e

        if service_account_json:
            creds = service_account.Credentials.from_service_account_info(
                json.loads(service_account_json), scopes=SCOPES)
        elif service_account_file:
            creds = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES)
        else:
            raise RuntimeError("No Google service-account credentials provided.")
        self._svc = build("drive", "v3", credentials=creds, cache_discovery=False)

    def upload(self, path: str, *, folder_id: str | None = None,
               name: str | None = None, mime: str = "application/pdf",
               shared_drive: bool = False) -> dict:
        from googleapiclient.http import MediaFileUpload
        meta: dict = {"name": name or os.path.basename(path)}
        if folder_id:
            meta["parents"] = [folder_id]
        media = MediaFileUpload(path, mimetype=mime, resumable=False)
        params: dict = dict(body=meta, media_body=media, fields="id,webViewLink,name")
        if shared_drive:
            params["supportsAllDrives"] = True
        f = self._svc.files().create(**params).execute()
        return {"id": f.get("id"), "link": f.get("webViewLink"), "name": f.get("name")}


def from_env():
    """Build an uploader from env vars, or return None if not configured."""
    js = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
    fp = os.environ.get("GDRIVE_SERVICE_ACCOUNT_FILE")
    if not (js or fp):
        return None
    return GDriveUploader(service_account_json=js, service_account_file=fp)
