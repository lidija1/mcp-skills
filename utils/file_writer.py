import csv
import os


def save_summary_to_csv(details, folder_name="policy_summary"):
    # Create folder if it doesn't exist
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    file_path = os.path.join(folder_name, "policy_reports.csv")
    file_exists = os.path.isfile(file_path)

    # 2. Writing in CVS (mode 'a' - append, so that we don't overwrite existing data)
    with open(file_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=details.keys())

        # If it is a new file, write the header
        if not file_exists:
            writer.writeheader()

        writer.writerow(details)

    return file_path