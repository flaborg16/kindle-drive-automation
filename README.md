# Kindle Drive Automation

Free personal automation for two workflows:

1. **Books_To_Kindle → convert if needed → Send to Kindle email → Sent_To_Kindle**
2. **Notebooks PDF exports → extract Kindle highlights/notes → artistic quote PNGs → Quotations/<Book - Author>/**

This project is built for Google Drive + Kindle Paperwhite/Kindle devices. It does not bypass DRM, remove copy protection, or download copyrighted books. It sends only files that you provide in your Drive folder.

## Drive folder layout

Create or share one root folder with the Google service account:

```text
Kindle_Automation/
  Books_To_Kindle/
  Notebooks/
  Sent_To_Kindle/
  Processed_Notebooks/
  Failed/
  Quotations/
```

The script can create missing folders automatically, but the root folder must be visible to the service account.

## What file types can be handled?

### Sent directly to Kindle when already accepted

- `.epub`, `.pdf`, `.doc`, `.docx`, `.txt`, `.rtf`, `.html`, `.htm`
- `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`

### Converted first when possible

- Markdown: `.md`, `.markdown` → `.html`
- Office/LibreOffice: `.odt`, `.ods`, `.odp`, `.ppt`, `.pptx`, `.xls`, `.xlsx`, `.csv` → `.pdf` using LibreOffice if available
- Old ebook formats: `.mobi`, `.azw`, `.azw3`, `.fb2` → `.epub` using Calibre `ebook-convert` if available and DRM-free
- Comic archives: `.cbz` → `.pdf`
- Unknown text-like files → `.txt`

### Not supported

- DRM-protected ebooks
- encrypted PDFs
- binary files that are not documents/books
- random app installers/executables
- very large files above the email attachment limit

## Setup overview

### 1. Google Cloud / Drive API

Create a Google Cloud project, enable Google Drive API, create a **service account**, download the JSON key, then share the `Kindle_Automation` Drive folder with the service account email.

### 2. Gmail app password

Use a Gmail account with 2-step verification enabled. Create an app password and put it in `SMTP_APP_PASSWORD`.

Your sending Gmail address must be added to Amazon's **Approved Personal Document E-mail List**.

### 3. Kindle email

Find your Kindle email in Amazon → Content & Devices → Devices → your Kindle.

### 4. Local run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env
python -m kindle_drive_automation.main
```

### 5. GitHub Actions 24/7 run

Add these repository secrets:

```text
GOOGLE_SERVICE_ACCOUNT_JSON
SMTP_USERNAME
SMTP_APP_PASSWORD
KINDLE_EMAIL
```

Then use the included workflow in `.github/workflows/kindle-automation.yml`.

For a private repository, scheduled Actions can eat your free minutes fast. A public repo is usually the cheapest/free route, but never commit secrets directly; use GitHub Secrets only.

## Notes on internet-downloaded books/files

You can send files downloaded from the internet to Kindle **only if you have the legal right to possess/read that file** and it is not DRM-protected. Good examples: Project Gutenberg books, public domain PDFs, your own documents, purchased DRM-free EPUB/PDF files, papers, manuals, and reports.

Do not use this to copy pirated books or bypass DRM.
