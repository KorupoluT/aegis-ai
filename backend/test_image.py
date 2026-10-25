
from pathlib import Path
from agents.ocr_agent import OCRAgent

agent = OCRAgent()

image_path = Path("sample.png")

if not image_path.exists():
    print("ERROR: sample.png not found in the backend folder.")
else:
    result = agent.analyze(str(image_path.resolve()))

    print("\n===== IMAGE OCR TEST =====")
    print(result)

    if result["status"] == "success":
        print("\nExtracted text:")
        print(result.get("raw_text_preview", ""))

        print("\nExtracted fields:")
        print(result.get("extracted_fields", {}))
    else:
        print("\nOCR error:", result.get("message"))
