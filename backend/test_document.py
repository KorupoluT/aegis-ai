
from pathlib import Path
from agents.ocr_agent import OCRAgent

agent = OCRAgent()

# Make sure sample.pdf exists inside the backend folder.
file_path = Path("sample.pdf")

if not file_path.exists():
    print("ERROR: sample.pdf not found!")
    print("Place a PDF named sample.pdf inside the backend folder.")
else:
    result = agent.analyze(str(file_path.resolve()))

    print("\n===== DOCUMENT OCR TEST =====")
    print(result)

    if result["status"] == "success":
        print("\nExtracted text:")
        print(result.get("raw_text_preview", ""))

        print("\nExtracted fields:")
        print(result.get("extracted_fields", {}))
    else:
        print("\nOCR error:", result.get("message"))
