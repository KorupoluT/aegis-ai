
from datetime import datetime, timezone
from pathlib import Path
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.ocr_agent import OCRAgent
from agents.risk_agent import RiskAgent

# ============================================================
# AEGIS AI - MULTI-AGENT RISK INTELLIGENCE PLATFORM
# ============================================================

app = FastAPI(
    title="AegisAI",
    description="Multi-Agent Risk Intelligence Platform",
    version="1.0.2",
)


# ============================================================
# CORS
# Development configuration. Restrict origins before deployment.
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DIRECTORIES AND TEMPORARY STORAGE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

documents = {}
reports = {}

ocr_agent = OCRAgent()
risk_agent = RiskAgent()

ALLOWED_TYPES = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}


def current_timestamp():
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# EVIDENCE VALIDATION
# ============================================================

def has_sufficient_evidence(ocr_result: dict) -> bool:
    """
    Require readable extracted text and at least one recognized
    relevant field.

    Field extraction does not prove that a document is genuine.
    This is only a minimum evidence-availability check.
    """

    if not isinstance(ocr_result, dict):
        return False

    raw_text = str(
        ocr_result.get("raw_text_preview") or ""
    ).strip()

    fields = ocr_result.get("extracted_fields") or {}

    if not isinstance(fields, dict):
        return False

    has_relevant_field = any(
        [
            bool(str(fields.get("name") or "").strip()),
            bool(str(fields.get("income") or "").strip()),
            fields.get("pan_detected") is True,
            fields.get("identity_number_detected") is True,
        ]
    )

    return bool(raw_text) and has_relevant_field


# ============================================================
# SHARED RISK CLASSIFICATION
# ============================================================

def classify_risk_score(risk_score: int) -> dict:
    """
    Classify a heuristic risk score consistently.

    This score is an indicator for review, not proof of fraud.
    The score alone must not automatically approve or reject
    a real document or lending application.
    """

    risk_score = max(0, min(100, int(risk_score)))

    if risk_score < 30:
        return {
            "level": "LOW",
            "decision": "MANUAL_REVIEW",
            "recommendation": (
                "The heuristic risk score is low. Complete identity, "
                "document authenticity, and other required verification "
                "checks before making a final decision."
            ),
        }

    if risk_score < 60:
        return {
            "level": "MEDIUM",
            "decision": "MANUAL_REVIEW",
            "recommendation": (
                "Risk indicators require additional manual verification "
                "before making a final decision."
            ),
        }

    return {
        "level": "HIGH",
        "decision": "MANUAL_REVIEW",
        "recommendation": (
            "The heuristic risk score is high. Escalate the case for "
            "investigation and manual verification. The score alone "
            "is not proof of fraud."
        ),
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "project": "AegisAI",
        "message": "AegisAI Risk Intelligence API is running",
        "version": "1.0.2",
        "status": "online",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AegisAI Backend",
    }


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing.",
        )

    content_type = (file.content_type or "").lower()
    extension = Path(file.filename).suffix.lower()

    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG and PNG files are allowed.",
        )

    if extension not in ALLOWED_TYPES[content_type]:
        raise HTTPException(
            status_code=400,
            detail="File extension does not match the allowed file type.",
        )

    document_id = str(uuid.uuid4())
    saved_filename = f"{document_id}{extension}"
    file_path = UPLOAD_DIR / saved_filename

    try:
        # Avoid loading the entire uploaded file into memory.
        with file_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

    except OSError:
        if file_path.exists():
            file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Could not save document.",
        )

    finally:
        await file.close()

    document_data = {
        "document_id": document_id,
        "original_filename": Path(file.filename).name,
        "saved_filename": saved_filename,
        "file_type": content_type,
        "file_path": str(file_path),
        "uploaded_at": current_timestamp(),
        "status": "uploaded",
    }

    documents[document_id] = document_data

    return {
        "success": True,
        "message": "Document uploaded successfully",
        "document": document_data,
    }


# ============================================================
# GET DOCUMENT
# ============================================================

@app.get("/document/{document_id}")
def get_document(document_id: str):
    document = documents.get(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "success": True,
        "document": document,
    }


