"""RFQ Bid Risk Identification Agent for Telecom & Security Systems.

This package provides a structured, rule-based pipeline for extracting
telecom and security system specification data from RFQ PDFs and
identifying bid-preparation risks across six orthogonal dimensions.

Modules:
    models      – Domain dataclasses and enumerations.
    extractor   – PDF text extraction and section classification.
    rules       – Risk rule definitions and evaluation engine.
    report      – Risk register export (CSV, Markdown, JSON).

Nexus Framework Layer: L1 (Aspirational) — top-level package identity.
"""

__version__ = "1.0.0"

from rfq_risk_agent.models import (
    ObligationType,
    PageClassification,
    ProjectContext,
    Risk,
    RiskDimension,
    RiskRegister,
    RiskRule,
    RiskSeverity,
    ShallStatement,
    SpecDocument,
    SpecSection,
)

__all__ = [
    "ObligationType",
    "PageClassification",
    "ProjectContext",
    "Risk",
    "RiskDimension",
    "RiskRegister",
    "RiskRule",
    "RiskSeverity",
    "ShallStatement",
    "SpecDocument",
    "SpecSection",
]
