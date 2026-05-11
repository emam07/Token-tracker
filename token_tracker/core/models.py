import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Warning:
    rule: str
    severity: str       # "low" | "medium" | "high"
    message: str
    suggestion: str


@dataclass
class PromptAnalysis:
    estimated_input_tokens: int
    estimated_cost_usd: float
    efficiency_score: int
    warnings: list[Warning]
    suggested_rewrite: str = ""
    token_delta: int = 0   # positive = tokens saved, negative = tokens added


@dataclass
class Session:
    name: str = "default"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None


@dataclass
class UsageRecord:
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    prompt_hash: str = ""
    efficiency_score: int | None = None
    flagged: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
