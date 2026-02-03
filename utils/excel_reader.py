import os

import pandas as pd


class ExcelReader:
    @staticmethod
    def get_excel_data(file_path, sheet_name="Sheet1", header_row=1, debug=False):
        """
        Reads Excel file and returns a list of rows as dictionaries.

        - header_row=1 means: second row in Excel is the header (first row is a title).
          If your header is on a different row, change this value.
        - Reads values as strings to preserve leading zeros (e.g. 0003).
        - Normalizes column names: strip + upper
        """
        # If path is relative, convert to absolute from project root
        if not os.path.isabs(file_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base_dir, file_path)

        if debug:
            print(f"DEBUG Excel path: {os.path.abspath(file_path)}")
            print(f"DEBUG Exists: {os.path.exists(file_path)}")
            print(f"DEBUG Sheet: {sheet_name}, header_row: {header_row}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Excel file not found: {os.path.abspath(file_path)}")

        # Read the Excel file
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine="openpyxl",
            dtype=str,          # keep everything as string (preserve 0003)
            header=header_row   # <-- IMPORTANT: skip title row; use next row as header
        )

        # Normalize columns
        df.columns = [str(c).strip().upper() for c in df.columns]
        df = df.fillna("")

        if debug:
            print("DEBUG Columns:", df.columns.tolist())
            print("DEBUG Row count:", len(df))
            if len(df) > 0:
                print("DEBUG First row:", df.iloc[0].to_dict())

        rows = df.to_dict(orient="records")

        # Safety checks (helpful errors instead of KeyError later)
        if not rows:
            raise AssertionError(
                f"No data rows read from Excel. file={os.path.abspath(file_path)}, sheet={sheet_name}. "
                f"Check header_row={header_row} and sheet name."
            )

        # Optional: hard check for TC_ID existence if your framework relies on it
        if "TC_ID" not in df.columns:
            raise KeyError(
                f"Column 'TC_ID' not found. Found columns: {df.columns.tolist()}. "
                f"Your header might not be on row {header_row+1} in Excel."
            )

        return rows