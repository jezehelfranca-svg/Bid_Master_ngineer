---
name: RFQ Risk Analysis
description: Skill for running the automated RFQ Bid Risk Identification pipeline. Evaluates specification PDFs against the telecom/security knowledge base and generates risk registers.
---

# RFQ Risk Analysis

This skill provides instructions for operating the Python-based RFQ Bid Risk Identification Agent located in `C:\Users\jezeh\.gemini\config\plugins\rfq-telecom-prep\skills\rfq-risk-analysis\scripts\rfq_risk_agent`.

## Context

The pipeline extracts structured text from technical specification PDFs, classifies the text into functional sections (Scope of Work, Testing, etc.), extracts "shall" statements, and evaluates everything against a predefined Knowledge Base of 50+ industry rules (based on SAES standards, checklists, and TBE criteria).

## Usage Instructions

When asked to evaluate a specification PDF for risks, follow these steps:

1. **Verify the Path:** Ensure the provided path to the PDF is valid.
2. **Execute the Pipeline:**
   Use the `run_command` tool to execute the CLI script:
   ```powershell
   $env:PYTHONPATH = "C:\Users\jezeh\.gemini\config\plugins\rfq-telecom-prep\skills\rfq-risk-analysis\scripts"
   python -m rfq_risk_agent.run_risk_analysis <absolute_path_to_pdf> --rfq-dir D:\Projects\AGSA\TELE\RFQ_PACKAGE --output-dir D:\Projects\AGSA\TELE\RFQ_PACKAGE\Risk_Analysis
   ```
3. **Review Outputs:**
   The script outputs to `D:\Projects\AGSA\TELE\RFQ_PACKAGE\Risk_Analysis`.
   Use `view_file` to read the generated `risk_register.md`.
4. **Report to User:**
   Summarize the findings. Focus on `CRITICAL` and `HIGH` severity risks. Suggest Technical Queries or Deviations to mitigate the identified risks.
