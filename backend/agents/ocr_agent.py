
from pathlib import Path
import re

from pypdf import PdfReader
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

class OCRAgent:
    def __init__(self):
        self.name = "Document Intelligence Agent"

    def analyze(self, file_path: str) -> dict:
        path = Path(file_path)

        if not path.exists() or not path.is_file():
            return self._error("Document not found")

        extension = path.suffix.lower()

        try:
            if extension == ".pdf":
                return self._analyze_pdf(path)

            if extension in {".jpg", ".jpeg", ".png"}:
                return self._analyze_image(path)

            return self._error(
                f"Unsupported document type: {extension}"
            )

        except Exception as error:
            return self._error(
                f"Document analysis failed: {error}"
            )

    def _error(self, message: str) -> dict:
        return {
            "agent": self.name,
            "status": "error",
            "message": message,
        }

    def _build_result(
        self,
        document_type: str,
        text: str,
        **metadata,
    ) -> dict:
        text = text.strip()
        fields = self._extract_fields(text)

        # Keep extracted_fields for structured output.
        # Also expose fields at the top level because the
        # current main.py evidence gate checks those keys.
        result = {
            "agent": self.name,
            "status": "success",
            "document_type": document_type,
            "extracted_fields": fields,
            "raw_text_preview": text[:1000],
            "text_extracted": bool(text),
            **metadata,
        }

        result.update(fields)
        return result

    # ---------------------------------------------------------
    # PDF ANALYSIS
    # ---------------------------------------------------------

    def _analyze_pdf(self, path: Path) -> dict:
        reader = PdfReader(str(path))
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text.strip())

        text = "\n".join(text_parts)

        # Scanned PDFs often contain images instead of selectable
        # text. Try optional OCR when normal PDF extraction is empty.
        if not text.strip():
            text = self._ocr_scanned_pdf(path)

        result = self._build_result(
            document_type="PDF",
            text=text,
            pages=len(reader.pages),
        )

        if not text.strip():
            result["message"] = (
                "No readable text was extracted. This may be a "
                "scanned PDF. Check the OCR dependencies and "
                "document image quality."
            )

        return result

    # ---------------------------------------------------------
    # IMAGE ANALYSIS
    # ---------------------------------------------------------

    def _analyze_image(self, path: Path) -> dict:
        try:
            import pytesseract
            from PIL import Image, ImageOps

            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image)
                image = ImageOps.grayscale(image)
                text = pytesseract.image_to_string(
                    image,
                    config="--psm 6",
                )

        except ImportError:
            return self._error(
                "Image OCR dependencies are missing. Install "
                "'pytesseract' and 'Pillow', and install the "
                "Tesseract OCR application separately."
            )
        except Exception as error:
            return self._error(
                "Image OCR failed. Confirm that Tesseract OCR "
                f"is installed and the image is readable: {error}"
            )

        return self._build_result(
            document_type=path.suffix.lstrip(".").upper(),
            text=text,
        )

    # ---------------------------------------------------------
    # OPTIONAL SCANNED-PDF OCR
    # ---------------------------------------------------------

    def _ocr_scanned_pdf(self, path: Path) -> str:
        try:
            from pdf2image import convert_from_path
            import pytesseract

            pages = convert_from_path(
                str(path),
                first_page=1,
                last_page=10,
                dpi=200,
            )

            extracted_pages = []

            for page in pages:
                extracted = pytesseract.image_to_string(
                    page,
                    config="--psm 6",
                )
                if extracted.strip():
                    extracted_pages.append(extracted.strip())

            return "\n".join(extracted_pages)

        except ImportError:
            # Text extraction can still succeed for ordinary PDFs.
            # Scanned PDFs need the optional dependencies.
            return ""
        except Exception:
            # Fail closed: do not invent text if OCR fails.
            return ""

    # ---------------------------------------------------------
    # FIELD EXTRACTION
    # ---------------------------------------------------------

    def _extract_fields(self, text: str) -> dict:
        fields = {}

        if not text.strip():
            return {
                "pan_detected": False,
                "identity_number_detected": False,
            }

        # Normalize whitespace while preserving line boundaries.
        lines = [
            re.sub(r"[ \t]+", " ", line).strip()
            for line in text.splitlines()
        ]

        # NAME: limit extraction to the matching line to avoid
        # accidentally consuming the rest of the document.
        name_labels = (
            r"(?:applicant\s+name|full\s+name|name)"
        )

        for line in lines:
            match = re.match(
                rf"^{name_labels}\s*[:\-]?\s*(.*?)\s*$",
                line,
                re.IGNORECASE,
            )

            if not match:
                continue

            candidate = match.group(1).strip(" :-")

            # Reject empty values and obvious non-name placeholders.
            if (
                candidate
                and re.search(r"[A-Za-z]", candidate)
                and len(candidate) <= 100
                and not re.search(
                    r"\b(income|salary|address|date of birth)\b",
                    candidate,
                    re.IGNORECASE,
                )
            ):
                fields["name"] = candidate
                break

        # INCOME: handles examples such as:
        # Income: 50000
        # Monthly Income: Rs. 50,000
        # Salary: ₹50,000
        income_pattern = re.compile(
            r"\b(?:monthly\s+income|annual\s+income|income|salary)"
            r"\b\s*[:\-]?\s*"
            r"(?:(?:INR|Rs\.?)\s*|₹\s*)?"
            r"([\d,]+(?:\.\d{1,2})?)",
            re.IGNORECASE,
        )

        for line in lines:
            match = income_pattern.search(line)
            if match:
                amount = match.group(1).replace(",", "")
                try:
                    if float(amount) >= 0:
                        fields["income"] = amount
                        break
                except ValueError:
                    pass

        # PAN: pattern detection only, not government verification.
        pan_match = re.search(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
            text,
            re.IGNORECASE,
        )

        fields["pan_detected"] = bool(pan_match)

        if pan_match:
            fields["pan"] = pan_match.group(0).upper()

        # Aadhaar-like number: report presence only.
        # Do not store the number in extracted output.
        identity_match = re.search(
            r"(?<!\d)(?:\d{4}[\s-]?){2}\d{4}(?!\d)",
            text,
        )

        fields["identity_number_detected"] = bool(
            identity_match
        )

        return fields
