"""PDF Specification Extractor for Telecom & Security System RFQ Documents.

This module extracts structured data from telecom and security
specification PDFs using PyMuPDF (fitz).  All extraction is purely
rule-based — no LLM or external API calls are needed.

Typical usage::

    from pathlib import Path
    from rfq_risk_agent.spec_extractor import extract_spec

    doc = extract_spec(Path("2525-8540-80-E050-0001.pdf"))
    print(doc.document_id, doc.title, len(doc.shall_statements))

Dependencies (stdlib + PyMuPDF only):
    fitz (PyMuPDF ≥ 1.27), re, json, pathlib, dataclasses, sys
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from rfq_risk_agent.models import (
    ObligationType,
    PageClassification,
    ShallStatement,
    SpecDocument,
    SpecSection,
)

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Regex patterns — compiled once at import time for performance.
_RE_DOC_ID_1 = re.compile(r"(\d{4}-8540-\d{2}-[A-Z]\d{3}-\d{4})")
_RE_DOC_ID_2 = re.compile(r"(\d{4}-\d{4}-[A-Z]{2}-[A-Z]\d{3}-\d{4})")
_RE_REVISION_1 = re.compile(r"Rev\.?\s*([A-Z]\d*\.?\d*)", re.IGNORECASE)
_RE_REVISION_2 = re.compile(r"Revision\s*:?\s*([A-Z]\d*)", re.IGNORECASE)

_RE_SAES = re.compile(r"SAES-[A-Z]-\d{3}")
_RE_SAMSS = re.compile(r"\d{2}-SAMSS-\d{3}")
_RE_IEC = re.compile(r"IEC\s+\d{4,5}(?:-\d+-\d+)?")
_RE_IEEE = re.compile(r"IEEE\s+802\.\d+[a-z]*")
_RE_NFPA = re.compile(r"NFPA\s+\d+")
_RE_ANSI_NEMA = re.compile(r"ANSI/NEMA\s+[A-Z]+-\d+")
_RE_SEC = re.compile(r"SEC-\d{2}")

_RE_DRAWING_1 = re.compile(r"(\d{4}-8540-\d{2}-[A-Z]\d{3}-\d{4})")
_RE_DRAWING_2 = re.compile(r"(2525-8540-80-R591-\d{4})")
_RE_DRAWING_3 = re.compile(r"(2270-8540-\d{2}-O002-\d{4})")

_RE_CLAUSE_REF = re.compile(
    r"^(?:"
    r"(?:i{1,3}|iv|vi{0,3}|ix|x)\."  # Roman numerals (i. ii. iii. iv. ...)
    r"|"
    r"\d+(?:\.\d+)*\.?"  # Decimal numbering (4.1, 4.2.3, etc.)
    r")\s+",
    re.IGNORECASE,
)

_RE_SHALL = re.compile(r"\b(?:shall|will|must)\b", re.IGNORECASE)

# Sentence-boundary split: period followed by whitespace and an uppercase
# letter (or end-of-string).  Avoids splitting on abbreviations like "Rev."
_RE_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\d])")

# Equipment vocabulary for telecom/security domains.
EQUIPMENT_VOCAB: list[str] = [
    "card reader",
    "electromagnetic door lock",
    "magnetic door contact",
    "break glass",
    "exit push button",
    "CCTV camera",
    "PTZ camera",
    "dome camera",
    "thermal camera",
    "NVR",
    "video server",
    "access controller",
    "door controller",
    "LDC",
    "fiber optic cable",
    "CAT6",
    "patch panel",
    "cabinet",
    "rack",
    "enclosure",
    "junction box",
    "UPS",
    "power supply",
    "battery",
    "workstation",
    "monitor",
    "display",
    "alarm panel",
    "fire alarm",
    "FACP",
    "anti-drone",
    "fence sensor",
    "microwave barrier",
    "muster station",
    "EPOB",
    "roll call",
    "loudspeaker",
    "speaker",
    "amplifier",
    "beacon",
    "access point",
    "switch",
    "router",
    "firewall",
    "telephone",
    "IP phone",
    "handset",
    "antenna",
    "tower",
    "BDA",
    "repeater",
    "conduit",
    "cable tray",
    "manhole",
    "handhole",
]

# Pre-compiled case-insensitive patterns for each equipment term.
_EQUIPMENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (term, re.compile(re.escape(term), re.IGNORECASE)) for term in EQUIPMENT_VOCAB
]


# ---------------------------------------------------------------------------
# Page classification keyword sets (lowercased for matching)
# ---------------------------------------------------------------------------

_PAGE_CLASSIFIERS: list[tuple[PageClassification, list[str]]] = [
    (
        PageClassification.TOC,
        ["table of contents"],
    ),
    (
        PageClassification.REFERENCES,
        ["references", "applicable standards", "referenced documents"],
    ),
    (
        PageClassification.SCOPE_OF_WORK,
        ["scope of work", "general requirements", "scope location", "scope and purpose"],
    ),
    (
        PageClassification.SYSTEM_DESCRIPTION,
        ["system description", "system architecture", "system overview"],
    ),
    (
        PageClassification.INSTALLATION_COMMISSIONING,
        [
            "installation",
            "commissioning",
            "mechanical completion",
            "construction",
        ],
    ),
    (
        PageClassification.TESTING,
        ["testing", "acceptance test", "factory acceptance", "site acceptance"],
    ),
    (
        PageClassification.SPARES_TRAINING,
        ["spare", "training", "familiarization"],
    ),
    (
        PageClassification.APPENDIX,
        ["appendix", "attachment", "annex"],
    ),
]


# ========================================================================
#  Public API
# ========================================================================


def extract_spec(pdf_path: Path) -> SpecDocument:
    """Extract structured specification data from a single PDF.

    This is the main entry point.  It opens *pdf_path* with PyMuPDF,
    delegates to private helpers for each extraction task, and returns
    a fully-populated :class:`SpecDocument`.

    Args:
        pdf_path: Filesystem path to the source PDF file.

    Returns:
        A :class:`SpecDocument` populated with metadata, sections,
        obligation statements, standards, drawings, and equipment.

    Raises:
        FileNotFoundError: If *pdf_path* does not exist.
        RuntimeError: If PyMuPDF cannot open the file.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        raise RuntimeError(f"PyMuPDF failed to open {pdf_path}: {exc}") from exc

    full_text = _extract_text(doc)
    document_id, title, revision = _extract_metadata(full_text, doc)
    referenced_standards = _extract_referenced_standards(full_text)
    referenced_drawings = _extract_referenced_drawings(full_text)
    sections = _classify_pages(doc)
    shall_statements = _extract_shall_statements(full_text, doc)
    equipment_mentions = _extract_equipment_mentions(full_text)

    spec = SpecDocument(
        document_id=document_id,
        title=title,
        revision=revision,
        total_pages=len(doc),
        file_path=pdf_path.resolve(),
        full_text=full_text,
        sections=sections,
        shall_statements=shall_statements,
        referenced_standards=referenced_standards,
        referenced_drawings=referenced_drawings,
        equipment_mentions=equipment_mentions,
    )

    doc.close()
    return spec


