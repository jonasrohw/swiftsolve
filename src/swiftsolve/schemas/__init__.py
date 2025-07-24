"""
swiftsolve.schemas  •  Unified Pydantic-v2 message contracts
------------------------------------------------------------
These classes are **the only canonical interface** by which agents, the
controller, and the FastAPI layer exchange data.  DO NOT modify field
names or enum literals without bumping `SCHEMA_VERSION`.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Literal
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ConfigDict, constr

SCHEMA_VERSION = "1.0.0"

# --------------------------------------------------------------------------- #
# 🔸 Enumerations
# --------------------------------------------------------------------------- #
class MessageType(str, Enum):
    PLAN            = "plan"
    CODE            = "code"
    PROFILE_REPORT  = "profile_report"
    VERDICT         = "verdict"
    RUN_RESULT      = "run_result"          # API response only


class TargetAgent(str, Enum):
    PLANNER = "PLANNER"
    CODER   = "CODER"


class RunStatus(str, Enum):
    SUCCESS               = "success"
    STATIC_PRUNE_FAILED   = "static_prune_failed"
    FAILED                = "failed"
    SANDBOX_ERROR         = "sandbox_error"


# --------------------------------------------------------------------------- #
# 🔸 Core envelope mixed into every on-loop message
# --------------------------------------------------------------------------- #
class _BaseMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: MessageType                       = Field(..., description="Message discriminator")
    task_id: constr(strip_whitespace=True)  = Field(..., examples=["B001"])
    iteration: int                          = Field(..., ge=0)
    timestamp_utc: datetime                 = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="ISO-8601 UTC timestamp",
    )
    schema_version: Literal["1.0.0"] = Field(default=SCHEMA_VERSION, description="Schema version")


# --------------------------------------------------------------------------- #
# 🔸 Concrete payloads
# --------------------------------------------------------------------------- #
class PlanMessage(_BaseMessage):
    type: Literal[MessageType.PLAN] = Field(default=MessageType.PLAN)
    algorithm: str
    input_bounds: Dict[str, int]            = Field(..., examples=[{"n": 100000}])
    constraints: Dict[str, int]             = Field(
        ..., description="e.g. {'runtime_limit': 2000, 'memory_limit': 512}"
    )
    retrieval_templates: Optional[List[str]] = None
    algorithm_id: Optional[str]              = Field(
        None, description="Canonical ID if retrieved from a template bank"
    )
    model_version: Optional[str]             = None   # claude build hash
    seed: Optional[int]                      = None   # future reproducibility


class CodeMessage(_BaseMessage):
    type: Literal[MessageType.CODE] = Field(default=MessageType.CODE)
    code_cpp: str                            = Field(..., description="ISO C++17 source code")
    compiler_flags: List[str]                = Field(default_factory=lambda: ["-O2", "-std=c++17"])
    model_version: Optional[str]             = None   # gpt-4.1 build hash
    seed: Optional[int]                      = None


class ProfileReport(_BaseMessage):
    type: Literal[MessageType.PROFILE_REPORT] = Field(default=MessageType.PROFILE_REPORT)
    input_sizes: List[int]
    runtime_ms: List[float]
    peak_memory_mb: List[float]
    hotspots: Dict[str, str]                 = Field(
        default_factory=dict,
        description="Maps code locations (e.g., 'line_23') to human hints",
    )


class VerdictMessage(_BaseMessage):
    type: Literal[MessageType.VERDICT] = Field(default=MessageType.VERDICT)
    efficient: bool
    target_agent: Optional[TargetAgent]      = Field(None, description="Receiver of next patch")
    patch: Optional[str]                     = None
    perf_gain: Optional[float]               = Field(
        None, ge=0.0, le=1.0, description="Fractional improvement vs previous iter"
    )


# --------------------------------------------------------------------------- #
# 🔸 External-facing payloads
# --------------------------------------------------------------------------- #
class ProblemInput(BaseModel):
    """Inbound object for FastAPI /solve."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: constr(strip_whitespace=True)
    prompt: str
    constraints: Dict[str, int]              = Field(..., examples=[{"runtime_limit": 2000}])
    unit_tests: List[Dict[str, str]]


class RunResult(BaseModel):
    """Outbound object returned by /solve."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal[MessageType.RUN_RESULT] = Field(default=MessageType.RUN_RESULT)
    task_id: str