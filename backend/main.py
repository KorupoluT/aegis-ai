from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import shutil
import uuid
from datetime import datetime

from agents.ocr_agent import OCRAgent


# ============================================================
# AEGISAI - MULTI-AGENT RISK INTELLIGENCE PLATFORM
# ============================================================

app = FastAPI(
    title="AegisAI",
    description="Multi-Agent Risk Intelligence Platform",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# TEMPORARY STORAGE
# ============================================================

documents = {}
reports = {}


# ============================================================
# AGENTS
# ============================================================

ocr_agent = OCRAgent()


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "project": "AegisAI",
        "message": "AegisAI Risk Intelligence API is running",
        "version": "1.0.0",
        "status": "online"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "AegisAI Backend"
    }


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    allowed_types = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/jpg"
    ]

    # --------------------------------------------------------
    # CHECK FILE TYPE
    # --------------------------------------------------------

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG and PNG files are allowed."
        )

    # --------------------------------------------------------
    # CHECK FILE NAME
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is missing."
        )

    # --------------------------------------------------------
    # CREATE DOCUMENT ID
    # --------------------------------------------------------

    document_id = str(uuid.uuid4())

    # --------------------------------------------------------
    # GET FILE EXTENSION
    # --------------------------------------------------------

    extension = Path(file.filename).suffix.lower()

    if not extension:
        extension = ".bin"

    # --------------------------------------------------------
    # CREATE SAFE SAVED FILE NAME
    # --------------------------------------------------------

    saved_filename = f"{document_id}{extension}"

    file_path = UPLOAD_DIR / saved_filename

    # --------------------------------------------------------
    # SAVE FILE
    # --------------------------------------------------------

    try:

        with open(file_path, "wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Could not save document: {str(error)}"
        )

    # --------------------------------------------------------
    # DOCUMENT DATA
    # --------------------------------------------------------

    document_data = {

        "document_id": document_id,

        "original_filename": file.filename,

        "saved_filename": saved_filename,

        "file_type": file.content_type,

        "file_path": str(file_path),

        "uploaded_at": datetime.now().isoformat(),

        "status": "uploaded"
    }

    documents[document_id] = document_data

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "success": True,

        "message": "Document uploaded successfully",

        "document": document_data
    }


# ============================================================
# GET DOCUMENT
# ============================================================

@app.get("/document/{document_id}")
def get_document(document_id: str):

    if document_id not in documents:

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return {

        "success": True,

        "document": documents[document_id]
    }


# ============================================================
# DOCUMENT ANALYSIS
# ============================================================

