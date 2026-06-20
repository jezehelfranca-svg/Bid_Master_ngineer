---
name: RFQ Telecom Workflow
description: Master SOP for preparing a complete Telecom & Security System RFQ package. Orchestrates the 9-phase workflow covering scaffolding, document template generation, extracting and indexing reference drawings, and final Material Requisition validation.
---

# RFQ Telecom Preparation Workflow

This skill is the master standard operating procedure (SOP) for the fq-engineer agent to prepare an industrial Telecommunication and Security Systems Request for Quotation (RFQ) package.

## The 9-Phase Workflow

### Phase 1: Scaffold — Folder Structure & Document Templates
Create the master RFQ package directory using the standard 5-Appendix hierarchy:
- MR_[System_Name].md — Main Material Requisition
- Appendix_1_Scope_of_Supply_and_Service/
- Appendix_2_Datasheet/
- Appendix_3_Deviation_and_Clarification/
- Appendix_4_Vendor_Data_Requirement/
- Appendix_5_Project_Specification_and_Drawing/
  - 1_Plot_Plan/, 2_Block_Diagram/, 3_Layout/, 4_Spec_Telecom_Security/, 5_General_Spec_Telecom_Security/, 6_Spec_Others/

### Phase 2: BOQ & Scope of Supply Templates
- Delegate to the fq-template-builder agent to create the BOQ_Telecom_Security.csv.
- Create a Scope_of_Supply_Checklist.md mapping responsibilities between Vendor, EPC Contractor, and Owner.

### Phase 3: Deviation & Clarification Framework
- Generate Deviation_Clarification_List.md.
- Pre-populate standard technical parameter defaults based on the ITB (e.g., Radio frequency bands, PAGA decibel requirements, outdoor IP ratings).

### Phase 4: Vendor Data Requirement (VDR) Template
- Generate VDR_Template.csv.
- Define standard NMR submission milestones (For Review, For Information, For Approval) and document categories (Drawings, Calculations, Testing Procedures, Manuals).

### Phase 5: Specification & Drawing Index
- Create Specification_Drawing_Index.csv to catalog all Saudi Aramco Standards (SAES), project drawings, calculations, and job specifications.

### Phase 6: TBE Preparation
- Generate TBE_Sheet.csv containing subsystem evaluation criteria and multi-vendor comparison matrices.

### Phase 7: Engineering Design Checklists
- Generate domain-specific checklists for each telecom subsystem (e.g., CCTV, PAGA, Data Network, ACS) to ensure all regulatory and design limits are met.
- Include interdiscipline interfaces (Civil, Piping, Electrical, HVAC) and Cable MTO modifiers (waste, slack, drops).

### Phase 8: Copying & Indexing Telecom Drawings
- Write python scripts to scan the source Google Drive folders for FEED drawings and specifications.
- Match documents against the drafted Material Requisition list.
- Copy verified PDF documents into the respective Appendix_5 subfolders.
- Update the Specification_Drawing_Index.csv with the actual file paths and availability statuses.

### Phase 9: Material Requisition (MR) Reference Updates & Review
- Update the main MR document with the final Section 7.0 (Reference Documents).
- Run automated verification scripts (deep_review.py) to cross-check the MR table against actual disk files.
- Fix any false HOLD statuses or category misplacements.
- Generate a formal verification report.

## Subsystem Taxonomy (16 Subsystems)
The standard scope includes:
1. Telephone & PABX
2. Industrial LAN/WAN/WIFI
3. PAGA System
4. PMR/TETRA Radio
5. Marine VHF Radio
6. Mobile 4G/LTE
7. CCTV (Process & Security)
8. Structured Cabling (ISP/OSP)
9. Fiber Optic Network
10. GPS Time Synchronization
11. Meteorological System
12. Access Control (ACS) & EPOB
13. Entertainment System (IPTV)
14. Perimeter Intrusion Detection (PIDS)
15. Security Philosophy
16. Telecom Interfaces

## Default Engineering Criteria (ITB Silent Rules)
- **CCTV**: H.264/H.265 at 1080p, 25-30 IPS live viewing, 15 IPS for 30-day storage (RAID 6).
- **PAGA**: 100V line, +10dB over ambient.
- **Redundancy**: 1+1 for core processors/switches/firewalls, N+1 for amplifiers.
- **Cable Slack**: 3m at field device, 5m at cabinet. 10% waste.
