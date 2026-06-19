from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .config import settings
from .converter import convert_for_kindle
from .google_drive import DriveClient
from .kindle_sender import send_to_kindle
from .notebook_parser import parse_notebook_pdf
from .quote_art import render_quote_image, write_metadata
from .utils import safe_filename


def main() -> None:
    workdir = Path(tempfile.mkdtemp(prefix="kindle_drive_automation_"))
    print(f"Working directory: {workdir}")
    try:
        drive = DriveClient(settings.google_service_account_json, settings.google_service_account_file)
        folders = ensure_drive_folders(drive)
        process_books(drive, folders, workdir)
        process_notebooks(drive, folders, workdir)
    finally:
        if settings.delete_local_workdir_after_run:
            shutil.rmtree(workdir, ignore_errors=True)


def ensure_drive_folders(drive: DriveClient) -> dict[str, str]:
    root = drive.ensure_folder(settings.kindle_root_folder_name)
    return {
        "root": root,
        "books": drive.ensure_folder(settings.books_folder_name, root),
        "notebooks": drive.ensure_folder(settings.notebooks_folder_name, root),
        "sent": drive.ensure_folder(settings.sent_folder_name, root),
        "processed_notebooks": drive.ensure_folder(settings.processed_notebooks_folder_name, root),
        "failed": drive.ensure_folder(settings.failed_folder_name, root),
        "quotations": drive.ensure_folder(settings.quotations_folder_name, root),
    }


def process_books(drive: DriveClient, folders: dict[str, str], workdir: Path) -> None:
    files = drive.list_files(folders["books"])
    files = [f for f in files if f.get("mimeType") != "application/vnd.google-apps.folder"]
    if not files:
        print("No books/files waiting to send.")
        return

    for item in files:
        print(f"Book pipeline: {item['name']}")
        local_in = workdir / "books" / safe_filename(item["name"])
        local_in.parent.mkdir(parents=True, exist_ok=True)
        try:
            drive.download_file(item["id"], local_in)
            converted_files = convert_for_kindle(local_in, workdir / "converted" / safe_filename(local_in.stem))
            for path in converted_files:
                send_to_kindle(path, settings)
                print(f"Sent to Kindle: {path.name}")
            drive.move_file(item["id"], folders["sent"])
        except Exception as exc:
            print(f"FAILED book pipeline for {item['name']}: {exc}")
            try:
                drive.update_description(item["id"], f"Kindle automation failed: {exc}")
                drive.move_file(item["id"], folders["failed"])
            except Exception as move_exc:
                print(f"Also failed to move to Failed folder: {move_exc}")


def process_notebooks(drive: DriveClient, folders: dict[str, str], workdir: Path) -> None:
    files = drive.list_files(folders["notebooks"])
    files = [f for f in files if f.get("mimeType") != "application/vnd.google-apps.folder"]
    pdfs = [f for f in files if f["name"].lower().endswith(".pdf")]
    if not pdfs:
        print("No notebook PDFs waiting to parse.")
        return

    for item in pdfs:
        print(f"Notebook pipeline: {item['name']}")
        local_pdf = workdir / "notebooks" / safe_filename(item["name"])
        local_pdf.parent.mkdir(parents=True, exist_ok=True)
        try:
            drive.download_file(item["id"], local_pdf)
            annotations = parse_notebook_pdf(local_pdf, process_notes_as_quotes=settings.process_notes_as_quotes)
            if not annotations:
                raise RuntimeError("No highlights found in notebook PDF")

            first = annotations[0]
            folder_name = safe_filename(f"{first.book_title} - {first.first_author}")
            book_quote_folder = drive.ensure_folder(folder_name, folders["quotations"])

            local_quote_dir = workdir / "quote_images" / folder_name
            for idx, ann in enumerate(annotations, start=1):
                image_path = render_quote_image(
                    ann,
                    local_quote_dir,
                    width=settings.quote_image_width,
                    height=settings.quote_image_height,
                    index=idx,
                )
                drive.upload_file(image_path, book_quote_folder, image_path.name, "image/png")
                print(f"Uploaded quotation image: {image_path.name}")

            metadata_path = write_metadata(annotations, local_quote_dir)
            drive.upload_file(metadata_path, book_quote_folder, metadata_path.name, "application/json")
            drive.move_file(item["id"], folders["processed_notebooks"])
        except Exception as exc:
            print(f"FAILED notebook pipeline for {item['name']}: {exc}")
            try:
                drive.update_description(item["id"], f"Notebook quote automation failed: {exc}")
                drive.move_file(item["id"], folders["failed"])
            except Exception as move_exc:
                print(f"Also failed to move to Failed folder: {move_exc}")


if __name__ == "__main__":
    main()
