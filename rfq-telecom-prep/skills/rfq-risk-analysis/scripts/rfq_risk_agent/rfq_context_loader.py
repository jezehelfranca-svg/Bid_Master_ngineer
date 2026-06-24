"""
RFQ Context Loader Module.

Loads and indexes existing RFQ package artifacts (MR, checklists, BOQ, TBE,
deviation list, scope of supply) to provide "ground truth" for risk
cross-referencing.
"""

import csv
import re
from pathlib import Path
from typing import Optional

from rfq_risk_agent.models import ProjectContext


def load_project_context(rfq_package_path: Path) -> ProjectContext:
    """Load all RFQ package artifacts into a ProjectContext object.

    Args:
        rfq_package_path: Path to the RFQ_PACKAGE directory.

    Returns:
        Populated ProjectContext with all indexed artifacts.
    """
    ctx = ProjectContext(rfq_package_path=rfq_package_path)

    # Load each component, tolerating missing files
    mr_path = rfq_package_path / "MR_Telecom_Security_System.md"
    if mr_path.exists():
        _load_mr_standards(mr_path, ctx)
        _load_mr_drawings(mr_path, ctx)
        _load_mr_bom(mr_path, ctx)

    boq_path = rfq_package_path / "Appendix_1_Scope_of_Supply_and_Service" / "BOQ_Telecom_Security.csv"
    if boq_path.exists():
        _load_boq(boq_path, ctx)

    checklist_dir = rfq_package_path / "Engineering_Checklists"
    if checklist_dir.exists():
        _load_checklists(checklist_dir, ctx)

    tbe_path = rfq_package_path / "KDA" / "TBE_Sheet.csv"
    if tbe_path.exists():
        _load_tbe(tbe_path, ctx)

    dcl_path = rfq_package_path / "Appendix_3_Deviation_and_Clarification" / "Deviation_Clarification_List.md"
    if dcl_path.exists():
        _load_deviations(dcl_path, ctx)

    sos_path = rfq_package_path / "Appendix_1_Scope_of_Supply_and_Service" / "Scope_of_Supply_Checklist.md"
    if sos_path.exists():
        _load_scope_of_supply(sos_path, ctx)

    return ctx


def _load_mr_standards(mr_path: Path, ctx: ProjectContext) -> None:
    """Extract SAES standards and their statuses from the MR document.

    Parses the markdown table in Section 7.1 to build a dict of
    standard_no -> status (Available / HOLD / Missing).
    """
    content = mr_path.read_text(encoding="utf-8", errors="replace")

    # Match table rows with standard numbers and statuses
    # Pattern: | SAES-X-NNN | Description | Status |
    pattern = re.compile(
        r'\|\s*(SAES-[A-Z]-\d{3})\s*\|[^|]+\|\s*(Available|HOLD\s*/?\s*Missing|HOLD|Missing)\s*\|',
        re.IGNORECASE
    )
    for match in pattern.finditer(content):
        standard = match.group(1).strip()
        status = match.group(2).strip()
        ctx.mr_saes_standards[standard] = status


def _load_mr_drawings(mr_path: Path, ctx: ProjectContext) -> None:
    """Extract drawing numbers and their statuses from the MR document.

    Parses the markdown tables in Sections 7.2.x to build a dict of
    drawing_no -> status.
    """
    content = mr_path.read_text(encoding="utf-8", errors="replace")

    # Match drawing table rows
    # Pattern: | 2270-8540-xx-Oxxx-xxxx-xxx | Title | Status |
    # or: | 2525-8540-80-R591-xxxx | Title | Status |
    pattern = re.compile(
        r'\|\s*(\d{4}-8540-\d{2}-[A-Z0-9]{1,4}-\d{4}(?:-\d{3})?)\s*\|[^|]+\|\s*(Available|HOLD\s*/?\s*Missing|HOLD|Missing)\s*\|',
        re.IGNORECASE
    )
    for match in pattern.finditer(content):
        drawing = match.group(1).strip()
        status = match.group(2).strip()
        ctx.mr_drawings[drawing] = status


def _load_mr_bom(mr_path: Path, ctx: ProjectContext) -> None:
    """Extract BOM line items from the MR document.

    Parses the markdown table in Section 6 to extract item descriptions,
    quantities, and units.
    """
    content = mr_path.read_text(encoding="utf-8", errors="replace")

    # Find BOM section (Section 6)
    bom_section = re.search(
        r'## 6\. BILL OF MATERIALS.*?\n(.*?)(?=\n## |\n---|\Z)',
        content,
        re.DOTALL
    )
    if not bom_section:
        return

    bom_text = bom_section.group(1)
    # Match table rows: | Ref | Description | Qty | Unit | Remarks |
    pattern = re.compile(
        r'\|\s*\*?\*?(\d[\d-]*)\*?\*?\s*\|\s*\*?\*?([^|]+?)\*?\*?\s*\|\s*(\d+)?\s*\|\s*([A-Z]+)?\s*\|[^|]*\|'
    )
    for match in pattern.finditer(bom_text):
        item = {
            "ref": match.group(1).strip(),
            "description": match.group(2).strip(),
            "quantity": int(match.group(3)) if match.group(3) else 0,
            "unit": match.group(4).strip() if match.group(4) else "",
        }
        ctx.bom_items.append(item)


