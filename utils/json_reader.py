import json
import os
from pathlib import Path


class DataLoader:
    @staticmethod
    def get_data(file_path):
        """
        Reads JSON data from a file.
        If file_path is not absolute, it tries to find it relative to the project root.
        """
        path = Path(file_path)
        
        if not path.is_absolute():
            # Assume it's relative to project root
            base_path = Path(__file__).parent.parent
            path = base_path / file_path

        if not path.exists():
            raise FileNotFoundError(f"JSON data file not found at: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)