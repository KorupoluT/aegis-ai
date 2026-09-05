from pathlib import Path
from pypdf import PdfReader
import re


class OCRAgent:

    def __init__(self):
        self.name = "Document Intelligence Agent"

    def analyze(self, file_path: str):

        path = Path(file_path)

        if not path.exists():
            return {
                "agent": self.name,
                "status": "error",
                "message": "Document not found"
            }

        extension = path.suffix.lower()

        # PDF
        if extension == ".pdf":
            return self._analyze_pdf(path)

        # Images
        if extension in [".jpg", ".jpeg", ".png"]:
            return self._analyze_image(path)

        return {
            "agent": self.name,
            "status": "error",
            "message": f"Unsupported document type: {extension}"
        }

    # ============================================================
    # PDF ANALYSIS
    # ============================================================

    def _analyze_pdf(self, path: Path):

        try:

            reader = PdfReader(str(path))

            text = ""

            for page in reader.pages:

                page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n"

            fields = self._extract_fields(text)

            return {
                "agent": self.name,
                "status": "success",
                "document_type": "PDF",
                "pages": len(reader.pages),
                "extracted_fields": fields,
                "raw_text_preview": text[:1000]
            }

        except Exception as error:

            return {
                "agent": self.name,
                "status": "error",
                "message": str(error)
            }

    # ============================================================
    # IMAGE ANALYSIS
    # ============================================================

    def _analyze_image(self, path: Path):

        return {
            "agent": self.name,
            "status": "success",
            "document_type": path.suffix.replace(".", "").upper(),
            "message": "Image received. OCR processing can be connected next.",
            "extracted_fields": {}
        }

    # ============================================================
    # FIELD EXTRACTION
    # ============================================================

    def _extract_fields(self, text: str):

        fields = {}

        # --------------------------------------------------------
        # NAME
        # --------------------------------------------------------

        name_match = re.search(
            r"(?:name|applicant name)\s*[:\-]?\s*([A-Za-z][A-Za-z ]+)",
            text,
            re.IGNORECASE
        )

        if name_match:

            fields["name"] = name_match.group(1).strip()

        # --------------------------------------------------------
        # INCOME
        # --------------------------------------------------------

        income_match = re.search(
            r"(?:income|salary|monthly income)\s*[:\-]?\s*[₹Rs.]*\s*([\d,]+)",
            text,
            re.IGNORECASE
        )

        if income_match:

            fields["income"] = income_match.group(1).replace(",", "")

        # --------------------------------------------------------
        # PAN
        # --------------------------------------------------------

        pan_match = re.search(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
            text
        )

        if pan_match:

            fields["pan_detected"] = True
            fields["pan"] = pan_match.group(0)

        else:

            fields["pan_detected"] = False

        # --------------------------------------------------------
        # AADHAAR-LIKE NUMBER
        # --------------------------------------------------------

        aadhaar_match = re.search(
            r"\b\d{4}\s\d{4}\s\d{4}\b",
            text
        )

        if aadhaar_match:

            fields["identity_number_detected"] = True

        else:

            fields["identity_number_detected"] = False

        return fields