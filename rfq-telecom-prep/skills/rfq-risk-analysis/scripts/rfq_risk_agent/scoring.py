"""
Risk Scoring Module for RFQ Bid Risk Analysis.

Implements a 5x5 Probability x Impact matrix for risk severity classification.
Score thresholds: CRITICAL >= 15, HIGH >= 9, MEDIUM >= 4, LOW < 4.
"""

from rfq_risk_agent.models import RiskSeverity


# 5x5 Probability x Impact Matrix
# Rows: Probability (1=Rare to 5=Almost Certain)
# Columns: Impact (1=Negligible to 5=Catastrophic)
RISK_MATRIX = [
    [1,  2,  3,  4,  5],   # Probability 1 (Rare)
    [2,  4,  6,  8,  10],  # Probability 2 (Unlikely)
    [3,  6,  9,  12, 15],  # Probability 3 (Possible)
    [4,  8,  12, 16, 20],  # Probability 4 (Likely)
    [5,  10, 15, 20, 25],  # Probability 5 (Almost Certain)
]

# Severity thresholds
CRITICAL_THRESHOLD = 15
HIGH_THRESHOLD = 9
MEDIUM_THRESHOLD = 4

# Probability descriptors
PROBABILITY_LABELS = {
    1: "Rare",
    2: "Unlikely",
    3: "Possible",
    4: "Likely",
    5: "Almost Certain",
}

# Impact descriptors
IMPACT_LABELS = {
    1: "Negligible",
    2: "Minor",
    3: "Moderate",
    4: "Major",
    5: "Catastrophic",
}


def calculate_risk_score(probability: int, impact: int) -> int:
    """Calculate risk score from probability and impact values.

    Args:
        probability: Value from 1 (Rare) to 5 (Almost Certain).
        impact: Value from 1 (Negligible) to 5 (Catastrophic).

    Returns:
        Risk score (1-25).

    Raises:
        ValueError: If probability or impact is outside the 1-5 range.
    """
    if not (1 <= probability <= 5):
        raise ValueError(f"Probability must be 1-5, got {probability}")
    if not (1 <= impact <= 5):
        raise ValueError(f"Impact must be 1-5, got {impact}")
    return RISK_MATRIX[probability - 1][impact - 1]


def classify_severity(score: int) -> RiskSeverity:
    """Classify a risk score into a severity level.

    Args:
        score: Risk score from calculate_risk_score (1-25).

    Returns:
        RiskSeverity enum value.
    """
    if score >= CRITICAL_THRESHOLD:
        return RiskSeverity.CRITICAL
    elif score >= HIGH_THRESHOLD:
        return RiskSeverity.HIGH
    elif score >= MEDIUM_THRESHOLD:
        return RiskSeverity.MEDIUM
    else:
        return RiskSeverity.LOW


def get_severity_emoji(severity: RiskSeverity) -> str:
    """Return the emoji indicator for a risk severity level."""
    return {
        RiskSeverity.CRITICAL: "🔴",
        RiskSeverity.HIGH: "🟠",
        RiskSeverity.MEDIUM: "🟡",
        RiskSeverity.LOW: "🟢",
    }[severity]


def get_probability_label(probability: int) -> str:
    """Return the human-readable label for a probability value."""
    return PROBABILITY_LABELS.get(probability, f"Unknown ({probability})")


def get_impact_label(impact: int) -> str:
    """Return the human-readable label for an impact value."""
    return IMPACT_LABELS.get(impact, f"Unknown ({impact})")


def format_risk_score_display(probability: int, impact: int) -> str:
    """Format a risk score for display with labels.

    Returns a string like: "P3 (Possible) × I4 (Major) = 12 🟠 HIGH"
    """
    score = calculate_risk_score(probability, impact)
    severity = classify_severity(score)
    emoji = get_severity_emoji(severity)
    p_label = get_probability_label(probability)
    i_label = get_impact_label(impact)
    return f"P{probability} ({p_label}) × I{impact} ({i_label}) = {score} {emoji} {severity.value}"


def generate_risk_matrix_markdown() -> str:
    """Generate the full 5x5 risk matrix as a Markdown table.

    Returns a formatted Markdown string with color-coded severity indicators.
    """
    header = "| | I1 (Negligible) | I2 (Minor) | I3 (Moderate) | I4 (Major) | I5 (Catastrophic) |"
    separator = "|---|:---:|:---:|:---:|:---:|:---:|"
    rows = []

    for p in range(5, 0, -1):
        p_label = PROBABILITY_LABELS[p]
        cells = []
        for i in range(1, 6):
            score = calculate_risk_score(p, i)
            severity = classify_severity(score)
            emoji = get_severity_emoji(severity)
            cells.append(f"{emoji} {score}")
        row = f"| **P{p} ({p_label})** | {' | '.join(cells)} |"
        rows.append(row)

    return "\n".join([header, separator] + rows)
