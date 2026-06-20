"""
Risk Analyzer Engine.

Evaluates an extracted SpecDocument against the Risk Knowledge Base
and Project Context to generate Risk findings.
"""

import json
import logging
import re
from pathlib import Path
from typing import Iterator, Optional

from rfq_risk_agent.models import (
    ProjectContext,
    Risk,
    RiskDimension,
    RiskRule,
    RiskSeverity,
    SpecDocument,
)
from rfq_risk_agent.scoring import calculate_risk_score, classify_severity

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """Core engine for identifying risks in telecom/security specifications."""

    def __init__(self, knowledge_base_path: Path):
        """Initialise the analyzer with rules from the knowledge base."""
        self.rules = self._load_knowledge_base(knowledge_base_path)
        logger.info("Loaded %d risk rules from KB.", len(self.rules))

    def _load_knowledge_base(self, kb_path: Path) -> list[RiskRule]:
        """Parse the JSON knowledge base into RiskRule objects."""
        if not kb_path.exists():
            raise FileNotFoundError(f"Knowledge base not found: {kb_path}")

        data = json.loads(kb_path.read_text(encoding="utf-8"))
        rules = []

        for dim_key, dim_data in data.get("risk_dimensions", {}).items():
            try:
                dimension = RiskDimension(dim_key)
            except ValueError:
                logger.warning("Unknown dimension %s in KB, skipping.", dim_key)
                continue

            for r in dim_data.get("rules", []):
                rules.append(
                    RiskRule(
                        rule_id=r["rule_id"],
                        dimension=dimension,
                        check_description=r["check"],
                        trigger_condition=r["trigger_condition"],
                        default_probability=r.get("default_probability", 3),
                        default_impact=r.get("default_impact", 3),
                        keywords=r.get("trigger_keywords", []),
                        applicable_subsystems=r.get("applicable_subsystems", ["ALL"]),
                    )
                )

        return rules

    def analyze(self, spec: SpecDocument, context: ProjectContext) -> list[Risk]:
        """Analyze a specification against all rules and context.

        Args:
            spec: The extracted specification document.
            context: The broader RFQ project context.

        Returns:
            A list of identified Risk findings.
        """
        risks = []
        full_text_lower = spec.full_text.lower()
        shall_texts_lower = [s.text.lower() for s in spec.shall_statements]

        for rule in self.rules:
            # 1. Check Standards Compliance
            if rule.dimension == RiskDimension.D1_STANDARDS_COMPLIANCE:
                risk = self._evaluate_d1(rule, spec, context, full_text_lower)
                if risk:
                    risks.append(risk)

            # 2. Check Scope Completeness
            elif rule.dimension == RiskDimension.D2_SCOPE_COMPLETENESS:
                risk = self._evaluate_d2(rule, spec, context, full_text_lower)
                if risk:
                    risks.append(risk)

            # 3. Check Technical Adequacy
            elif rule.dimension == RiskDimension.D3_TECHNICAL_ADEQUACY:
                risk = self._evaluate_d3(rule, spec, context, full_text_lower, shall_texts_lower)
                if risk:
                    risks.append(risk)

            # 4. Check Documentation Gaps
            elif rule.dimension == RiskDimension.D4_DOCUMENTATION_GAPS:
                risk = self._evaluate_d4(rule, spec, context, full_text_lower)
                if risk:
                    risks.append(risk)

            # 5. Check Interface Coordination
            elif rule.dimension == RiskDimension.D5_INTERFACE_COORDINATION:
                risk = self._evaluate_d5(rule, spec, context, full_text_lower)
                if risk:
                    risks.append(risk)

            # 6. Check Commercial Schedule
            elif rule.dimension == RiskDimension.D6_COMMERCIAL_SCHEDULE:
                risk = self._evaluate_d6(rule, spec, context, full_text_lower)
                if risk:
                    risks.append(risk)

        # Generate unique risk IDs (e.g. RISK-001)
        for i, risk in enumerate(risks, 1):
            risk.risk_id = f"RISK-{i:03d}"

        return risks

    def _create_risk(self, rule: RiskRule, spec: SpecDocument, source_ref: str, mitigation_override: str = "") -> Risk:
        """Helper to create a Risk object from a triggered rule."""
        score = calculate_risk_score(rule.default_probability, rule.default_impact)
        severity = classify_severity(score)
        
        # Look up mitigation from original rule dictionary if possible, 
        # or use override, or use trigger condition as placeholder
        return Risk(
            risk_id="",  # Assigned later
            rule_id=rule.rule_id,
            dimension=rule.dimension,
            severity=severity,
            description=rule.check_description,
            source_reference=source_ref,
            probability=rule.default_probability,
            impact=rule.default_impact,
            score=score,
            affected_subsystems=list(rule.applicable_subsystems),
            mitigation=mitigation_override or "Review specification and resolve gap.",
            spec_document_id=spec.document_id
        )

    def _matches_any_keyword(self, keywords: list[str], text_lower: str) -> bool:
        """Check if any keyword is present in the lowercased text."""
        return any(kw.lower() in text_lower for kw in keywords)

    # --- Dimension Evaluators ---

    def _evaluate_d1(self, rule: RiskRule, spec: SpecDocument, context: ProjectContext, text: str) -> Optional[Risk]:
        # D1-001: SAES referenced but HOLD/Missing
        if rule.rule_id == "D1-001":
            missing = []
            for std in spec.referenced_standards:
                if std in context.mr_saes_standards:
                    status = context.mr_saes_standards[std].upper()
                    if "HOLD" in status or "MISSING" in status:
                        missing.append(f"{std} ({status})")
            if missing:
                return self._create_risk(rule, spec, f"References section: {', '.join(missing)}")
            return None

        # Standard missing reference rules (D1-002 to D1-006, D1-008 to D1-010)
        if rule.rule_id in ["D1-002", "D1-003", "D1-004", "D1-005", "D1-006", "D1-008", "D1-009", "D1-010"]:
            # If the spec mentions the domain keywords
            if self._matches_any_keyword(rule.keywords, text):
                # Extract the target standard from the check description (e.g. "SAES-T-555")
                match = re.search(r'(SAES-[A-Z]-\d{3}|SAIS|SEC-\d{2})', rule.check_description)
                if match:
                    target_std = match.group(1)
                    if not any(target_std in std for std in spec.referenced_standards):
                        return self._create_risk(rule, spec, f"Missing standard: {target_std}")
        
        return None

    def _evaluate_d2(self, rule: RiskRule, spec: SpecDocument, context: ProjectContext, text: str) -> Optional[Risk]:
        # D2-004: Battery/UPS backup duration not specified
        if rule.rule_id == "D2-004":
            if "ups" in text or "battery" in text:
                if not re.search(r'(duration|backup time|hours|hrs|minutes|mins)', text):
                    return self._create_risk(rule, spec, "Equipment Power Supply Section")
        
        # D2-005: Spare parts scope
        if rule.rule_id == "D2-005":
            if not re.search(r'(commissioning spare|operational spare|2-year spare|two year spare)', text):
                return self._create_risk(rule, spec, "Spares Section Missing")
                
        # D2-008: Contractor vs Vendor scope
        if rule.rule_id == "D2-008":
            if "contractor" in text and "vendor" in text:
                if not re.search(r'(scope of supply|responsibility matrix|contractor shall supply|vendor shall supply)', text):
                    return self._create_risk(rule, spec, "General Scope")

        return None

    def _evaluate_d3(self, rule: RiskRule, spec: SpecDocument, context: ProjectContext, text: str, shalls: list[str]) -> Optional[Risk]:
        # D3-001: CCTV resolution
        if rule.rule_id == "D3-001":
            if "cctv" in text or "camera" in text:
                has_res = False
                for shall in shalls:
                    if "resolution" in shall or "1080p" in shall or "megapixel" in shall or " 4k " in shall:
                        has_res = True
                        break
                if not has_res:
                    return self._create_risk(rule, spec, "CCTV Camera Specifications")

        # D3-003: Redundancy
        if rule.rule_id == "D3-003":
            if "server" in text or "controller" in text:
                if not self._matches_any_keyword(["redundant", "redundancy", "n+1", "1+1", "hot-standby"], text):
                    return self._create_risk(rule, spec, "System Architecture")

        # D3-012: Cybersecurity
        if rule.rule_id == "D3-012":
            if "network" in text or "server" in text:
                if not self._matches_any_keyword(["cybersecurity", "firewall", "ips", "encryption", "tls"], text):
                    return self._create_risk(rule, spec, "Network Architecture")

        return None

    def _evaluate_d4(self, rule: RiskRule, spec: SpecDocument, context: ProjectContext, text: str) -> Optional[Risk]:
        # D4-001: Drawing referenced but HOLD/Missing
        if rule.rule_id == "D4-001":
            missing = []
            for dwg in spec.referenced_drawings:
                if dwg in context.mr_drawings:
                    status = context.mr_drawings[dwg].upper()
                    if "HOLD" in status or "MISSING" in status:
                        missing.append(f"{dwg} ({status})")
            if missing:
                return self._create_risk(rule, spec, f"Referenced Drawings: {', '.join(missing)}")
        
        # D4-003: FAT/SAT procedure
        if rule.rule_id == "D4-003":
            if "fat " in text or "sat " in text or "factory acceptance" in text:
                if not re.search(r'(procedure|test plan|script|criteria)', text):
                    return self._create_risk(rule, spec, "Testing & Commissioning Section")

        return None

    def _evaluate_d5(self, rule: RiskRule, spec: SpecDocument, context: ProjectContext, text: str) -> Optional[Risk]:
        # D5-002: Electrical interface
        if rule.rule_id == "D5-002":
            if "cabinet" in text or "rack" in text:
                if not self._matches_any_keyword(["feeder", "circuit breaker", "power source", "electrical load"], text):
                    return self._create_risk(rule, spec, "Cabinet/Rack Specifications")

        # D5-005: Fire alarm integration
        if rule.rule_id == "D5-005":
            if "access control" in text or "acs " in text or "door lock" in text:
                if not self._matches_any_keyword(["fire alarm", "facp", "fail-safe", "emergency release"], text):
                    return self._create_risk(rule, spec, "Access Control Hardware")

        return None

    def _evaluate_d6(self, rule: RiskRule, spec: SpecDocument, context: ProjectContext, text: str) -> Optional[Risk]:
        # D6-002: Training scope
        if rule.rule_id == "D6-002":
            if "training" in text:
                if not re.search(r'(duration|days|hours|attendees|curriculum)', text):
                    return self._create_risk(rule, spec, "Training Section")

        # D6-003: Warranty terms
        if rule.rule_id == "D6-003":
            if "warranty" in text or "guarantee" in text:
                if not re.search(r'(months|years|defect liability)', text):
                    return self._create_risk(rule, spec, "Warranty Section")

        return None