def _load_boq(boq_path: Path, ctx: ProjectContext) -> None:
    """Load BOQ CSV into context (supplements MR BOM if available)."""
    try:
        with open(boq_path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only add if not already in bom_items from MR
                desc = row.get("DESCRIPTION", "").strip()
                if desc and not any(b["description"] == desc for b in ctx.bom_items):
                    ctx.bom_items.append({
                        "ref": row.get("ITEM NO", "").strip(),
                        "description": desc,
                        "quantity": int(row.get("TOTAL", 0) or 0),
                        "unit": row.get("UNIT", "").strip(),
                    })
    except Exception:
        pass  # Tolerate malformed CSV


def _load_checklists(checklist_dir: Path, ctx: ProjectContext) -> None:
    """Load engineering checklist items organized by subsystem.

    Parses markdown checklist files and extracts checkbox items.
    """
    for md_file in sorted(checklist_dir.glob("*_Checklist.md")):
        # Derive subsystem name from filename
        subsystem = md_file.stem.replace("_Checklist", "").replace("_", " ")
        items = []

        content = md_file.read_text(encoding="utf-8", errors="replace")
        # Match checklist items: * [ ] **Label:** Description
        pattern = re.compile(r'\*\s*\[\s*\]\s*\*\*([^*]+)\*\*:?\s*(.*)')
        for match in pattern.finditer(content):
            label = match.group(1).strip()
            description = match.group(2).strip()
            items.append(f"{label}: {description}")

        if items:
            ctx.checklist_items[subsystem] = items


def _load_tbe(tbe_path: Path, ctx: ProjectContext) -> None:
    """Load TBE evaluation criteria from CSV."""
    try:
        with open(tbe_path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                desc = row.get("DESCRIPTION", "").strip()
                req = row.get("PROJECT REQUIREMENT", "").strip()
                if desc and req:
                    ctx.tbe_criteria.append({
                        "item_no": row.get("TBE ITEM NO.", "").strip(),
                        "description": desc,
                        "requirement": req,
                    })
    except Exception:
        pass


def _load_deviations(dcl_path: Path, ctx: ProjectContext) -> None:
    """Load pre-populated deviation/clarification items from markdown."""
    content = dcl_path.read_text(encoding="utf-8", errors="replace")

    # Match deviation table rows
    pattern = re.compile(
        r'\|\s*\*?\*?(\d+)\*?\*?\s*\|\s*\*?\*?([^|]+?)\*?\*?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|',
    )
    for match in pattern.finditer(content):
        num = match.group(1).strip()
        subsystem = match.group(2).strip()
        reference = match.group(3).strip()
        clarification = match.group(4).strip()
        if subsystem and clarification:
            ctx.deviation_clarifications.append({
                "number": num,
                "subsystem": subsystem,
                "reference": reference,
                "clarification": clarification,
            })


def _load_scope_of_supply(sos_path: Path, ctx: ProjectContext) -> None:
    """Load scope of supply responsibility matrix from markdown."""
    content = sos_path.read_text(encoding="utf-8", errors="replace")

    # Match scope table rows
    pattern = re.compile(
        r'\|\s*[\d.]+\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|'
    )
    for match in pattern.finditer(content):
        item = match.group(1).strip()
        vendor = match.group(2).strip()
        contractor = match.group(3).strip()
        owner = match.group(4).strip()
        remarks = match.group(5).strip()
        if item and (vendor or contractor or owner):
            ctx.scope_of_supply.append({
                "item": item,
                "vendor": vendor,
                "contractor": contractor,
                "owner": owner,
                "remarks": remarks,
            })


def get_hold_missing_standards(ctx: ProjectContext) -> list[str]:
    """Return list of SAES standards marked as HOLD/Missing."""
    return [
        std for std, status in ctx.mr_saes_standards.items()
        if "HOLD" in status.upper() or "MISSING" in status.upper()
    ]


def get_hold_missing_drawings(ctx: ProjectContext) -> list[str]:
    """Return list of drawings marked as HOLD/Missing."""
    return [
        dwg for dwg, status in ctx.mr_drawings.items()
        if "HOLD" in status.upper() or "MISSING" in status.upper()
    ]


def get_available_drawings(ctx: ProjectContext) -> list[str]:
    """Return list of drawings marked as Available."""
    return [
        dwg for dwg, status in ctx.mr_drawings.items()
        if "available" in status.lower()
    ]


def summarize_context(ctx: ProjectContext) -> str:
    """Generate a human-readable summary of the loaded project context."""
    hold_standards = get_hold_missing_standards(ctx)
    hold_drawings = get_hold_missing_drawings(ctx)
    avail_drawings = get_available_drawings(ctx)

    lines = [
        "# Project Context Summary",
        f"**RFQ Package Path:** `{ctx.rfq_package_path}`",
        "",
        f"## SAES Standards: {len(ctx.mr_saes_standards)} total",
        f"- Available: {len(ctx.mr_saes_standards) - len(hold_standards)}",
        f"- HOLD/Missing: {len(hold_standards)}",
    ]
    if hold_standards:
        lines.append("- Missing: " + ", ".join(hold_standards))

    lines.extend([
        "",
        f"## Project Drawings: {len(ctx.mr_drawings)} total",
        f"- Available: {len(avail_drawings)}",
        f"- HOLD/Missing: {len(hold_drawings)}",
        "",
        f"## BOM Items: {len(ctx.bom_items)}",
        f"## Engineering Checklists: {len(ctx.checklist_items)} subsystems",
        f"## TBE Criteria: {len(ctx.tbe_criteria)} items",
        f"## Deviation Clarifications: {len(ctx.deviation_clarifications)} items",
        f"## Scope of Supply Items: {len(ctx.scope_of_supply)} items",
    ])

    return "\n".join(lines)