def extract_specs_batch(pdf_dir: Path) -> list[SpecDocument]:
    """Batch-process every PDF in *pdf_dir* and return results.

    Non-PDF files are silently skipped.  Errors on individual files
    are logged but do not halt the batch.

    Args:
        pdf_dir: Directory containing one or more PDF files.

    Returns:
        List of successfully extracted :class:`SpecDocument` objects.
    """
    pdf_dir = Path(pdf_dir)
    if not pdf_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {pdf_dir}")

    results: list[SpecDocument] = []
    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        try:
            logger.info("Processing %s …", pdf_file.name)
            results.append(extract_spec(pdf_file))
        except Exception:
            logger.exception("Failed to extract %s — skipping.", pdf_file.name)

    logger.info(
        "Batch complete: %d/%d PDFs extracted.",
        len(results),
        len(list(pdf_dir.glob("*.pdf"))),
    )
    return results


# ========================================================================
#  Private helpers
# ========================================================================


def _extract_text(doc: fitz.Document) -> str:
    """Extract and clean full text from every page of *doc*.

    Applies light normalisation: collapses runs of whitespace, strips
    common headers/footers (page numbers, document-number watermarks),
    and removes control characters.

    Args:
        doc: An open PyMuPDF Document.

    Returns:
        Cleaned, concatenated text of all pages.
    """
    pages: list[str] = []

    for page_num in range(len(doc)):
        try:
            page = doc[page_num]
            text = page.get_text("text") or ""
        except Exception:
            logger.warning("Could not read page %d — skipping.", page_num + 1)
            continue

        # Remove common header/footer patterns.
        text = _strip_headers_footers(text, page_num + 1)
        # Collapse multiple blank lines to a single newline.
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Collapse runs of spaces (but preserve newlines).
        text = re.sub(r"[ \t]{2,}", " ", text)

        pages.append(text.strip())

    return "\n\n".join(pages)


