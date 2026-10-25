
from pathlib import Path
from agents.ocr_agent import OCRAgent

agent = OCRAgent()

# Test field extraction without needing a document file.
sample_text = """
Applicant Name: Ravi Kumar
Monthly Income: Rs. 50,000
PAN: ABCDE1234F
Aadhaar: 1234 5678 9012
"""

fields = agent._extract_fields(sample_text)

print("\n===== OCR FIELD EXTRACTION TEST =====")
print("Extracted fields:", fields)

assert fields.get("name") == "Ravi Kumar"
assert fields.get("income") == "50000"
assert fields.get("pan_detected") is True
assert fields.get("identity_number_detected") is True

print("\nPASS: All field extraction tests passed!")

# Test missing text.
empty_fields = agent._extract_fields("")
assert empty_fields["pan_detected"] is False
assert empty_fields["identity_number_detected"] is False

print("PASS: Empty-text test passed!")
