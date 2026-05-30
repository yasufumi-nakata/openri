from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

SCHEMA_VERSION = "openri-report-v1"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Status(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class Evidence(BaseModel):
    quote: Optional[str] = None
    location: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: f"finding_{uuid4().hex[:10]}")
    check_id: str
    title: str
    category: str
    severity: Severity
    status: Status
    score: int = Field(ge=0, le=100)
    message: str
    recommendation: str
    evidence: List[Evidence] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    total_checks: int
    score: int = Field(ge=0, le=100)
    passed: int
    warnings: int
    failed: int
    skipped: int
    severity_counts: Dict[Severity, int]


class RunRequest(BaseModel):
    manuscript_text: str = Field(min_length=1)
    title: str = "Untitled manuscript"
    strictness: Literal["lenient", "standard", "strict"] = "standard"
    review_mode: Literal["integrity_triage", "ai_reviewer_replication"] = "ai_reviewer_replication"
    include_experimental_checks: bool = True
    activated_rulesets: List[str] = Field(default_factory=list)
    enable_network: bool = False
    pdf_inspection: Optional[Dict[str, Any]] = None
    image_inspection: Optional[Dict[str, Any]] = None
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


class RunReport(BaseModel):
    schema_version: str = SCHEMA_VERSION
    report_id: str = Field(default_factory=lambda: f"openri_{uuid4().hex[:12]}")
    title: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    objective: str
    strictness: str
    summary: RunSummary
    findings: List[Finding]
    manuscript_profile: Dict[str, Any]
    submission_processing: Dict[str, Any] = Field(default_factory=dict)
    ai_review_protocol: Dict[str, Any] = Field(default_factory=dict)
    accountability: Dict[str, Any] = Field(default_factory=dict)


class CheckDefinition(BaseModel):
    id: str
    title: str
    category: str
    description: str
    maturity: Literal["stable", "beta", "experimental"]