def _strip_headers_footers(text: str, page_num: int) -> str:
    """Remove repetitive header/footer lines from a single page's text.

    Targets standalone page-number lines and document-number watermarks
    that PyMuPDF extracts as separate text blocks.
    """
    lines = text.split("\n")
    cleaned: list[str] = []

    for line in lines:
        stripped = line.strip()
        # Skip standalone page numbers ("1", "Page 2 of 45", etc.)
        if re.match(r"^(?:Page\s+)?\d{1,3}(?:\s+of\s+\d{1,3})?$", stripped, re.IGNORECASE):
            continue
        # Skip lines that are ONLY a document-number watermark.
        if _RE_DOC_ID_1.fullmatch(stripped) or _RE_DOC_ID_2.fullmatch(stripped):
            continue
        cleaned.append(line)

    return "\n".join(cleaned)


def _extract_metadata(
    full_text: str,
    doc: fitz.Document,
) -> tuple[str, str, str]:
    """Extract document ID, title, and revision from the first few pages.

    Strategy:
        1. Build a search corpus from pages 1–3 (title-page vicinity).
        2. Match document-ID patterns.  Prefer the *first* match.
        3. Match revision patterns.
        4. Attempt to extract a title — look for text immediately
           following the document ID, or fall back to the PDF metadata
           ``/Title`` entry.

    Args:
        full_text: Cleaned full text of the document.
        doc: An open PyMuPDF Document (used for page-level access).

    Returns:
        Tuple of ``(document_id, title, revision)``.
    """
    # Build a focused search window from the first 3 pages.
    header_pages: list[str] = []
    for i in range(min(3, len(doc))):
        try:
            header_pages.append(doc[i].get_text("text") or "")
        except Exception:
            pass
    header_text = "\n".join(header_pages)

    # --- Document ID ---
    document_id = ""
    for pattern in (_RE_DOC_ID_1, _RE_DOC_ID_2):
        match = pattern.search(header_text)
        if match:
            document_id = match.group(1)
            break

    # If not found in first 3 pages, try full text.
    if not document_id:
        for pattern in (_RE_DOC_ID_1, _RE_DOC_ID_2):
            match = pattern.search(full_text)
            if match:
                document_id = match.group(1)
                break

    # --- Revision ---
    revision = ""
    for pattern in (_RE_REVISION_1, _RE_REVISION_2):
        match = pattern.search(header_text)
        if match:
            revision = match.group(1)
            break

    if not revision:
        for pattern in (_RE_REVISION_1, _RE_REVISION_2):
            match = pattern.search(full_text)
            if match:
                revision = match.group(1)
                break

    # --- Title ---
    title = _extract_title(header_text, document_id, doc)

    return document_id, title, revision


def _extract_title(
    header_text: str,
    document_id: str,
    doc: fitz.Document,
) -> str:
    """Best-effort title extraction from the title-page region.

    Heuristics (tried in order):
        1. If a document ID was found, take the next non-blank line(s)
           after it that look like a title (mixed-case or ALL-CAPS,
           length 10–200 chars).
        2. Check PyMuPDF's metadata ``/Title``.
        3. Return ``"UNTITLED"`` as a fallback.
    """
    # Strategy 1 — text after the document ID on the title page.
    if document_id:
        # Find the doc-ID line and grab subsequent lines.
        idx = header_text.find(document_id)
        if idx != -1:
            after = header_text[idx + len(document_id) :]
            for line in after.split("\n"):
                candidate = line.strip()
                if 10 <= len(candidate) <= 200 and not _is_boilerplate(candidate):
                    return candidate

    # Strategy 2 — look for prominent ALL-CAPS lines on page 1.
    first_page = ""
    if len(doc) > 0:
        try:
            first_page = doc[0].get_text("text") or ""
        except Exception:
            pass

    for line in first_page.split("\n"):
        candidate = line.strip()
        if (
            len(candidate) >= 15
            and candidate == candidate.upper()
            and not candidate.isdigit()
            and not _is_boilerplate(candidate)
        ):
            return candidate

    # Strategy 3 — PyMuPDF embedded metadata.
    meta_title = doc.metadata.get("title", "").strip() if doc.metadata else ""
    if meta_title:
        return meta_title

    return "UNTITLED"


