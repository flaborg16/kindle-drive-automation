from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Iterable

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveClient:
    def __init__(self, service_account_json: str | None = None, service_account_file: str | None = None):
        creds_info = None
        if service_account_json:
            raw = service_account_json.strip()
            try:
                if raw.startswith("{"):
                    creds_info = json.loads(raw)
                else:
                    creds_info = json.loads(base64.b64decode(raw).decode("utf-8"))
            except Exception as exc:
                raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON must be raw JSON or base64 encoded JSON") from exc
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        elif service_account_file and Path(service_account_file).exists():
            creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
        else:
            raise RuntimeError("Provide GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE")
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)

    @staticmethod
    def _escape_query(value: str) -> str:
        return value.replace("'", "\\'")

    def find_folder(self, name: str, parent_id: str | None = None) -> str | None:
        q = [
            "mimeType='application/vnd.google-apps.folder'",
            "trashed=false",
            f"name='{self._escape_query(name)}'",
        ]
        if parent_id:
            q.append(f"'{parent_id}' in parents")
        resp = self.service.files().list(
            q=" and ".join(q),
            spaces="drive",
            fields="files(id,name)",
            pageSize=10,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = resp.get("files", [])
        return files[0]["id"] if files else None

    def ensure_folder(self, name: str, parent_id: str | None = None) -> str:
        existing = self.find_folder(name, parent_id)
        if existing:
            return existing
        metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            metadata["parents"] = [parent_id]
        created = self.service.files().create(
            body=metadata,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        return created["id"]

    def list_files(self, folder_id: str) -> list[dict]:
        results = []
        token = None
        while True:
            resp = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces="drive",
                fields="nextPageToken,files(id,name,mimeType,size,modifiedTime)",
                pageSize=100,
                pageToken=token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            results.extend(resp.get("files", []))
            token = resp.get("nextPageToken")
            if not token:
                return results

    def download_file(self, file_id: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        with out_path.open("wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return out_path

    def upload_file(self, local_path: Path, parent_id: str, name: str | None = None, mime_type: str | None = None) -> str:
        metadata = {"name": name or local_path.name, "parents": [parent_id]}
        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
        created = self.service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        return created["id"]

    def move_file(self, file_id: str, new_parent_id: str) -> None:
        current = self.service.files().get(
            fileId=file_id,
            fields="parents",
            supportsAllDrives=True,
        ).execute()
        previous_parents = ",".join(current.get("parents", []))
        self.service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=previous_parents,
            fields="id,parents",
            supportsAllDrives=True,
        ).execute()

    def update_description(self, file_id: str, description: str) -> None:
        self.service.files().update(
            fileId=file_id,
            body={"description": description[:12000]},
            fields="id",
            supportsAllDrives=True,
        ).execute()