# ============================================================
# DOCUMENT ANALYSIS
# ============================================================

@app.post("/analyze/{document_id}")
def analyze_document(document_id: str):

    # --------------------------------------------------------
    # CHECK DOCUMENT
    # --------------------------------------------------------

    document = documents.get(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    file_path = Path(document["file_path"])

    if not file_path.is_file():
        documents[document_id]["status"] = "analysis_failed"

        raise HTTPException(
            status_code=404,
            detail="Uploaded document file is missing.",
        )

    documents[document_id]["status"] = "analyzing"

    # --------------------------------------------------------
    # OCR / DOCUMENT INTELLIGENCE
    # --------------------------------------------------------

    try:
        ocr_result = ocr_agent.analyze(str(file_path))

    except Exception:
        documents[document_id]["status"] = "analysis_failed"

        raise HTTPException(
            status_code=500,
            detail="Document analysis failed.",
        )

    if not isinstance(ocr_result, dict):
        documents[document_id]["status"] = "analysis_failed"

        raise HTTPException(
            status_code=500,
            detail="Document analysis returned an invalid result.",
        )

    if ocr_result.get("status") != "success":
        documents[document_id]["status"] = "analysis_failed"

        raise HTTPException(
            status_code=422,
            detail="The document could not be processed successfully.",
        )

    # --------------------------------------------------------
    # EXTRACTED FIELDS AND EVIDENCE GATE
    # --------------------------------------------------------

    extracted_fields = ocr_result.get("extracted_fields") or {}

    if not isinstance(extracted_fields, dict):
        extracted_fields = {}

    sufficient_evidence = has_sufficient_evidence(ocr_result)

    # ========================================================
    # ADDITIONAL RISK ASSESSMENT AGENT
    # ========================================================

    try:
        risk_assessment = risk_agent.analyze(ocr_result)
    except Exception:
        documents[document_id]["status"] = "analysis_failed"
        raise HTTPException(
            status_code=500,
            detail="Risk assessment failed.",
        )

    if not isinstance(risk_assessment, dict) or risk_assessment.get("status") != "success":
        documents[document_id]["status"] = "analysis_failed"
        raise HTTPException(
            status_code=500,
            detail="Risk assessment returned an invalid result.",
        )

    # Apply both evidence checks. The risk agent requires readable text,
    # an extracted name, and an interpretable income value.
    sufficient_evidence = (
        sufficient_evidence
        and risk_assessment.get("evidence_sufficient", False) is True
    )

    risk_agent_result = {
        "agent": risk_assessment.get("agent", "Risk Assessment Agent"),
        "status": "completed",
        "risk_score": max(0, min(100, int(risk_assessment.get("risk_score", 0)))),
        "risk_level": risk_assessment.get("risk_level", "UNKNOWN"),
        "finding": " ".join(risk_assessment.get("findings", [])),
        "requires_manual_review": True,
    }

    # ========================================================
    # FRAUD DETECTION AGENT
    # ========================================================

    fraud_score = 10

    fraud_findings = [
        "Automated analysis did not perform forensic "
        "document-authenticity verification."
    ]

    raw_text = str(
        ocr_result.get("raw_text_preview") or ""
    ).strip()

    if not raw_text:
        fraud_score += 10
        fraud_findings.append(
            "No readable document text was extracted."
        )

    if not sufficient_evidence:
        fraud_findings.append(
            "Evidence is insufficient for a reliable automated decision."
        )

    fraud_score = min(fraud_score, 100)

    fraud_agent = {
        "agent": "Fraud Detection Agent",
        "status": "completed",
        "risk_score": fraud_score,
        "finding": " ".join(fraud_findings),
    }

    # ========================================================
    # COMPLIANCE AGENT
    # ========================================================

    compliance_score = 10

    compliance_findings = [
        "Basic document-type and field-availability checks completed."
    ]

    document_type = ocr_result.get("document_type", "UNKNOWN")

    if document_type == "UNKNOWN":
        compliance_score += 15
        compliance_findings.append(
            "Document type could not be confidently determined."
        )

    if not sufficient_evidence:
        compliance_score += 20
        compliance_findings.append(
            "Required evidence is not sufficiently available."
        )

    compliance_score = min(compliance_score, 100)

    compliance_agent = {
        "agent": "Compliance Agent",
        "status": "completed",
        "risk_score": compliance_score,
        "finding": " ".join(compliance_findings),
    }

    # ========================================================
    # FINANCIAL RISK AGENT
    # ========================================================

    financial_score = 20
    income = extracted_fields.get("income")
    financial_findings = []

    if income is not None and str(income).strip():

        try:
            income_value = float(income)

            if income_value < 0:
                financial_score = 50
                financial_findings.append(
                    "Income value is invalid because it is negative."
                )

            elif income_value < 15000:
                financial_score = 45
                financial_findings.append(
                    "Detected income may require additional verification."
                )

            elif income_value < 30000:
                financial_score = 30
                financial_findings.append(
                    "Detected income indicates a need for further review."
                )

            else:
                financial_score = 15
                financial_findings.append(
                    "Income value was extracted and is available for review."
                )

        except (ValueError, TypeError):
            financial_score = 35
            financial_findings.append(
                "Income information could not be interpreted reliably."
            )

    else:
        financial_score = 35
        financial_findings.append(
            "No reliable income information was detected."
        )

    financial_score = min(financial_score, 100)

    financial_agent = {
        "agent": "Financial Risk Agent",
        "status": "completed",
        "risk_score": financial_score,
        "finding": " ".join(financial_findings),
    }

    # ========================================================
    # IDENTITY VERIFICATION AGENT
    # ========================================================

    identity_score = 10
    identity_findings = []

    if extracted_fields.get("pan_detected") is True:
        identity_findings.append(
            "PAN-like identifier detected; authenticity is not verified."
        )
    else:
        identity_score += 25
        identity_findings.append(
            "PAN identifier was not detected."
        )

    if extracted_fields.get("identity_number_detected") is True:
        identity_findings.append(
            "Identity-number pattern detected; authenticity is not verified."
        )
    else:
        identity_score += 10
        identity_findings.append(
            "Identity-number pattern was not detected."
        )

    identity_score = min(identity_score, 100)

    identity_agent = {
        "agent": "Identity Verification Agent",
        "status": "completed",
        "risk_score": identity_score,
        "finding": " ".join(identity_findings),
    }

    # ========================================================
    # OVERALL RISK SCORE
    # ========================================================

    agents = [
        fraud_agent,
        compliance_agent,
        financial_agent,
        identity_agent,
        risk_agent_result,
    ]

    agent_scores = [
        agent["risk_score"] for agent in agents
    ]

    overall_risk = round(
        sum(agent_scores) / len(agent_scores)
    )

    overall_risk = max(0, min(100, overall_risk))

    # ========================================================
    # RISK LEVEL AND DECISION
    # ========================================================

    # Insufficient evidence always takes priority over the score.
    # A heuristic score is not enough to approve or reject a real case.

    if not sufficient_evidence:

        risk_level = "INSUFFICIENT_EVIDENCE"
        decision = "MANUAL_REVIEW"

        recommendation = (
            "The document does not contain enough readable text "
            "and required fields for a reliable automated assessment. "
            "Verify the document manually. OCR output may contain errors, "
            "and extracted identity patterns do not establish authenticity."
        )

    else:

        classification = classify_risk_score(overall_risk)

        risk_level = classification["level"]
        decision = classification["decision"]
        recommendation = classification["recommendation"]

    # ========================================================
    # EXPLAINABILITY
    # ========================================================

    explanation = [
        "Document processed by the Document Intelligence Agent.",
        f"Evidence sufficient for automatic scoring: {sufficient_evidence}.",
        fraud_agent["finding"],
        compliance_agent["finding"],
        financial_agent["finding"],
        identity_agent["finding"],
        risk_agent_result["finding"],
    ]

    if not sufficient_evidence:
        explanation.append(
            "Automatic approval was blocked because evidence "
            "was insufficient."
        )

    explanation.append(
        "The heuristic risk score is an indicator for review, "
        "not proof of document authenticity or fraud."
    )

    # ========================================================
    # CREATE REPORT
    # ========================================================

    report_id = str(uuid.uuid4())

    report = {
        "report_id": report_id,
        "document_id": document_id,
        "created_at": current_timestamp(),
        "document_intelligence": ocr_result,
        "evidence_check": {
            "sufficient_evidence": sufficient_evidence,
            "automatic_approval_allowed": False,
            "status": (
                "sufficient" if sufficient_evidence else "insufficient"
            ),
        },
        "risk": {
            "score": overall_risk,
            "level": risk_level,
            "assessment_agent": {
                "score": risk_agent_result["risk_score"],
                "level": risk_agent_result["risk_level"],
                "evidence_sufficient": risk_assessment.get(
                    "evidence_sufficient", False
                ),
                "findings": risk_assessment.get("findings", []),
            },
        },
        "decision": decision,
        "recommendation": recommendation,
        "explanation": explanation,
        "agents": agents,
    }

    reports[report_id] = report

    documents[document_id]["status"] = "analyzed"
    documents[document_id]["report_id"] = report_id

    return {
        "success": True,
        "message": "Multi-agent analysis completed",
        "report": report,
    }


# ============================================================
# GET REPORT
# ============================================================

@app.get("/report/{report_id}")
def get_report(report_id: str):
    report = reports.get(report_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    return {
        "success": True,
        "report": report,
    }


# ============================================================
# WHAT-IF RISK SIMULATION
# ============================================================

@app.post("/simulate")
async def simulate_risk(
    loan_amount: float = 100000,
    co_applicant: bool = False,
):
    if loan_amount < 0:
        raise HTTPException(
            status_code=400,
            detail="Loan amount cannot be negative.",
        )

    base_score = 35

    if loan_amount > 1000000:
        base_score += 20
    elif loan_amount > 500000:
        base_score += 10
    elif loan_amount > 250000:
        base_score += 5

    if co_applicant:
        base_score -= 10

    risk_score = max(0, min(100, base_score))

    classification = classify_risk_score(risk_score)

    return {
        "success": True,
        "simulation_only": True,
        "message": (
            "This is a hypothetical risk simulation, "
            "not a final lending decision."
        ),
        "simulation": {
            "loan_amount": loan_amount,
            "co_applicant": co_applicant,
            "risk_score": risk_score,
            "risk_level": classification["level"],
            "decision": classification["decision"],
            "recommendation": classification["recommendation"],
        },
    }


# ============================================================
# LIST ALL DOCUMENTS
# ============================================================

@app.get("/documents")
def list_documents():
    return {
        "success": True,
        "count": len(documents),
        "documents": list(documents.values()),
    }


# ============================================================
# LIST ALL REPORTS
# ============================================================

@app.get("/reports")
def list_reports():
    return {
        "success": True,
        "count": len(reports),
        "reports": list(reports.values()),
    }


# ============================================================
# DELETE DOCUMENT
# ============================================================

@app.delete("/document/{document_id}")
def delete_document(document_id: str):
    document = documents.get(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    file_path = Path(document["file_path"])

    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            raise HTTPException(
                status_code=500,
                detail="Could not delete document file.",
            )

    report_id = document.get("report_id")

    if report_id:
        reports.pop(report_id, None)

    del documents[document_id]

    return {
        "success": True,
        "message": "Document deleted successfully",
        "document_id": document_id,
    }


# ============================================================
# CHAT
# ============================================================

class ChatRequest(BaseModel):
    message: str = Field(max_length=4000)


@app.post("/chat")
def chat(request: ChatRequest):
    user_message = request.message.strip()

    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    # Placeholder response: this is not a connected LLM.
    response = f"AegisAI received your message: {user_message}"

    return {
        "success": True,
        "message": response,
    }


# ============================================================
# APPLICATION STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():
    print()
    print("=" * 60)
    print("              AEGISAI BACKEND")
    print("=" * 60)
    print("Status : ONLINE")
    print("API    : http://127.0.0.1:8000")
    print("Docs   : http://127.0.0.1:8000/docs")
    print("=" * 60)
    print()