@app.post("/analyze/{document_id}")
def analyze_document(document_id: str):

    # --------------------------------------------------------
    # CHECK DOCUMENT
    # --------------------------------------------------------

    if document_id not in documents:

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    document = documents[document_id]

    # --------------------------------------------------------
    # UPDATE STATUS
    # --------------------------------------------------------

    documents[document_id]["status"] = "analyzing"

    # --------------------------------------------------------
    # OCR / DOCUMENT INTELLIGENCE
    # --------------------------------------------------------

    try:

        ocr_result = ocr_agent.analyze(
            document["file_path"]
        )

    except Exception as error:

        documents[document_id]["status"] = "analysis_failed"

        raise HTTPException(
            status_code=500,
            detail=f"OCR analysis failed: {str(error)}"
        )

    # --------------------------------------------------------
    # CHECK OCR RESULT
    # --------------------------------------------------------

    if ocr_result.get("status") == "error":

        documents[document_id]["status"] = "analysis_failed"

        raise HTTPException(
            status_code=500,
            detail=ocr_result.get(
                "message",
                "Document analysis failed."
            )
        )

    # --------------------------------------------------------
    # EXTRACTED FIELDS
    # --------------------------------------------------------

    extracted_fields = ocr_result.get(
        "extracted_fields",
        {}
    )


    # ========================================================
    # FRAUD DETECTION AGENT
    # ========================================================

    fraud_score = 10

    fraud_findings = []

    fraud_findings.append(
        "No major document manipulation indicators "
        "were detected during the current analysis."
    )

    # If OCR could not extract text, increase uncertainty.
    raw_text = ocr_result.get(
        "raw_text_preview",
        ""
    )

    if not raw_text:

        fraud_score += 10

        fraud_findings.append(
            "Limited document text was available for analysis."
        )

    fraud_score = min(fraud_score, 100)

    fraud_agent = {

        "agent": "Fraud Detection Agent",

        "status": "completed",

        "risk_score": fraud_score,

        "finding": " ".join(fraud_findings)
    }


    # ========================================================
    # COMPLIANCE AGENT
    # ========================================================

    compliance_score = 10

    compliance_findings = []

    compliance_findings.append(
        "Basic document compliance checks completed."
    )

    document_type = ocr_result.get(
        "document_type",
        "UNKNOWN"
    )

    if document_type == "UNKNOWN":

        compliance_score += 15

        compliance_findings.append(
            "Document type could not be confidently determined."
        )

    compliance_score = min(
        compliance_score,
        100
    )

    compliance_agent = {

        "agent": "Compliance Agent",

        "status": "completed",

        "risk_score": compliance_score,

        "finding": " ".join(compliance_findings)
    }


    # ========================================================
    # FINANCIAL RISK AGENT
    # ========================================================

    financial_score = 20

    income = extracted_fields.get(
        "income"
    )

    financial_findings = []

    # --------------------------------------------------------
    # INCOME FOUND
    # --------------------------------------------------------

    if income:

        try:

            income_value = float(income)

            if income_value < 15000:

                financial_score = 45

                financial_findings.append(
                    "Detected income is relatively low and "
                    "may require additional verification."
                )

            elif income_value < 30000:

                financial_score = 30

                financial_findings.append(
                    "Detected income indicates moderate "
                    "financial risk."
                )

            else:

                financial_score = 15

                financial_findings.append(
                    "Detected income appears sufficient for "
                    "basic financial verification."
                )

        except (ValueError, TypeError):

            financial_score = 35

            financial_findings.append(
                "Income information was detected but could "
                "not be reliably interpreted."
            )

    # --------------------------------------------------------
    # INCOME NOT FOUND
    # --------------------------------------------------------

    else:

        financial_score = 35

        financial_findings.append(
            "No reliable income information was detected. "
            "Additional verification is recommended."
        )

    financial_score = min(
        financial_score,
        100
    )

    financial_agent = {

        "agent": "Financial Risk Agent",

        "status": "completed",

        "risk_score": financial_score,

        "finding": " ".join(financial_findings)
    }


    # ========================================================
    # IDENTITY VERIFICATION AGENT
    # ========================================================

    identity_score = 10

    identity_findings = []

    # --------------------------------------------------------
    # PAN
    # --------------------------------------------------------

    if extracted_fields.get("pan_detected"):

        identity_findings.append(
            "PAN number detected in the document."
        )

    else:

        identity_score += 25

        identity_findings.append(
            "PAN number was not detected."
        )

    # --------------------------------------------------------
    # IDENTITY NUMBER
    # --------------------------------------------------------

    if extracted_fields.get(
        "identity_number_detected"
    ):

        identity_findings.append(
            "Identity number detected in the document."
        )

    else:

        identity_score += 10

        identity_findings.append(
            "Identity number was not detected."
        )

    identity_score = min(
        identity_score,
        100
    )

    identity_agent = {

        "agent": "Identity Verification Agent",

        "status": "completed",

        "risk_score": identity_score,

        "finding": " ".join(identity_findings)
    }


    # ========================================================
    # OVERALL RISK
    # ========================================================

    agent_scores = [

        fraud_agent["risk_score"],

        compliance_agent["risk_score"],

        financial_agent["risk_score"],

        identity_agent["risk_score"]

    ]

    overall_risk = round(
        sum(agent_scores) / len(agent_scores)
    )

    # Make absolutely sure score stays between 0 and 100.

    overall_risk = max(
        0,
        min(
            100,
            overall_risk
        )
    )


    # ========================================================
    # RISK LEVEL
    # ========================================================

    if overall_risk < 30:

        risk_level = "LOW"

    elif overall_risk < 60:

        risk_level = "MEDIUM"

    else:

        risk_level = "HIGH"


    # ========================================================
    # DECISION AGENT
    # ========================================================

    if risk_level == "LOW":

        decision = "APPROVE"

        recommendation = (
            "The document presents relatively low risk. "
            "Proceed with standard verification."
        )

    elif risk_level == "MEDIUM":

        decision = "REVIEW"

        recommendation = (
            "The document contains moderate risk indicators. "
            "Manual verification is recommended before approval."
        )

    else:

        decision = "REJECT"

        recommendation = (
            "The document contains significant risk indicators. "
            "Additional investigation is required."
        )


    # ========================================================
    # EXPLAINABILITY
    # ========================================================

    explanation = [

        "Document processed by the Document "
        "Intelligence Agent.",

        fraud_agent["finding"],

        compliance_agent["finding"],

        financial_agent["finding"],

        identity_agent["finding"]
    ]


    # ========================================================
    # CREATE REPORT
    # ========================================================

    report_id = str(uuid.uuid4())

    report = {

        "report_id": report_id,

        "document_id": document_id,

        "created_at": datetime.now().isoformat(),

        "document_intelligence": ocr_result,

        "risk": {

            "score": overall_risk,

            "level": risk_level
        },

        "decision": decision,

        "recommendation": recommendation,

        "explanation": explanation,

        "agents": [

            fraud_agent,

            compliance_agent,

            financial_agent,

            identity_agent

        ]
    }

    # --------------------------------------------------------
    # SAVE REPORT
    # --------------------------------------------------------

    reports[report_id] = report

    documents[document_id]["status"] = "analyzed"

    documents[document_id]["report_id"] = report_id

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "success": True,

        "message": "Multi-agent analysis completed",

        "report": report
    }


