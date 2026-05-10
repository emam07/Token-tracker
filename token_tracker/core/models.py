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
    warnings: list
    suggested_rewrite: str = ""   # populated in Phase 3
    token_savings: int = 0        # populated in Phase 3


@dataclass
class Session:
    name: str = "default"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.utcnow)
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
    timestamp: datetime = field(default_factory=datetime.utcnow)
