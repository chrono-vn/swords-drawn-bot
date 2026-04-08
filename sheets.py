import gspread, json, os
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone
from config import CREDS_FILE, SHEET_ID

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def log_commendation(type_, target_name, target_id, giver_name, giver_id, reason):
    sheet    = get_sheet()
    log_tab  = sheet.worksheet("log")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    log_tab.append_row([
        timestamp, type_, target_name, str(target_id),
        giver_name, str(giver_id), reason
    ])

def update_members_tab(target_name, target_id, type_):
    sheet      = get_sheet()
    members    = sheet.worksheet("members")
    all_rows   = members.get_all_records()
    target_id_str = str(target_id)
    now        = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    for i, row in enumerate(all_rows, start=2):  # row 1 is headers
        if str(row["discord_id"]) == target_id_str:
            if type_ == "commend":
                new_count = int(row["commend_count"] or 0) + 1
                members.update_cell(i, 4, new_count)   # commend_count column
            else:
                new_count = int(row["demerit_count"] or 0) + 1
                members.update_cell(i, 5, new_count)   # demerit_count column
            members.update_cell(i, 6, now)              # last_updated column
            return

    # Member not in sheet yet — add them
    members.append_row([
        target_id_str, target_name, "Member",
        1 if type_ == "commend" else 0,
        1 if type_ == "demerit" else 0,
        now
    ])