"""
RFQ Bid Risk Identification Agent — Data Models
=================================================

Defines the core domain models used throughout the risk analysis pipeline:

- **Enumerations**: RiskDimension, RiskSeverity, ObligationType, PageClassification
- **Extraction Models**: ShallStatement, SpecSection, SpecDocument
- **Risk Models**: RiskRule, Risk, RiskRegister
- **Context Model**: ProjectContext

All models use Python dataclasses with full type hints.
Serialisation helpers (to_dict, to_csv_rows, to_markdown) are provided
for downstream reporting.

Nexus Framework Layer: L2 (Global Strategy) — domain vocabulary that
every downstream component depends on.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────
#  Enumerations
# ──────────────────────────────────────────────

class RiskDimension(Enum):
    """Six orthogonal risk dimensions used to classify every finding.

    Each dimension maps to a specific area of concern when reviewing
    telecom & security-system RFQ specifications.
    """

    D1_STANDARDS_COMPLIANCE = "D1_STANDARDS_COMPLIANCE"
    D2_SCOPE_COMPLETENESS = "D2_SCOPE_COMPLETENESS"
    D3_TECHNICAL_ADEQUACY = "D3_TECHNICAL_ADEQUACY"
    D4_DOCUMENTATION_GAPS = "D4_DOCUMENTATION_GAPS"
    D5_INTERFACE_COORDINATION = "D5_INTERFACE_COORDINATION"
    D6_COMMERCIAL_SCHEDULE = "D6_COMMERCIAL_SCHEDULE"


class RiskSeverity(Enum):
    """Qualitative severity buckets derived from probability × impact scoring."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ObligationType(Enum):
    """Categories of contractual obligation extracted from *shall* statements."""

    DESIGN = "DESIGN"
    SUPPLY = "SUPPLY"
    TESTING = "TESTING"
    DOCUMENTATION = "DOCUMENTATION"
    INTERFACE = "INTERFACE"


class PageClassification(Enum):
    """Semantic labels assigned to specification pages / sections.

    Used by the section classifier to tag extracted text blocks so that
    downstream rules can target specific parts of the document.
    """

    COVER = "COVER"
    TOC = "TOC"
    REFERENCES = "REFERENCES"
    SCOPE_OF_WORK = "SCOPE_OF_WORK"
    SYSTEM_DESCRIPTION = "SYSTEM_DESCRIPTION"
    INSTALLATION_COMMISSIONING = "INSTALLATION_COMMISSIONING"
    TESTING = "TESTING"
    SPARES_TRAINING = "SPARES_TRAINING"
    APPENDIX = "APPENDIX"
    UNKNOWN = "UNKNOWN"


# ──────────────────────────────────────────────
#  Extraction Models
# ──────────────────────────────────────────────

@dataclass
class ShallStatement:
    """A single contractual obligation extracted from a specification.

    Attributes:
        text: The full sentence or clause containing the *shall* keyword.
        page: 1-based page number where the statement was found.
        clause: The specification clause reference (e.g. ``"3.2.1"``).
        obligation_type: Categorised obligation (DESIGN, SUPPLY, …).
    """

    text: str
    page: int
    clause: str
    obligation_type: ObligationType


@dataclass
class SpecSection:
    """A contiguous block of text belonging to a classified section.

    Attributes:
        section_type: The semantic label for this section.
        page_range: ``(start_page, end_page)`` inclusive, 1-based.
        text: The raw extracted text content.
        title: Optional human-readable section title.
    """

    section_type: PageClassification
    page_range: tuple[int, int]
    text: str
    title: str = ""


