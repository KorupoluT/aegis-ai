
from agents.risk_agent import RiskAgent

agent = RiskAgent()

sample_document = {
    "name": "Ravi Kumar",
    "income": "50000",
    "raw_text_preview": (
        "Applicant Name: Ravi Kumar\n"
        "Monthly Income: Rs. 50,000\n"
        "PAN: ABCDE1234F\n"
        "Aadhaar: 1234 5678 9012"
    ),
    "pan_detected": True,
    "identity_number_detected": True,
}

result = agent.analyze(sample_document)

print("\n===== RISK AGENT TEST =====")
print(result)
