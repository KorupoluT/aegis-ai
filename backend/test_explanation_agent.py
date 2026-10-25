from agents.explanation_agent import ExplanationAgent

print("Initializing AI Explanation Agent...")

agent = ExplanationAgent()

sample_assessment = {
    "risk_score": 30,
    "risk_level": "MEDIUM",
    "decision": "MANUAL_REVIEW",
    "evidence_sufficient": True,
    "findings": [
        "PAN-like pattern was not detected.",
        "Basic income information was extracted."
    ],
}

print("\n--- ENGLISH EXPLANATION ---")
print(agent.explain(sample_assessment, "english"))

print("\n--- TELUGU EXPLANATION ---")
print(agent.explain(sample_assessment, "telugu"))

print("\nTest completed.")
