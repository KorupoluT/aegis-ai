
class RiskAgent:
    """Evaluates document evidence and produces explainable risk indicators."""

    def __init__(self):
        self.name = "Risk Assessment Agent"

    def analyze(self, document_data: dict) -> dict:
        """
        Assess evidence quality and basic risk indicators.

        This is a rule-based prototype, not a fraud detector.
        It does not automatically approve or reject applicants.
        """
        extracted_fields = document_data.get("extracted_fields", {})

        # Some existing API responses store fields at the top level.
        name = document_data.get("name") or extracted_fields.get("name")
        income = document_data.get("income") or extracted_fields.get("income")
        raw_text = document_data.get("raw_text_preview", "")

        findings = []
        risk_score = 0

        # Check whether the document contains readable evidence.
        if not raw_text.strip():
            findings.append("No readable document text is available.")
            risk_score += 30

        # Check whether the applicant name was extracted.
        if not name:
            findings.append("Applicant name could not be extracted.")
            risk_score += 20

        # Check whether income was extracted and is numeric.
        income_value = None
        if income is not None:
            try:
                income_value = float(str(income).replace(",", "").strip())
            except (TypeError, ValueError):
                findings.append("Income value could not be interpreted.")
                risk_score += 15
        else:
            findings.append("Income information is missing.")
            risk_score += 20

        if income_value is not None and income_value < 0:
            findings.append("Income value is negative and needs verification.")
            risk_score += 20

        # Check for identity-number patterns, not identity authenticity.
        pan_detected = document_data.get(
            "pan_detected",
            extracted_fields.get("pan_detected", False),
        )
        identity_detected = document_data.get(
            "identity_number_detected",
            extracted_fields.get("identity_number_detected", False),
        )

        if not pan_detected:
            findings.append("PAN-like pattern was not detected.")
            risk_score += 10

        if not identity_detected:
            findings.append("12-digit identity-number pattern was not detected.")
            risk_score += 10

        risk_score = min(risk_score, 100)

        if risk_score < 30:
            risk_level = "LOW"
        elif risk_score < 60:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        # Missing or uncertain evidence always requires human review.
        evidence_sufficient = bool(raw_text.strip() and name and income_value is not None)

        if not evidence_sufficient:
            decision = "INSUFFICIENT_EVIDENCE"
        else:
            decision = "MANUAL_REVIEW"

        if not findings:
            findings.append(
                "Basic evidence checks passed. This does not establish "
                "document authenticity or applicant eligibility."
            )

        return {
            "agent": self.name,
            "status": "success",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "decision": decision,
            "evidence_sufficient": evidence_sufficient,
            "findings": findings,
            "requires_manual_review": True,
        }
