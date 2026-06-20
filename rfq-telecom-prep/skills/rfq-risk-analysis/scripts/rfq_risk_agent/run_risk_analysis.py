"""
CLI Entry Point for the RFQ Risk Agent.

Usage:
    python -m rfq_risk_agent.run_risk_analysis <pdf_dir_or_file> [--output-dir <dir>]
"""

import argparse
import datetime
import logging
from pathlib import Path

from rfq_risk_agent.models import RiskRegister
from rfq_risk_agent.rfq_context_loader import load_project_context
from rfq_risk_agent.risk_analyzer import RiskAnalyzer
from rfq_risk_agent.spec_extractor import extract_spec, extract_specs_batch

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="RFQ Bid Risk Identification Agent")
    parser.add_argument("input_path", type=Path, help="Path to specification PDF or directory of PDFs")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("D:/Projects/AGSA/TELE/RFQ_PACKAGE/Risk_Analysis"),
        help="Directory to save the risk register outputs",
    )
    parser.add_argument(
        "--rfq-dir",
        type=Path,
        default=Path("D:/Projects/AGSA/TELE/RFQ_PACKAGE"),
        help="Root directory of the RFQ package (for context loading)",
    )
    
    args = parser.parse_args()

    # 1. Load Context
    logger.info("Loading project context from %s...", args.rfq_dir)
    context = load_project_context(args.rfq_dir)
    
    # 2. Extract Specifications
    specs = []
    if args.input_path.is_file() and args.input_path.suffix.lower() == ".pdf":
        logger.info("Extracting single spec: %s", args.input_path.name)
        specs.append(extract_spec(args.input_path))
    elif args.input_path.is_dir():
        logger.info("Batch extracting specs from: %s", args.input_path)
        specs.extend(extract_specs_batch(args.input_path))
    else:
        logger.error("Input path must be a .pdf file or a directory containing PDFs.")
        return

    if not specs:
        logger.error("No valid specifications extracted. Exiting.")
        return

    # 3. Analyze Risks
    kb_path = Path(__file__).parent / "risk_knowledge_base.json"
    analyzer = RiskAnalyzer(kb_path)
    
    register = RiskRegister(
        project_name="Telecom & Security Systems RFQ",
        analysis_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        spec_documents_analyzed=[s.document_id or s.title for s in specs]
    )

    for spec in specs:
        logger.info("Analyzing %s...", spec.document_id or spec.title)
        risks = analyzer.analyze(spec, context)
        for r in risks:
            register.add_risk(r)
            
    logger.info("Analysis complete. Identified %d total risks.", len(register.risks))

    # 4. Generate Outputs
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Markdown
    md_path = args.output_dir / "risk_register.md"
    md_path.write_text(register.to_markdown(), encoding="utf-8")
    logger.info("Saved Markdown register to %s", md_path)
    
    # CSV
    import csv
    csv_path = args.output_dir / "risk_register.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(register.to_csv_rows())
    logger.info("Saved CSV register to %s", csv_path)
    
    logger.info("Risk Analysis successfully completed.")


if __name__ == "__main__":
    main()