def _is_boilerplate(text: str) -> bool:
    """Return True if *text* looks like a boilerplate header/footer."""
    lower = text.lower()
    boilerplate_markers = [
        "confidential",
        "proprietary",
        "page",
        "rev.",
        "revision",
        "date",
        "approved",
        "checked",
        "issued",
    ]
    return any(marker in lower for marker in boilerplate_markers)


def _extract_referenced_standards(full_text: str) -> list[str]:
    """Extract unique referenced standards sorted alphabetically.

    Matches seven families of industry/corporate standards commonly
    cited in Saudi Aramco telecom and security specifications.

    Args:
        full_text: Cleaned full document text.

    Returns:
        Sorted, deduplicated list of standard identifiers.
    """
    standards: set[str] = set()
    for pattern in (
        _RE_SAES,
        _RE_SAMSS,
        _RE_IEC,
        _RE_IEEE,
        _RE_NFPA,
        _RE_ANSI_NEMA,
        _RE_SEC,
    ):
        standards.update(pattern.findall(full_text))

    return sorted(standards)


def _extract_referenced_drawings(full_text: str) -> list[str]:
    """Extract unique drawing numbers sorted alphabetically.

    Args:
        full_text: Cleaned full document text.

    Returns:
        Sorted, deduplicated list of drawing identifiers.
    """
    drawings: set[str] = set()
    for pattern in (_RE_DRAWING_1, _RE_DRAWING_2, _RE_DRAWING_3):
        drawings.update(pattern.findall(full_text))

    return sorted(drawings)


def _classify_pages(doc: fitz.Document) -> list[SpecSection]:
    """Classify every page and group consecutive like-classified pages.

    Each page is assigned the *best-matching* :class:`PageClassification`
    based on keyword hits.  Consecutive pages sharing the same class
    are merged into a single :class:`SpecSection`.

    Args:
        doc: An open PyMuPDF Document.

    Returns:
        List of :class:`SpecSection` objects covering the full document.
    """
    page_classes: list[PageClassification] = []

    for page_idx in range(len(doc)):
        try:
            page_text = (doc[page_idx].get_text("text") or "").lower()
        except Exception:
            page_classes.append(PageClassification.UNKNOWN)
            continue

        classification = _classify_single_page(page_text, page_idx)
        page_classes.append(classification)

    # Merge consecutive pages with the same classification.
    return _merge_page_runs(page_classes, doc)


def _classify_single_page(page_text_lower: str, page_idx: int) -> PageClassification:
    """Classify a single page based on keyword density.

    Args:
        page_text_lower: Lowered full text of the page.
        page_idx: Zero-based page index (page 0 → likely COVER).

    Returns:
        Best-fit :class:`PageClassification`.
    """
    # Page 0 is almost always the cover sheet.
    if page_idx == 0:
        return PageClassification.COVER

    # TOC detection — dotted leader lines are a strong signal.
    dotted_leaders = len(re.findall(r"\.{4,}", page_text_lower))
    if "table of contents" in page_text_lower or dotted_leaders >= 5:
        return PageClassification.TOC

    # Score each classification by keyword hits.
    best_class = PageClassification.UNKNOWN
    best_score = 0

    for classification, keywords in _PAGE_CLASSIFIERS:
        score = sum(1 for kw in keywords if kw in page_text_lower)
        if score > best_score:
            best_score = score
            best_class = classification

    return best_class


