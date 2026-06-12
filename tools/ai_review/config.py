import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ReviewConfig:
    # Provider / model
    llm_provider: Optional[str] = None        # anthropic | openai | None (auto-detect)
    review_model: Optional[str] = None        # explicit model override

    # What to post
    review_mode: str = "inline"               # inline | summary | both
    review_focus: list = field(default_factory=lambda: ["bugs", "security", "performance", "style"])

    # Noise controls
    min_severity: str = "warning"             # error | warning | info
    max_diff_lines: int = 500                 # skip files larger than this
    max_total_lines: int = 2000               # abort the whole review if diff is too large
    skip_paths: list = field(default_factory=lambda: [
        "*.lock", "*.lockb", "dist/**", "__pycache__/**",
        "*.min.js", "*.min.css", "*.pb.go", "*.generated.*",
        "allure-results/**", "reports/**",
    ])

    dry_run: bool = False

    @classmethod
    def from_env(cls) -> "ReviewConfig":
        focus_raw = os.getenv("REVIEW_FOCUS", "bugs,security,performance,style")
        skip_raw = os.getenv(
            "REVIEW_SKIP_PATHS",
            "*.lock,*.lockb,dist/**,__pycache__/**,*.min.js,*.min.css,allure-results/**,reports/**",
        )
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER") or None,
            review_model=os.getenv("REVIEW_MODEL") or None,
            review_mode=os.getenv("REVIEW_MODE", "inline"),
            review_focus=[f.strip() for f in focus_raw.split(",") if f.strip()],
            min_severity=os.getenv("MIN_SEVERITY", "warning"),
            max_diff_lines=int(os.getenv("MAX_DIFF_LINES", "500")),
            max_total_lines=int(os.getenv("MAX_TOTAL_LINES", "2000")),
            skip_paths=[p.strip() for p in skip_raw.split(",") if p.strip()],
            dry_run=os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"),
        )
