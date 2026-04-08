"""
Writes the AI-generated scaffold files to the correct project directories.
"""

import json
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def write_scaffold(lob_name: str, files: dict[str, str]) -> list[str]:
    """
    Write all generated files to the appropriate project paths.

    Args:
        lob_name: e.g. "workers_comp"
        files:    dict from ai_enricher.generate_scaffold()

    Returns:
        List of written file paths (relative to project root).
    """
    lob_class = "".join(w.capitalize() for w in lob_name.split("_"))
    written = []

    mapping = {
        "page_object":      _PROJECT_ROOT / "ui" / "pages" / lob_name / f"{lob_name}_quote_page.py",
        "feature_file":     _PROJECT_ROOT / "ui" / "features" / lob_name / f"{lob_name}_creation.feature",
        "step_definitions": _PROJECT_ROOT / "ui" / "steps" / f"{lob_name}_steps.py",
        "test_entry":       _PROJECT_ROOT / "ui" / "tests" / f"test_{lob_name}.py",
        "test_data":        _PROJECT_ROOT / "testdata" / "static" / f"{lob_class}Data.json",
    }

    for key, path in mapping.items():
        content = files.get(key)
        if not content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure __init__.py exists in new page / feature directories
        if key == "page_object":
            init = path.parent / "__init__.py"
            if not init.exists():
                init.write_text("")

        path.write_text(content, encoding="utf-8")
        written.append(str(path.relative_to(_PROJECT_ROOT)))

    return written