def _merge_page_runs(
    page_classes: list[PageClassification],
    doc: fitz.Document
) -> list[SpecSection]:
    """Merge consecutive pages of the same class into SpecSection spans.

    Args:
        page_classes: Per-page classification list (0-indexed internally,
            but SpecSection uses 1-based page numbers).
        doc: Open PyMuPDF Document (to extract text).

    Returns:
        Merged list of :class:`SpecSection` objects.
    """
    if not page_classes:
        return []

    sections: list[SpecSection] = []
    current_class = page_classes[0]
    start_page = 1  # 1-based

    for i in range(1, len(page_classes)):
        if page_classes[i] != current_class:
            text_parts = []
            for p in range(start_page - 1, i):
                try:
                    text_parts.append(doc[p].get_text("text") or "")
                except Exception:
                    pass
            sections.append(
                SpecSection(
                    section_type=current_class,
                    page_range=(start_page, i),
                    text="\n".join(text_parts),
                    title=current_class.value.replace("_", " ").title(),
                )
            )
            current_class = page_classes[i]
            start_page = i + 1  # 1-based

    # Close the final run.
    text_parts = []
    for p in range(start_page - 1, len(page_classes)):
        try:
            text_parts.append(doc[p].get_text("text") or "")
        except Exception:
            pass
    sections.append(
        SpecSection(
            section_type=current_class,
            page_range=(start_page, len(page_classes)),
            text="\n".join(text_parts),
            title=current_class.value.replace("_", " ").title(),
        )
    )

    return sections


def _extract_shall_statements(
    full_text: str,
    doc: fitz.Document,
) -> list[ShallStatement]:
    """Extract obligation sentences containing SHALL, WILL, or MUST.

    Each extracted sentence is classified by obligation type and, where
    possible, tagged with a clause reference and page number.

    Args:
        full_text: Cleaned full document text.
        doc: Open PyMuPDF Document (for page-level location).

    Returns:
        List of :class:`ShallStatement` objects.
    """
    # Pre-extract per-page text for page-number look-up.
    page_texts: list[str] = []
    for page_idx in range(len(doc)):
        try:
            page_texts.append(doc[page_idx].get_text("text") or "")
        except Exception:
            page_texts.append("")

    # Split into sentences.
    sentences = _RE_SENTENCE_SPLIT.split(full_text)

    statements: list[ShallStatement] = []
    seen: set[str] = set()  # Deduplicate by normalised text.

    for raw in sentences:
        sentence = raw.strip()
        if not sentence or len(sentence) < 15:
            continue

        if not _RE_SHALL.search(sentence):
            continue

        # Normalise for deduplication.
        normalised = re.sub(r"\s+", " ", sentence.lower())
        if normalised in seen:
            continue
        seen.add(normalised)

        obligation = _classify_obligation(sentence)
        page_number = _locate_page(sentence, page_texts)
        clause_ref = _extract_clause_ref(sentence)

        statements.append(
            ShallStatement(
                text=sentence,
                obligation_type=obligation,
                page=page_number,
                clause=clause_ref,
            )
        )

    return statements


def _classify_obligation(sentence: str) -> ObligationType:
    """Classify an obligation sentence into a domain category.

    Uses keyword matching against the lowered sentence text.  The
    first matching category wins (evaluated in a deliberate priority
    order so that more specific categories are checked first).

    Args:
        sentence: The raw obligation sentence.

    Returns:
        The best-fit :class:`ObligationType`.
    """
    lower = sentence.lower()

    classification_rules: list[tuple[ObligationType, list[str]]] = [
        (
            ObligationType.TESTING,
            ["test", "commission", "inspect", "fat", "sat", "calibrat"],
        ),
        (
            ObligationType.DOCUMENTATION,
            ["document", "submit", "drawing", "manual", "report", "certificate"],
        ),
        (
            ObligationType.INTERFACE,
            ["interface", "integrat", "coordinat", "connect", "communicat"],
        ),
        (
            ObligationType.DESIGN,
            ["design", "engineer", "calculate", "sizing", "study"],
        ),
        (
            ObligationType.SUPPLY,
            ["supply", "provide", "procure", "deliver", "furnish"],
        ),
    ]

    for obligation_type, keywords in classification_rules:
        if any(kw in lower for kw in keywords):
            return obligation_type

    return ObligationType.DESIGN


def _locate_page(sentence: str, page_texts: list[str]) -> int:
    """Find the 1-based page number where *sentence* appears.

    Uses a truncated search key (first 60 chars) to avoid issues with
    sentences that span page boundaries.

    Args:
        sentence: The sentence to locate.
        page_texts: Raw per-page text (0-indexed).

    Returns:
        1-based page number, or 0 if not found.
    """
    # Use a meaningful snippet for matching.
    search_key = sentence[:80].strip()
    # Normalise whitespace in both the key and targets.
    normalised_key = re.sub(r"\s+", " ", search_key)

    for idx, pt in enumerate(page_texts):
        normalised_page = re.sub(r"\s+", " ", pt)
        if normalised_key in normalised_page:
            return idx + 1

    # Fallback: try a shorter fragment.
    short_key = re.sub(r"\s+", " ", sentence[:40].strip())
    for idx, pt in enumerate(page_texts):
        normalised_page = re.sub(r"\s+", " ", pt)
        if short_key in normalised_page:
            return idx + 1

    return 0


