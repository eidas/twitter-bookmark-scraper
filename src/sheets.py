import gspread
from google.oauth2.service_account import Credentials


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_client(credentials_path: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


def get_worksheet(
    client: gspread.Client, spreadsheet_id: str, worksheet_name: str
) -> gspread.Worksheet:
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(worksheet_name)


def get_existing_urls(worksheet: gspread.Worksheet) -> set[str]:
    urls = worksheet.col_values(1)  # A列
    return set(urls)


def append_bookmarks(
    worksheet: gspread.Worksheet, bookmarks: list[dict]
) -> int:
    existing = get_existing_urls(worksheet)
    rows = []
    for bm in bookmarks:
        if bm["url"] in existing:
            continue
        rows.append([bm["url"], bm["datetime_hint"], "pending"])

    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)


def get_pending_urls(worksheet: gspread.Worksheet) -> list[dict]:
    records = worksheet.get_all_values()
    pending = []
    for i, row in enumerate(records, start=1):
        if len(row) < 3:
            continue
        url, _, status = row[0], row[1], row[2]
        # D列（投稿日時）が空で、ステータスが remove 以外
        has_details = len(row) >= 4 and row[3].strip()
        if status.strip().lower() != "remove" and url and not has_details:
            pending.append({"row": i, "url": url})
    return pending


def update_details(
    worksheet: gspread.Worksheet,
    row_number: int,
    post_date: str,
    image_formula: str,
) -> None:
    worksheet.update_cell(row_number, 4, post_date)  # D列
    if image_formula:
        worksheet.update_cell(row_number, 5, image_formula)  # E列
