import { useState } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  // ============================================================
  // GENERAL STATE
  // ============================================================

  const [activePage, setActivePage] = useState('assistant')

  // ============================================================
  // CHAT STATE
  // ============================================================

  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Hello! I’m AegisAI. How can I help you today?',
    },
  ])

  // ============================================================
  // DOCUMENT STATE
  // ============================================================

  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  const [document, setDocument] = useState(null)
  const [report, setReport] = useState(null)

  const [documentError, setDocumentError] = useState('')

  // ============================================================
  // CHAT
  // ============================================================

  const sendMessage = async () => {
    const trimmedMessage = message.trim()

    if (!trimmedMessage || loading) {
      return
    }

    setMessages((previous) => [
      ...previous,
      {
        role: 'user',
        text: trimmedMessage,
      },
    ])

    setMessage('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json',
        },

        body: JSON.stringify({
          message: trimmedMessage,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Backend request failed'
        )
      }

      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          text: data.message,
        },
      ])
    } catch (error) {
      console.error(error)

      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          text:
            'I could not connect to the AegisAI backend. Please make sure the FastAPI server is running on port 8000.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      sendMessage()
    }
  }

  const startNewChat = () => {
    setMessages([
      {
        role: 'assistant',
        text: 'Hello! I’m AegisAI. How can I help you today?',
      },
    ])

    setMessage('')
  }

  // ============================================================
  // FILE SELECTION
  // ============================================================

  const handleFileChange = (event) => {
    const file = event.target.files?.[0]

    setDocumentError('')
    setReport(null)
    setDocument(null)

    if (!file) {
      setSelectedFile(null)
      return
    }

    const allowedTypes = [
      'application/pdf',
      'image/jpeg',
      'image/png',
      'image/jpg',
    ]

    if (!allowedTypes.includes(file.type)) {
      setSelectedFile(null)

      setDocumentError(
        'Only PDF, JPG and PNG files are allowed.'
      )

      return
    }

    setSelectedFile(file)
  }

  // ============================================================
  // UPLOAD DOCUMENT
  // ============================================================

  const uploadDocument = async () => {
    if (!selectedFile || uploading || analyzing) {
      return
    }

    setUploading(true)
    setDocumentError('')
    setDocument(null)
    setReport(null)

    try {
      const formData = new FormData()

      formData.append('file', selectedFile)

      const response = await fetch(
        `${API_URL}/upload`,
        {
          method: 'POST',
          body: formData,
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Upload failed'
        )
      }

      setDocument(data.document)

      // Automatically start analysis
      await analyzeDocument(
        data.document.document_id
      )
    } catch (error) {
      console.error(error)

      setDocumentError(
        error.message ||
        'Could not upload the document.'
      )
    } finally {
      setUploading(false)
    }
  }

  // ============================================================
  // ANALYZE DOCUMENT
  // ============================================================

  const analyzeDocument = async (documentId) => {
    setAnalyzing(true)
    setDocumentError('')

    try {
      const response = await fetch(
        `${API_URL}/analyze/${documentId}`,
        {
          method: 'POST',
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Analysis failed'
        )
      }

      setReport(data.report)
    } catch (error) {
      console.error(error)

      setDocumentError(
        error.message ||
        'Could not analyze the document.'
      )
    } finally {
      setAnalyzing(false)
    }
  }

  // ============================================================
  // RISK LEVEL CLASS
  // ============================================================

  const getRiskClass = (level) => {
    if (level === 'LOW') {
      return 'risk-low'
    }

    if (level === 'MEDIUM') {
      return 'risk-medium'
    }

    if (level === 'HIGH') {
      return 'risk-high'
    }

    return ''
  }

  // ============================================================
  // ASSISTANT PAGE
  // ============================================================

  const renderAssistant = () => {
    return (
      <section className="chat-container">

        <div className="welcome">

          <div className="aegis-orb">
            <span>A</span>
          </div>

          <h3>
            Your intelligent AI workspace
          </h3>

          <p>
            Ask questions, analyze information, and interact
            with your AegisAI assistant.
          </p>

        </div>


        <div className="messages">

          {messages.map((item, index) => (

            <div
              key={index}
              className={
                `message-row ${
                  item.role === 'user'
                    ? 'user'
                    : 'assistant'
                }`
              }
            >

              <div className="message-avatar">
                {item.role === 'user'
                  ? 'You'
                  : 'A'}
              </div>

              <div className="message">

                <div className="message-role">
                  {item.role === 'user'
                    ? 'You'
                    : 'AegisAI'}
                </div>

                <div className="message-text">
                  {item.text}
                </div>

              </div>

            </div>

          ))}


          {loading && (

            <div className="message-row assistant">

              <div className="message-avatar">
                A
              </div>

              <div className="message">

                <div className="message-role">
                  AegisAI
                </div>

                <div className="message-text">
                  Thinking...
                </div>

              </div>

            </div>

          )}

        </div>


        <div className="input-area">

          <textarea
            value={message}
            onChange={(event) =>
              setMessage(event.target.value)
            }
            onKeyDown={handleKeyDown}
            placeholder="Ask AegisAI anything..."
            rows="1"
            disabled={loading}
          />

          <button
            className="send-button"
            onClick={sendMessage}
            disabled={loading}
          >
            ↑
          </button>

        </div>


        <p className="disclaimer">
          AegisAI can make mistakes.
          Verify important information.
        </p>

      </section>
    )
  }

  // ============================================================
  // DOCUMENT PAGE
  // ============================================================

  const renderDocuments = () => {
    return (
      <section className="documents-container">

        <div className="page-heading">

          <div>
            <p className="eyebrow">
              DOCUMENT INTELLIGENCE
            </p>

            <h3>
              Risk Analysis
            </h3>

            <p>
              Upload a document and let AegisAI analyze
              its risk profile.
            </p>
          </div>

        </div>


        {/* UPLOAD CARD */}

        <div className="upload-card">

          <div className="upload-icon">
            📄
          </div>

          <h3>
            Upload a document
          </h3>

          <p>
            Supported formats: PDF, JPG and PNG
          </p>


          <label className="file-picker">

            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={handleFileChange}
            />

            <span>
              Choose document
            </span>

          </label>


          {selectedFile && (

            <div className="selected-file">

              <span>
                📎
              </span>

              <div>

                <strong>
                  {selectedFile.name}
                </strong>

                <small>
                  {(
                    selectedFile.size /
                    1024 /
                    1024
                  ).toFixed(2)} MB
                </small>

              </div>

            </div>

          )}


          {documentError && (

            <div className="error-message">
              {documentError}
            </div>

          )}


          <button
            className="analyze-button"
            onClick={uploadDocument}
            disabled={
              !selectedFile ||
              uploading ||
              analyzing
            }
          >

            {uploading
              ? 'Uploading...'
              : analyzing
                ? 'Analyzing...'
                : 'Upload & Analyze'}

          </button>

        </div>


        {/* UPLOADED DOCUMENT */}

        {document && (

          <div className="document-info-card">

            <div>

              <span className="card-label">
                DOCUMENT
              </span>

              <h4>
                {document.original_filename}
              </h4>

            </div>

            <span className="document-status">
              {document.status}
            </span>

          </div>

        )}


        {/* REPORT */}

        {report && (

          <div className="report">

            <div className="report-header">

              <div>

                <span className="card-label">
                  AEGISAI RISK REPORT
                </span>

                <h3>
                  Analysis complete
                </h3>

              </div>

              <div
                className={
                  `risk-badge ${
                    getRiskClass(
                      report.risk.level
                    )
                  }`
                }
              >
                {report.risk.level}
              </div>

            </div>


            {/* SCORE */}

            <div className="risk-overview">

              <div className="score-card">

                <span>
                  Overall Risk Score
                </span>

                <strong>
                  {report.risk.score}
                </strong>

                <small>
                  out of 100
                </small>

              </div>


              <div className="decision-card">

                <span>
                  Decision
                </span>

                <strong>
                  {report.decision}
                </strong>

                <small>
                  {report.recommendation}
                </small>

              </div>

            </div>


            {/* AGENTS */}

            <h4 className="report-section-title">
              Agent Findings
            </h4>


            <div className="agent-grid">

              {report.agents.map(
                (agent, index) => (

                  <div
                    className="agent-card"
                    key={index}
                  >

                    <div className="agent-card-top">

                      <span>
                        {agent.agent}
                      </span>

                      <strong>
                        {agent.risk_score}
                      </strong>

                    </div>

                    <div className="agent-bar">

                      <div
                        style={{
                          width:
                            `${agent.risk_score}%`,
                        }}
                      />

                    </div>

                    <p>
                      {agent.finding}
                    </p>

                  </div>

                )
              )}

            </div>


            {/* EXPLANATION */}

            <h4 className="report-section-title">
              Explainability
            </h4>


            <div className="explanation">

              {report.explanation.map(
                (item, index) => (

                  <div
                    className="explanation-item"
                    key={index}
                  >
                    <span>
                      {index + 1}
                    </span>

                    <p>
                      {item}
                    </p>
                  </div>

                )
              )}

            </div>

          </div>

        )}

      </section>
    )
  }

  // ============================================================
  // SETTINGS PAGE
  // ============================================================

  const renderSettings = () => {
    return (
      <section className="simple-page">

        <p className="eyebrow">
          SYSTEM
        </p>

        <h3>
          Settings
        </h3>

        <p>
          AegisAI configuration options will be added here.
        </p>

      </section>
    )
  }

  // ============================================================
  // PAGE CONTENT
  // ============================================================

  const renderPage = () => {
    if (activePage === 'documents') {
      return renderDocuments()
    }

    if (activePage === 'settings') {
      return renderSettings()
    }

    return renderAssistant()
  }

  // ============================================================
  // MAIN UI
  // ============================================================

  return (
    <div className="app">

      {/* ======================================================
          SIDEBAR
      ====================================================== */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-icon">
            A
          </div>

          <div>

            <h1>
              AegisAI
            </h1>

            <span>
              Intelligent Assistant
            </span>

          </div>

        </div>


        <button
          className="new-chat"
          onClick={() => {
            startNewChat()
            setActivePage('assistant')
          }}
        >

          <span>
            ＋
          </span>

          New conversation

        </button>


        <div className="sidebar-section">

          <p className="section-title">
            Workspace
          </p>


          <button
            className={
              `sidebar-item ${
                activePage === 'assistant'
                  ? 'active'
                  : ''
              }`
            }
            onClick={() =>
              setActivePage('assistant')
            }
          >

            <span>
              ◈
            </span>

            AI Assistant

          </button>


          <button
            className={
              `sidebar-item ${
                activePage === 'documents'
                  ? 'active'
                  : ''
              }`
            }
            onClick={() =>
              setActivePage('documents')
            }
          >

            <span>
              ▣
            </span>

            Documents

          </button>


          <button
            className={
              `sidebar-item ${
                activePage === 'settings'
                  ? 'active'
                  : ''
              }`
            }
            onClick={() =>
              setActivePage('settings')
            }
          >

            <span>
              ⚙
            </span>

            Settings

          </button>

        </div>


        <div className="sidebar-bottom">

          <div className="status">

            <span className="status-dot"></span>

            System online

          </div>

        </div>

      </aside>


      {/* ======================================================
          MAIN
      ====================================================== */}

      <main className="main">

        <header className="topbar">

          <div>

            <p className="eyebrow">
              AEGISAI
            </p>

            <h2>
              {activePage === 'assistant'
                ? 'AI Command Center'
                : activePage === 'documents'
                  ? 'Document Intelligence'
                  : 'Settings'}
            </h2>

          </div>


          <div className="topbar-status">

            <span className="status-dot"></span>

            Online

          </div>

        </header>


        {renderPage()}

      </main>

    </div>
  )
}

export default App