def _extract_clause_ref(sentence: str) -> str:
    """Extract a leading clause reference from *sentence* if present.

    Recognises:
        - Roman numerals: ``i.``, ``ii.``, ``iii.``, ``iv.`` …
        - Decimal numbering: ``4.1``, ``4.2.3``, ``10.1.2`` …

    Args:
        sentence: The raw obligation sentence.

    Returns:
        The matched clause reference string, or ``""`` if none found.
    """
    match = _RE_CLAUSE_REF.match(sentence)
    if match:
        return match.group(0).strip().rstrip(".")

    return ""


def _extract_equipment_mentions(full_text: str) -> list[str]:
    """Extract equipment terms present in the document text.

    Matches against a curated telecom/security equipment vocabulary
    using case-insensitive search.  Returns deduplicated results in
    the canonical casing defined in :data:`EQUIPMENT_VOCAB`.

    Args:
        full_text: Cleaned full document text.

    Returns:
        Sorted, unique list of equipment terms found.
    """
    found: list[str] = []
    for canonical_term, pattern in _EQUIPMENT_PATTERNS:
        if pattern.search(full_text):
            found.append(canonical_term)

    return sorted(set(found))


# ========================================================================
#  CLI entry point
# ========================================================================


def _print_summary(spec: SpecDocument) -> None:
    """Pretty-print a concise extraction summary to stdout."""
    divider = "=" * 68
    print(divider)
    print("  SPEC EXTRACTOR — Extraction Summary")
    print(divider)
    print(f"  Document ID : {spec.document_id or '(not found)'}")
    print(f"  Title       : {spec.title or '(not found)'}")
    print(f"  Revision    : {spec.revision or '(not found)'}")
    print(f"  Total pages : {spec.total_pages}")
    print(f"  Source      : {spec.source_path}")
    print(divider)
    print(f"  Standards referenced : {len(spec.referenced_standards)}")
    print(f"  Drawings referenced  : {len(spec.referenced_drawings)}")
    print(f"  Shall statements     : {len(spec.shall_statements)}")
    print(f"  Equipment mentions   : {len(spec.equipment_mentions)}")
    print(divider)

    if spec.sections:
        print("\n  SECTIONS:")
        for sec in spec.sections:
            print(
                f"    pp. {sec.start_page:>3}–{sec.end_page:<3}  "
                f"{sec.classification.value}"
            )

    if spec.referenced_standards:
        print("\n  REFERENCED STANDARDS:")
        for std in spec.referenced_standards[:15]:
            print(f"    • {std}")
        if len(spec.referenced_standards) > 15:
            print(f"    … and {len(spec.referenced_standards) - 15} more")

    if spec.equipment_mentions:
        print("\n  EQUIPMENT FOUND:")
        for eq in spec.equipment_mentions:
            print(f"    • {eq}")

    if spec.shall_statements:
        preview_count = min(5, len(spec.shall_statements))
        print(f"\n  FIRST {preview_count} SHALL STATEMENTS:")
        for i, stmt in enumerate(spec.shall_statements[:preview_count], 1):
            # Truncate long sentences for readability.
            text_preview = stmt.text[:120] + ("…" if len(stmt.text) > 120 else "")
            print(f"    {i}. [{stmt.obligation_type.value}] (p.{stmt.page_number})")
            if stmt.clause_ref:
                print(f"       Clause: {stmt.clause_ref}")
            print(f"       {text_preview}")

    print()


def main() -> None:
    """CLI entry point for standalone testing."""
    if len(sys.argv) < 2:
        print("Usage: python -m rfq_risk_agent.spec_extractor <pdf_path>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    print(f"\nExtracting spec from: {pdf_path}\n")

    try:
        spec = extract_spec(pdf_path)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    _print_summary(spec)


if __name__ == "__main__":
    main()
