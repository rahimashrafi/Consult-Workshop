from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class Article:
    title: str
    url: str
    source_name: str
    category: str
    language: str
    published: datetime
    summary: str = ""
    # Set by the LLM processor
    tier: Literal[1, 2, 3, 0] = 0  # 0 = unscored
    tier_reason: str = ""
