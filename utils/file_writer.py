import csv
import os
from datetime import datetime


def save_summary_to_csv(details, folder_name="policy_summary", file_name="policy_reports.csv"):
    # Create folder if it doesn't exist
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    file_path = os.path.join(folder_name, file_name)
    file_exists = os.path.isfile(file_path)
    fieldnames = list(details.keys())

    if file_exists and _header_mismatch(file_path, fieldnames):
        archive_path = _archive_path(file_path)
        os.replace(file_path, archive_path)
        file_exists = False

    # 2. Writing in CVS (mode 'a' - append, so that we don't overwrite existing data)
    with open(file_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        # If it is a new file, write the header
        if not file_exists:
            writer.writeheader()

        writer.writerow(details)

    return file_path


def _header_mismatch(file_path, fieldnames):
    with open(file_path, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            existing_header = next(reader)
        except StopIteration:
            return False
    return existing_header != fieldnames


def _archive_path(file_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root, ext = os.path.splitext(file_path)
    return f"{root}_schema_mismatch_{timestamp}{ext}"
