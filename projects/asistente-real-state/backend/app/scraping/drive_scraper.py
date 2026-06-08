"""
drive_scraper.py — Google Drive / Sheets ingestion worker.

Flow per configured source:
  1. Authenticate with service account (credentials JSON stored in source.config)
  2. List files in the configured folder(s) — .xlsx, .xls, or Google Sheets
  3. Download / export each file as .xlsx bytes
  4. Parse with openpyxl → normalize rows with excel_parser
  5. Upsert properties/contacts to DB with same dedup logic as adinco_scraper

Circuit breaker: shared instance from adinco_scraper (threshold=3).
"""
import io
import structlog
from datetime import datetime, timezone
from typing import Any

import openpyxl
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.scraping.adinco_scraper import circuit_breaker, _upsert_properties, _upsert_contacts
from app.scraping.excel_parser import (
    normalize_headers,
    parse_excel_property_row,
    parse_excel_contact_row,
    _PROPERTY_COLUMN_MAP,
    _CONTACT_COLUMN_MAP,
)

log = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# MIME type Google uses for Sheets; export target
_SHEETS_MIME = "application/vnd.google-apps.spreadsheet"
_EXPORT_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_XLSX_MIMES = {
    _EXPORT_MIME,
    "application/vnd.ms-excel",
    "application/octet-stream",
}


# ─── Auth ─────────────────────────────────────────────────────────────────────
def _build_drive_service(credentials_info: dict):
    """Build an authenticated Drive v3 service from a service account dict."""
    creds = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ─── File listing ─────────────────────────────────────────────────────────────
def _list_files(service, folder_ids: list[str]) -> list[dict]:
    """
    Return metadata for all xlsx / Google Sheets files in the given folders.
    Handles pagination automatically.
    """
    files: list[dict] = []
    for folder_id in folder_ids:
        q = (
            f"'{folder_id}' in parents and trashed=false and ("
            f"mimeType='{_SHEETS_MIME}' or "
            f"mimeType='{_EXPORT_MIME}' or "
            f"mimeType='application/vnd.ms-excel')"
        )
        page_token = None
        while True:
            resp = service.files().list(
                q=q,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageToken=page_token,
            ).execute()
            files.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    return files


# ─── Download ─────────────────────────────────────────────────────────────────
def _download_file(service, file_meta: dict) -> bytes:
    """Download or export a Drive file as xlsx bytes."""
    file_id = file_meta["id"]
    mime = file_meta.get("mimeType", "")

    if mime == _SHEETS_MIME:
        # Google Sheets → export as xlsx
        request = service.files().export_media(fileId=file_id, mimeType=_EXPORT_MIME)
    else:
        request = service.files().get_media(fileId=file_id)

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


# ─── Excel parsing ────────────────────────────────────────────────────────────
def _detect_sheet_role(sheet_title: str) -> str:
    """
    Guess whether a sheet holds properties or contacts based on its title.
    Returns 'properties', 'contacts', or 'unknown'.
    """
    title = sheet_title.lower()
    if any(k in title for k in ("prop", "inmueble", "listing", "ficha")):
        return "properties"
    if any(k in title for k in ("contact", "cliente", "lead", "buyer")):
        return "contacts"
    return "unknown"


def parse_workbook(xlsx_bytes: bytes, source_name: str = "drive") -> dict[str, list[dict]]:
    """
    Parse an xlsx workbook and return normalized rows per role.
    Returns: {"properties": [...], "contacts": [...]}
    """
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    result: dict[str, list[dict]] = {"properties": [], "contacts": []}

    for sheet in wb.worksheets:
        role = _detect_sheet_role(sheet.title)
        if role == "unknown" and len(wb.worksheets) == 1:
            # Single-sheet workbook: try properties first
            role = "properties"
        if role == "unknown":
            log.debug("drive.sheet_skipped", sheet=sheet.title)
            continue

        column_map = _PROPERTY_COLUMN_MAP if role == "properties" else _CONTACT_COLUMN_MAP
        rows_iter = sheet.iter_rows(values_only=True)

        try:
            raw_headers = [str(h or "") for h in next(rows_iter)]
        except StopIteration:
            continue

        headers = normalize_headers(raw_headers, column_map)

        for raw_row in rows_iter:
            if all(v is None or str(v).strip() == "" for v in raw_row):
                continue  # skip blank rows
            row_dict = dict(zip(headers, [str(v) if v is not None else "" for v in raw_row]))
            try:
                if role == "properties":
                    result["properties"].append(parse_excel_property_row(row_dict, source_name))
                else:
                    result["contacts"].append(parse_excel_contact_row(row_dict))
            except Exception as exc:
                log.warning("drive.row_parse_error", sheet=sheet.title, error=str(exc))

    wb.close()
    return result


# ─── Main sync function ───────────────────────────────────────────────────────
async def run_drive_sync(source_config: dict) -> dict:
    """
    Main entry point for the Drive sync worker.
    source_config comes from scraping_sources (source_type='google_drive').

    Required config keys:
      credentials   — service account JSON dict (from env/secret, never stored raw)
      folder_ids    — list of Drive folder IDs to scan
      source_name   — label stored in property.source / client.source
    """
    source_id = source_config.get("id", "drive")

    if circuit_breaker.is_open(source_id):
        log.warning("drive.circuit_open_skip", source=source_id)
        return {"status": "circuit_open", "source": source_id}

    credentials_info = source_config.get("credentials")
    folder_ids = source_config.get("folder_ids", [])
    source_name = source_config.get("source_name", "drive")

    if not credentials_info or not folder_ids:
        log.error("drive.missing_config", source=source_id)
        return {"status": "config_error", "source": source_id, "error": "credentials or folder_ids missing"}

    from app.core.database import AsyncSessionLocal

    start = datetime.now(timezone.utc)
    log.info("drive.sync_start", source=source_id, folders=len(folder_ids))

    total_props_ins = total_props_skip = 0
    total_contacts_ins = total_contacts_skip = 0
    files_processed = 0

    try:
        service = _build_drive_service(credentials_info)
        files = _list_files(service, folder_ids)
        log.info("drive.files_found", source=source_id, count=len(files))

        for file_meta in files:
            try:
                xlsx_bytes = _download_file(service, file_meta)
                parsed = parse_workbook(xlsx_bytes, source_name)

                async with AsyncSessionLocal() as db:
                    p_ins, p_skip = await _upsert_properties(parsed["properties"], db)
                    c_ins, c_skip = await _upsert_contacts(parsed["contacts"], db)

                total_props_ins += p_ins
                total_props_skip += p_skip
                total_contacts_ins += c_ins
                total_contacts_skip += c_skip
                files_processed += 1

                log.info(
                    "drive.file_done",
                    file=file_meta["name"],
                    props_inserted=p_ins,
                    contacts_inserted=c_ins,
                )
            except Exception as exc:
                log.warning("drive.file_error", file=file_meta.get("name"), error=str(exc))

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        circuit_breaker.record_success(source_id)

        result = {
            "status": "ok",
            "source": source_id,
            "files_processed": files_processed,
            "properties": {"inserted": total_props_ins, "skipped": total_props_skip},
            "contacts": {"inserted": total_contacts_ins, "skipped": total_contacts_skip},
            "elapsed_s": round(elapsed, 2),
        }
        log.info("drive.sync_complete", **result)
        return result

    except Exception as exc:
        circuit_breaker.record_failure(source_id)
        log.error("drive.sync_error", source=source_id, error=str(exc))
        return {"status": "error", "source": source_id, "error": str(exc)}