@dataclass
class SpecDocument:
    """Parsed representation of a single specification PDF.

    Holds both raw content and structured extractions (sections,
    shall-statements, referenced standards / drawings, equipment
    mentions).  Acts as the primary input artefact for the risk
    analysis engine.

    Attributes:
        file_path: Absolute path to the source PDF.
        document_id: Short identifier (e.g. ``"09-SAMSS-711"``).
        title: Document title extracted from cover / header.
        revision: Revision code (e.g. ``"Rev.5"``).
        total_pages: Total number of pages in the source PDF.
        referenced_standards: List of standard numbers cited in the document.
        referenced_drawings: List of drawing numbers cited in the document.
        sections: Classified sections extracted from the document.
        shall_statements: All obligation statements found.
        equipment_mentions: Unique equipment names / model references found.
        full_text: Concatenated full text of the entire document.
    """

    file_path: Path
    document_id: str
    title: str
    revision: str
    total_pages: int
    referenced_standards: list[str] = field(default_factory=list)
    referenced_drawings: list[str] = field(default_factory=list)
    sections: list[SpecSection] = field(default_factory=list)
    shall_statements: list[ShallStatement] = field(default_factory=list)
    equipment_mentions: list[str] = field(default_factory=list)
    full_text: str = ""

    # -- Serialisation -------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the document model to a JSON-compatible dictionary.

        Returns:
            A plain ``dict`` with all nested dataclasses and enums
            converted to their primitive representations.
        """
        return {
            "file_path": str(self.file_path),
            "document_id": self.document_id,
            "title": self.title,
            "revision": self.revision,
            "total_pages": self.total_pages,
            "referenced_standards": list(self.referenced_standards),
            "referenced_drawings": list(self.referenced_drawings),
            "sections": [
                {
                    "section_type": sec.section_type.value,
                    "page_range": list(sec.page_range),
                    "text": sec.text,
                    "title": sec.title,
                }
                for sec in self.sections
            ],
            "shall_statements": [
                {
                    "text": stmt.text,
                    "page": stmt.page,
                    "clause": stmt.clause,
                    "obligation_type": stmt.obligation_type.value,
                }
                for stmt in self.shall_statements
            ],
            "equipment_mentions": list(self.equipment_mentions),
            "full_text": self.full_text,
        }

    # -- Query helpers -------------------------------------------------

    def get_section_text(self, section_type: PageClassification) -> str:
        """Return the concatenated text of all sections matching *section_type*.

        Args:
            section_type: The ``PageClassification`` label to filter on.

        Returns:
            A single string with a newline separator between matching
            section blocks.  Returns an empty string when no sections
            match.
        """
        matching = [
            sec.text
            for sec in self.sections
            if sec.section_type == section_type
        ]
        return "\n".join(matching)


# ──────────────────────────────────────────────
#  Risk Models
# ──────────────────────────────────────────────

@dataclass
class RiskRule:
    """A declarative rule that the analysis engine evaluates against a spec.

    Each rule targets one :class:`RiskDimension` and describes a
    *trigger condition* — a pattern or absence that, when detected,
    generates a :class:`Risk` entry.

    Attributes:
        rule_id: Unique rule identifier (e.g. ``"R-D1-001"``).
        dimension: Which risk dimension this rule belongs to.
        check_description: Human-readable summary of what is checked.
        trigger_condition: Description of the pattern that fires the rule.
        default_probability: Default probability score (1–5).
        default_impact: Default impact score (1–5).
        keywords: Regex-friendly keywords used for fast pre-filtering.
        applicable_subsystems: Subsystem codes this rule applies to
            (empty → all subsystems).
    """

    rule_id: str
    dimension: RiskDimension
    check_description: str
    trigger_condition: str
    default_probability: int  # 1-5
    default_impact: int  # 1-5
    keywords: list[str] = field(default_factory=list)
    applicable_subsystems: list[str] = field(default_factory=list)


@dataclass
class Risk:
    """A concrete risk finding produced by a rule evaluation.

    Attributes:
        risk_id: Unique identifier for this finding (e.g. ``"RISK-001"``).
        rule_id: The :class:`RiskRule` that generated this finding.
        dimension: Inherited risk dimension.
        severity: Computed severity bucket.
        description: Detailed narrative of the risk.
        source_reference: Spec clause / page that triggered the finding.
        probability: Assessed probability (1–5).
        impact: Assessed impact (1–5).
        score: ``probability × impact`` composite score.
        affected_subsystems: Subsystems impacted by this risk.
        mitigation: Proposed mitigation action (populated during review).
        owner: Person or team responsible for the mitigation.
        spec_document_id: The ``document_id`` of the originating spec.
    """

    risk_id: str
    rule_id: str
    dimension: RiskDimension
    severity: RiskSeverity
    description: str
    source_reference: str
    probability: int
    impact: int
    score: int
    affected_subsystems: list[str] = field(default_factory=list)
    mitigation: str = ""
    owner: str = ""
    spec_document_id: str = ""


@dataclass
class RiskRegister:
    """Aggregated risk register for an entire RFQ analysis run.

    Collects all :class:`Risk` entries across multiple specification
    documents and provides query, statistics, and export helpers.

    Attributes:
        project_name: Human-readable project / RFQ name.
        analysis_date: ISO-8601 date string of the analysis run.
        spec_documents_analyzed: List of ``document_id`` values processed.
        risks: All risk findings collected during the analysis.
    """

    project_name: str
    analysis_date: str
    spec_documents_analyzed: list[str] = field(default_factory=list)
    risks: list[Risk] = field(default_factory=list)

    # -- Mutation -------------------------------------------------------

    def add_risk(self, risk: Risk) -> None:
        """Append a risk to the register.

        Args:
            risk: The :class:`Risk` instance to add.
        """
        self.risks.append(risk)

    # -- Query helpers --------------------------------------------------

    def get_risks_by_severity(self, severity: RiskSeverity) -> list[Risk]:
        """Return all risks matching the given *severity*.

        Args:
            severity: The :class:`RiskSeverity` level to filter on.

        Returns:
            A list of matching :class:`Risk` entries (may be empty).
        """
        return [r for r in self.risks if r.severity == severity]

    def get_risks_by_dimension(self, dimension: RiskDimension) -> list[Risk]:
        """Return all risks matching the given *dimension*.

        Args:
            dimension: The :class:`RiskDimension` to filter on.

        Returns:
            A list of matching :class:`Risk` entries (may be empty).
        """
        return [r for r in self.risks if r.dimension == dimension]

    # -- Statistics -----------------------------------------------------

    def get_summary_stats(self) -> dict:
        """Compute summary counts grouped by severity and dimension.

        Returns:
            A dictionary with two sub-dicts::

                {
                    "total": int,
                    "by_severity": {"CRITICAL": int, …},
                    "by_dimension": {"D1_STANDARDS_COMPLIANCE": int, …},
                }
        """
        by_severity: dict[str, int] = {s.value: 0 for s in RiskSeverity}
        by_dimension: dict[str, int] = {d.value: 0 for d in RiskDimension}

        for risk in self.risks:
            by_severity[risk.severity.value] += 1
            by_dimension[risk.dimension.value] += 1

        return {
            "total": len(self.risks),
            "by_severity": by_severity,
            "by_dimension": by_dimension,
        }

    # -- Export: CSV -----------------------------------------------------

    _CSV_HEADER: list[str] = field(
        init=False,
        repr=False,
        default_factory=lambda: [
            "risk_id",
            "rule_id",
            "dimension",
            "severity",
            "description",
            "source_reference",
            "probability",
            "impact",
            "score",
            "affected_subsystems",
            "mitigation",
            "owner",
            "spec_document_id",
        ],
    )

    def to_csv_rows(self) -> list[list[str]]:
        """Serialise the register to a list of CSV-ready rows.

        The first row is the header.  Subsequent rows contain one risk
        each, with list fields joined by ``"; "``.

        Returns:
            A list of string lists suitable for ``csv.writer.writerows``.
        """
        rows: list[list[str]] = [list(self._CSV_HEADER)]
        for r in self.risks:
            rows.append([
                r.risk_id,
                r.rule_id,
                r.dimension.value,
                r.severity.value,
                r.description,
                r.source_reference,
                str(r.probability),
                str(r.impact),
                str(r.score),
                "; ".join(r.affected_subsystems),
                r.mitigation,
                r.owner,
                r.spec_document_id,
            ])
        return rows

    # -- Export: Markdown ------------------------------------------------

    _SEVERITY_EMOJI: dict[str, str] = field(
        init=False,
        repr=False,
        default_factory=lambda: {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        },
    )

    def to_markdown(self) -> str:
        """Render the full risk register as a formatted Markdown string.

        Includes:
        - A header block with project metadata.
        - A summary statistics section.
        - A detailed risk table with severity emoji indicators.

        Returns:
            A complete Markdown document as a single string.
        """
        lines: list[str] = []

        # -- Header ----------------------------------------------------
        lines.append(f"# Risk Register — {self.project_name}")
        lines.append("")
        lines.append(f"**Analysis Date:** {self.analysis_date}  ")
        lines.append(
            f"**Documents Analyzed:** {', '.join(self.spec_documents_analyzed) or '—'}"
        )
        lines.append("")

        # -- Summary ----------------------------------------------------
        stats = self.get_summary_stats()
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Count |")
        lines.append("|--------|------:|")
        lines.append(f"| **Total Risks** | {stats['total']} |")
        for sev in RiskSeverity:
            emoji = self._SEVERITY_EMOJI.get(sev.value, "")
            count = stats["by_severity"][sev.value]
            lines.append(f"| {emoji} {sev.value} | {count} |")
        lines.append("")

        lines.append("### By Dimension")
        lines.append("")
        lines.append("| Dimension | Count |")
        lines.append("|-----------|------:|")
        for dim in RiskDimension:
            count = stats["by_dimension"][dim.value]
            lines.append(f"| {dim.value} | {count} |")
        lines.append("")

        # -- Detail table -----------------------------------------------
        if not self.risks:
            lines.append("_No risks identified._")
            return "\n".join(lines)

        lines.append("## Risk Detail")
        lines.append("")
        lines.append(
            "| # | Severity | Dimension | P | I | Score "
            "| Description | Source | Subsystems | Mitigation |"
        )
        lines.append(
            "|---|----------|-----------|---|---|------"
            "|-------------|--------|------------|------------|"
        )

        for r in self.risks:
            emoji = self._SEVERITY_EMOJI.get(r.severity.value, "")
            subsystems = (
                ", ".join(r.affected_subsystems)
                if r.affected_subsystems
                else "—"
            )
            mitigation = r.mitigation if r.mitigation else "—"
            # Escape pipe characters inside cell content
            desc = r.description.replace("|", "\\|")
            source = r.source_reference.replace("|", "\\|")
            mitigation_safe = mitigation.replace("|", "\\|")

            lines.append(
                f"| {r.risk_id} "
                f"| {emoji} {r.severity.value} "
                f"| {r.dimension.value} "
                f"| {r.probability} "
                f"| {r.impact} "
                f"| {r.score} "
                f"| {desc} "
                f"| {source} "
                f"| {subsystems} "
                f"| {mitigation_safe} |"
            )

        lines.append("")
        lines.append("---")
        lines.append(
            f"_Generated by RFQ Bid Risk Identification Agent v1.0.0 "
            f"on {self.analysis_date}_"
        )
        return "\n".join(lines)


# ──────────────────────────────────────────────
#  Project Context
# ──────────────────────────────────────────────

@dataclass
class ProjectContext:
    """Aggregated project-level context consumed by the risk engine.

    Collects outputs from the broader RFQ preparation workflow (MR
    cross-reference, BOM extraction, TBE criteria, etc.) so that
    risk rules can correlate spec requirements against actual
    project deliverables.

    Attributes:
        rfq_package_path: Root path of the RFQ preparation workspace.
        mr_saes_standards: Map of SAES/SAMSS standard numbers to their
            cross-reference status (e.g. ``"VERIFIED"``, ``"MISSING"``).
        mr_drawings: Map of drawing numbers to their cross-reference
            status.
        bom_items: List of BOM line-item dicts extracted from the MR /
            equipment schedules.
        checklist_items: Per-subsystem lists of checklist check items.
        tbe_criteria: List of Technical Bid Evaluation criterion dicts.
        deviation_clarifications: List of deviation / clarification
            request dicts.
        scope_of_supply: List of scope-of-supply line-item dicts.
    """

    rfq_package_path: Path
    mr_saes_standards: dict[str, str] = field(default_factory=dict)
    mr_drawings: dict[str, str] = field(default_factory=dict)
    bom_items: list[dict] = field(default_factory=list)
    checklist_items: dict[str, list[str]] = field(default_factory=dict)
    tbe_criteria: list[dict] = field(default_factory=list)
    deviation_clarifications: list[dict] = field(default_factory=list)
    scope_of_supply: list[dict] = field(default_factory=list)
