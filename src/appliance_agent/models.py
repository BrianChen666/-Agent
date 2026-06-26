from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class Chunk:
    text: str
    metadata: dict[str, Any]
    doc_id: str


@dataclass(frozen=True)
class RetrievedDoc:
    doc_id: str
    text: str
    metadata: dict[str, Any]
    score: float


@dataclass(frozen=True)
class GuardrailResult:
    risk: Literal["none", "high_signal", "forbidden_request"]
    signal: str | None = None


@dataclass
class DiagnosisState:
    flow_id: str
    question_index: int = 0
    pending_question: str | None = None
    answers: dict[str, str] = field(default_factory=dict)
    done: bool = False


@dataclass(frozen=True)
class StepResult:
    kind: Literal["ask", "advise", "switch_flow", "retrieve", "escalate"]
    payload: str
    flow_done: bool = False


@dataclass(frozen=True)
class ChatResponse:
    answer: str
    intent: str
    contexts: list[str]
    citations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