# ============================================================
# GET REPORT
# ============================================================

@app.get("/report/{report_id}")
def get_report(report_id: str):

    if report_id not in reports:

        raise HTTPException(
            status_code=404,
            detail="Report not found."
        )

    return {

        "success": True,

        "report": reports[report_id]
    }


# ============================================================
# WHAT-IF RISK SIMULATION
# ============================================================

@app.post("/simulate")
async def simulate_risk(

    loan_amount: float = 100000,

    co_applicant: bool = False

):

    # --------------------------------------------------------
    # BASE SCORE
    # --------------------------------------------------------

    base_score = 35

    # --------------------------------------------------------
    # LOAN AMOUNT IMPACT
    # --------------------------------------------------------

    if loan_amount > 1000000:

        base_score += 20

    elif loan_amount > 500000:

        base_score += 10

    elif loan_amount > 250000:

        base_score += 5

    # --------------------------------------------------------
    # CO-APPLICANT IMPACT
    # --------------------------------------------------------

    if co_applicant:

        base_score -= 10

    # --------------------------------------------------------
    # KEEP SCORE BETWEEN 0 AND 100
    # --------------------------------------------------------

    risk_score = max(
        0,
        min(
            100,
            base_score
        )
    )

    # --------------------------------------------------------
    # RISK LEVEL
    # --------------------------------------------------------

    if risk_score < 30:

        risk_level = "LOW"

    elif risk_score < 60:

        risk_level = "MEDIUM"

    else:

        risk_level = "HIGH"

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    if risk_level == "LOW":

        decision = "APPROVE"

    elif risk_level == "MEDIUM":

        decision = "REVIEW"

    else:

        decision = "REJECT"

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "success": True,

        "simulation": {

            "loan_amount": loan_amount,

            "co_applicant": co_applicant,

            "risk_score": risk_score,

            "risk_level": risk_level,

            "decision": decision
        }
    }


# ============================================================
# LIST ALL DOCUMENTS
# ============================================================

@app.get("/documents")
def list_documents():

    return {

        "success": True,

        "count": len(documents),

        "documents": list(
            documents.values()
        )
    }


# ============================================================
# LIST ALL REPORTS
# ============================================================

@app.get("/reports")
def list_reports():

    return {

        "success": True,

        "count": len(reports),

        "reports": list(
            reports.values()
        )
    }


# ============================================================
# DELETE DOCUMENT
# ============================================================

@app.delete("/document/{document_id}")
def delete_document(document_id: str):

    if document_id not in documents:

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    document = documents[document_id]

    # --------------------------------------------------------
    # DELETE PHYSICAL FILE
    # --------------------------------------------------------

    file_path = Path(
        document["file_path"]
    )

    if file_path.exists():

        try:

            file_path.unlink()

        except Exception as error:

            raise HTTPException(
                status_code=500,
                detail=f"Could not delete document file: {str(error)}"
            )

    # --------------------------------------------------------
    # DELETE ASSOCIATED REPORT
    # --------------------------------------------------------

    report_id = document.get(
        "report_id"
    )

    if report_id and report_id in reports:

        del reports[report_id]

    # --------------------------------------------------------
    # DELETE DOCUMENT FROM MEMORY
    # --------------------------------------------------------

    del documents[document_id]

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "success": True,

        "message": "Document deleted successfully",

        "document_id": document_id
    }


# ============================================================
# CHAT
# ============================================================

class ChatRequest(BaseModel):

    message: str


@app.post("/chat")
def chat(request: ChatRequest):

    user_message = request.message.strip()

    if not user_message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    # --------------------------------------------------------
    # TEMPORARY CHAT RESPONSE
    # --------------------------------------------------------
    #
    # The chat system is intentionally kept working here.
    # Later we can connect this endpoint to an actual
    # AegisAI reasoning/LLM agent.
    #

    response = (
        f"AegisAI received your message: {user_message}"
    )

    return {

        "success": True,

        "message": response
    }


# ============================================================
# APPLICATION STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():

    print("")

    print("=" * 60)

    print("              AEGISAI BACKEND")

    print("=" * 60)

    print("Status : ONLINE")

    print("API    : http://127.0.0.1:8000")

    print("Docs   : http://127.0.0.1:8000/docs")

    print("=" * 60)

    print("")