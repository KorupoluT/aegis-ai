
import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'

const API_URL = (
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

const LANGUAGE_OPTIONS = [
  { label: 'English', value: 'en-IN' },
  { label: 'తెలుగు', value: 'te-IN' },
  { label: 'हिन्दी', value: 'hi-IN' },
]

// Safely convert backend values into text React can render.
const toDisplayText = (value, fallback = '') => {
  if (value == null) return fallback

  if (
    typeof value === 'string' ||
    typeof value === 'number'
  ) {
    return String(value)
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }

  if (Array.isArray(value)) {
    return value
      .map((item) => toDisplayText(item))
      .filter(Boolean)
      .join('\n')
  }

  if (typeof value === 'object') {
    const preferred =
      value.explanation ??
      value.message ??
      value.finding ??
      value.name ??
      value.agent_name

    if (preferred != null && preferred !== value) {
      return toDisplayText(preferred, fallback)
    }

    return JSON.stringify(value, null, 2)
  }

  return fallback
}

const cleanTextForSpeech = (text) =>
  String(text ?? '')
    .replace(/[*_`#]/g, '')
    .replace(/\s+/g, ' ')
    .trim()

const getLanguagePrefix = (language) => {
  if (language?.startsWith('te')) return 'te'
  if (language?.startsWith('hi')) return 'hi'
  return 'en'
}

const chooseVoice = (voices, language) => {
  const prefix = getLanguagePrefix(language)

  return (
    voices.find(
      (voice) =>
        voice.lang?.toLowerCase() === language?.toLowerCase()
    ) ||
    voices.find((voice) =>
      voice.lang?.toLowerCase().startsWith(prefix)
    ) ||
    null
  )
}

const getRiskClass = (level) => {
  const normalized = String(level ?? '').toLowerCase()

  if (['high', 'critical', 'severe'].includes(normalized)) {
    return 'high'
  }

  if (['medium', 'moderate'].includes(normalized)) {
    return 'medium'
  }

  if (['low', 'safe'].includes(normalized)) {
    return 'low'
  }

  return 'review'
}

function App() {
  const [activePage, setActivePage] = useState('assistant')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [document, setDocument] = useState(null)
  const [report, setReport] = useState(null)
  const [documentError, setDocumentError] = useState('')
  const [explanationLanguage, setExplanationLanguage] =
    useState('english')
  const [voiceLanguage, setVoiceLanguage] = useState('en-IN')
  const [isListening, setIsListening] = useState(false)
  const [speakReplies, setSpeakReplies] = useState(true)
  const [voiceError, setVoiceError] = useState('')
  const [chatError, setChatError] = useState('')

  const recognitionRef = useRef(null)
  const voicesRef = useRef([])
  const mountedRef = useRef(true)
  const audioRef = useRef(null)
  const audioUrlRef = useRef(null)

  useEffect(() => {
    mountedRef.current = true

    const loadVoices = () => {
      if ('speechSynthesis' in window) {
        voicesRef.current = window.speechSynthesis.getVoices()
      }
    }

    loadVoices()

    if ('speechSynthesis' in window) {
      window.speechSynthesis.addEventListener(
        'voiceschanged',
        loadVoices
      )
    }

    return () => {
      mountedRef.current = false

      if ('speechSynthesis' in window) {
        window.speechSynthesis.removeEventListener(
          'voiceschanged',
          loadVoices
        )
        window.speechSynthesis.cancel()
      }

      recognitionRef.current?.stop()

      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }

      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current)
        audioUrlRef.current = null
      }
    }
  }, [])

  const speakText = useCallback(
    async (text, language = voiceLanguage) => {
      const cleanText = cleanTextForSpeech(text)
      if (!cleanText) return

      try {
        const response = await fetch(`${API_URL}/tts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: cleanText,
            language,
          }),
        })

        if (!response.ok) {
          throw new Error(`Speech request failed (${response.status})`)
        }

        const audioBlob = await response.blob()

        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current)
        }

        const audioUrl = URL.createObjectURL(audioBlob)
        audioUrlRef.current = audioUrl

        if (audioRef.current) {
          audioRef.current.pause()
        }

        const audio = new Audio(audioUrl)
        audioRef.current = audio
        await audio.play()
      } catch (error) {
        console.error('Text-to-speech error:', error)

        // Browser speech is a fallback if backend TTS is unavailable.
        if ('speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(cleanText)
          utterance.lang = language
          const voice = chooseVoice(voicesRef.current, language)

          if (voice) utterance.voice = voice

          window.speechSynthesis.cancel()
          window.speechSynthesis.speak(utterance)
        }
      }
    },
    [voiceLanguage]
  )

  const startListening = () => {
    setVoiceError('')

    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition

    if (!SpeechRecognition) {
      setVoiceError(
        'Voice input is not supported in this browser. Try Chrome.'
      )
      return
    }

    if (isListening) {
      recognitionRef.current?.stop()
      setIsListening(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = voiceLanguage
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onstart = () => {
      if (mountedRef.current) setIsListening(true)
    }

    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript

      if (transcript && mountedRef.current) {
        setMessage((previous) =>
          previous ? `${previous} ${transcript}` : transcript
        )
      }
    }

    recognition.onerror = (event) => {
      if (mountedRef.current) {
        setVoiceError(
          event.error === 'not-allowed'
            ? 'Microphone access was denied. Allow microphone access in your browser.'
            : `Voice input failed: ${event.error}`
        )
      }
    }

    recognition.onend = () => {
      if (mountedRef.current) setIsListening(false)
    }

    recognitionRef.current = recognition

    try {
      recognition.start()
    } catch (error) {
      setIsListening(false)
      setVoiceError(error.message || 'Could not start voice input.')
    }
  }

  const sendMessage = async () => {
    const submittedMessage = message.trim()
    if (!submittedMessage || loading) return

    setChatError('')
    setLoading(true)
    setMessage('')

    setMessages((previous) => [
      ...previous,
      { role: 'user', content: submittedMessage },
    ])

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: submittedMessage,
          document_id:
            document?.id ?? document?.document_id ?? null,
        }),
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          toDisplayText(
            data.detail ?? data.error,
            `Request failed (${response.status})`
          )
        )
      }

      const rawReply =
        data.message ??
        data.response ??
        data.reply ??
        data.answer ??
        data

      const reply = toDisplayText(rawReply)

      if (!reply) {
        throw new Error('The backend returned an empty response.')
      }

      setMessages((previous) => [
        ...previous,
        { role: 'assistant', content: reply },
      ])

      if (speakReplies) {
        speakText(reply, voiceLanguage)
      }
    } catch (error) {
      setChatError(
        error.message || 'Could not reach the AegisAI backend.'
      )
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
    setMessages([])
    setMessage('')
    setChatError('')
    setVoiceError('')
  }

  const handleFileChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setDocumentError('')
    setReport(null)

    if (!/\.(pdf|jpe?g|png)$/i.test(file.name)) {
      setSelectedFile(null)
      setDocumentError('Please select a PDF, JPG, or PNG file.')
      event.target.value = ''
      return
    }

    setSelectedFile(file)
  }

  const analyzeDocument = async (documentId) => {
    setAnalyzing(true)
    setDocumentError('')

    try {
      const response = await fetch(
        `${API_URL}/analyze/${encodeURIComponent(documentId)}`,
        { method: 'POST' }
      )

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          toDisplayText(
            data.detail ?? data.error,
            `Analysis failed (${response.status})`
          )
        )
      }

      const nextReport = data.report ?? data
      setReport(nextReport)
    } catch (error) {
      setDocumentError(
        error.message || 'Could not analyze the document.'
      )
    } finally {
      setAnalyzing(false)
    }
  }

  const uploadDocument = async () => {
    if (!selectedFile || uploading || analyzing) return

    setUploading(true)
    setDocumentError('')
    setReport(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          toDisplayText(
            data.detail ?? data.error,
            `Upload failed (${response.status})`
          )
        )
      }

      const uploadedDocument = data.document ?? data
      setDocument(uploadedDocument)

      const documentId =
        uploadedDocument.id ?? uploadedDocument.document_id

      if (documentId == null) {
        throw new Error(
          'Upload succeeded, but the response did not include a document ID.'
        )
      }

      await analyzeDocument(documentId)
    } catch (error) {
      setDocumentError(
        error.message || 'Could not upload the document.'
      )
    } finally {
      setUploading(false)
    }
  }

  const getSelectedAIExplanation = () => {
    const explanations = report?.ai_explanations

    if (typeof explanations === 'string') {
      return explanationLanguage === 'english' ? explanations : ''
    }

    if (!explanations || typeof explanations !== 'object') {
      return ''
    }

    const selected =
      explanationLanguage === 'telugu'
        ? explanations.telugu ?? explanations.te
        : explanations.english ?? explanations.en

    return toDisplayText(selected)
  }

  const getSelectedExplanationStatus = () => {
    const explanations = report?.ai_explanations

    if (!explanations || typeof explanations !== 'object') {
      return 'ai'
    }

    const selected =
      explanationLanguage === 'telugu'
        ? explanations.telugu ?? explanations.te
        : explanations.english ?? explanations.en

    return selected?.status === 'fallback' ? 'fallback' : 'ai'
  }

  const renderAssistant = () => (
    <section className="assistant-container">
      <div className="page-heading">
        <div>
          <p className="eyebrow">INTELLIGENT CONVERSATION</p>
          <h3>AI Assistant</h3>
          <p>
            Ask questions, understand documents, and get help from AegisAI.
          </p>
        </div>
      </div>

      <div className="chat-card">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <div className="upload-icon">✦</div>
              <h3>How can I help you today?</h3>
              <p>
                Ask a question or upload a document in the Documents section
                to begin your analysis.
              </p>
            </div>
          )}

          {messages.map((item, index) => (
            <div
              className={`message ${item.role === 'user' ? 'user-message' : 'assistant-message'}`}
              key={`${item.role}-${index}`}
            >
              <div className="message-avatar">
                {item.role === 'user' ? 'Y' : 'A'}
              </div>
              <div className="message-body">
                <span className="message-role">
                  {item.role === 'user' ? 'You' : 'AegisAI'}
                </span>
                <p>{toDisplayText(item.content)}</p>

                {item.role === 'assistant' && (
                  <button
                    type="button"
                    className="read-aloud-button"
                    onClick={() =>
                      speakText(
                        toDisplayText(item.content),
                        voiceLanguage
                      )
                    }
                  >
                    🔊 Read aloud
                  </button>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant-message">
              <div className="message-avatar">A</div>
              <div className="message-body">
                <span className="message-role">AegisAI</span>
                <p>Thinking...</p>
              </div>
            </div>
          )}
        </div>

        {chatError && (
          <div className="error-message" role="alert">
            {chatError}
          </div>
        )}

        {voiceError && (
          <div className="error-message" role="alert">
            {voiceError}
          </div>
        )}

        <div className="chat-controls">
          <div className="chat-options">
            <label>
              <span>Voice language</span>
              <select
                value={voiceLanguage}
                onChange={(event) => setVoiceLanguage(event.target.value)}
              >
                {LANGUAGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="toggle-option">
              <input
                type="checkbox"
                checked={speakReplies}
                onChange={(event) => setSpeakReplies(event.target.checked)}
              />
              Read replies aloud
            </label>

            <button
              type="button"
              className="new-chat"
              onClick={startNewChat}
            >
              New chat
            </button>
          </div>

          <div className="chat-input-row">
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message AegisAI..."
              rows={2}
              aria-label="Message AegisAI"
            />

            <button
              type="button"
              className={`voice-button ${isListening ? 'active' : ''}`}
              onClick={startListening}
              aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
              title={isListening ? 'Stop listening' : 'Speak'}
            >
              {isListening ? '■' : '🎙'}
            </button>

            <button
              type="button"
              className="analyze-button"
              onClick={sendMessage}
              disabled={!message.trim() || loading}
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
          </div>
          <p className="input-hint">
            Press Enter to send. Shift + Enter for a new line.
          </p>
        </div>
      </div>
    </section>
  )

  const renderDocuments = () => {
    const aiExplanation = getSelectedAIExplanation()
    const explanationStatus = getSelectedExplanationStatus()

    const agents = Array.isArray(report?.agents)
      ? report.agents
      : []

    const additionalFindings = Array.isArray(report?.explanation)
      ? report.explanation
      : report?.explanation
        ? [report.explanation]
        : []

    const riskLevel =
      report?.risk?.level ?? report?.risk_level ?? 'REVIEW'

    const riskScore =
      report?.risk?.score ?? report?.risk_score ?? '—'

    return (
      <section className="documents-container">
        <div className="page-heading">
          <div>
            <p className="eyebrow">DOCUMENT INTELLIGENCE</p>
            <h3>Risk Analysis</h3>
            <p>
              Upload a document and let AegisAI analyze its risk profile.
            </p>
          </div>
        </div>

        <div className="upload-card">
          <div className="upload-icon">📄</div>
          <h3>Upload a document</h3>
          <p>Supported formats: PDF, JPG and PNG</p>

          <label className="file-picker">
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              onChange={handleFileChange}
            />
            <span>Choose document</span>
          </label>

          {selectedFile && (
            <div className="selected-file">
              <span>📎</span>
              <div>
                <strong>{selectedFile.name}</strong>
                <small>
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </small>
              </div>
            </div>
          )}

          {documentError && (
            <div className="error-message" role="alert">
              {documentError}
            </div>
          )}

          <button
            type="button"
            className="analyze-button"
            onClick={uploadDocument}
            disabled={!selectedFile || uploading || analyzing}
          >
            {uploading
              ? 'Uploading...'
              : analyzing
                ? 'Analyzing...'
                : 'Upload & Analyze'}
          </button>
        </div>

        {document && (
          <div className="document-info-card">
            <div>
              <span className="card-label">DOCUMENT</span>
              <h4>
                {toDisplayText(
                  document.original_filename ?? document.filename,
                  'Uploaded document'
                )}
              </h4>
            </div>
            <span className="document-status">
              {toDisplayText(document.status, 'Uploaded')}
            </span>
          </div>
        )}

        {report && (
          <div className="report">
            <div className="report-header">
              <div>
                <span className="card-label">AEGISAI RISK REPORT</span>
                <h3>Analysis complete</h3>
              </div>
              <div className={`risk-badge ${getRiskClass(riskLevel)}`}>
                {toDisplayText(riskLevel, 'REVIEW')}
              </div>
            </div>

            <div className="risk-overview">
              <div className="score-card">
                <span>Overall Risk Score</span>
                <strong>{toDisplayText(riskScore, '—')}</strong>
                <small>out of 100</small>
              </div>

              <div className="decision-card">
                <span>Decision</span>
                <strong>
                  {toDisplayText(report.decision, 'MANUAL_REVIEW')}
                </strong>
                <small>
                  {toDisplayText(
                    report.recommendation,
                    'Review the findings before making a decision.'
                  )}
                </small>
              </div>
            </div>

            <h4 className="report-section-title">Agent Findings</h4>

            <div className="agent-grid">
              {agents.map((agent, index) => {
                const score = Number(agent?.risk_score) || 0
                const safeScore = Math.max(0, Math.min(100, score))

                const agentName = toDisplayText(
                  agent?.agent,
                  `Agent ${index + 1}`
                )

                const finding = toDisplayText(
                  agent?.finding ??
                    agent?.explanation ??
                    agent?.status,
                  'No finding provided.'
                )

                return (
                  <div
                    className="agent-card"
                    key={`${agentName}-${index}`}
                  >
                    <div className="agent-card-top">
                      <span>{agentName}</span>
                      <strong>{score}</strong>
                    </div>
                    <div className="agent-bar">
                      <div style={{ width: `${safeScore}%` }} />
                    </div>
                    <p>{finding}</p>
                  </div>
                )
              })}
            </div>

            <div className="ai-explanation-section">
              <div className="ai-explanation-heading">
                <div>
                  <h4 className="report-section-title">AI Explanation</h4>
                  <p>
                    Understand the report in your preferred language.
                  </p>
                </div>

                <div
                  className="language-switcher"
                  role="group"
                  aria-label="Explanation language"
                >
                  <button
                    type="button"
                    className={
                      explanationLanguage === 'english' ? 'active' : ''
                    }
                    onClick={() => setExplanationLanguage('english')}
                    aria-pressed={explanationLanguage === 'english'}
                  >
                    English
                  </button>
                  <button
                    type="button"
                    className={
                      explanationLanguage === 'telugu' ? 'active' : ''
                    }
                    onClick={() => setExplanationLanguage('telugu')}
                    aria-pressed={explanationLanguage === 'telugu'}
                  >
                    తెలుగు
                  </button>
                </div>
              </div>

              {aiExplanation ? (
                <div className="ai-explanation-card" aria-live="polite">
                  {explanationStatus === 'fallback' && (
                    <p className="explanation-note">
                      AI service fallback explanation
                    </p>
                  )}
                  <p className="ai-explanation-text">
                    {aiExplanation}
                  </p>
                </div>
              ) : (
                <div className="ai-explanation-card" aria-live="polite">
                  <p>
                    {report.ai_explanations
                      ? explanationLanguage === 'telugu'
                        ? 'తెలుగు వివరణ అందుబాటులో లేదు. బ్యాకెండ్‌లో Telugu explanation విజయవంతంగా తిరిగి వస్తుందో చూడండి.'
                        : 'The English AI explanation is not available in this report. Check the backend response for ai_explanations.'
                      : 'AI explanations were not included in this report. Confirm that the backend returns ai_explanations for both English and Telugu.'}
                  </p>
                </div>
              )}
            </div>

            {additionalFindings.length > 0 && (
              <>
                <h4 className="report-section-title">
                  Additional Findings
                </h4>
                <div className="explanation">
                  {additionalFindings.map((item, index) => (
                    <div className="explanation-item" key={index}>
                      <span>{index + 1}</span>
                      <p>{toDisplayText(item)}</p>
                    </div>
                  ))}
                </div>
              </>
            )}

            <p className="disclaimer">
              This risk report is decision support, not proof of fraud or
              authenticity. Review the evidence and follow your
              organization’s procedures before making a decision.
            </p>
          </div>
        )}
      </section>
    )
  }

  const renderSettings = () => (
    <section className="simple-page">
      <p className="eyebrow">SYSTEM</p>
      <h3>Settings</h3>
      <p>AegisAI configuration options will be added here.</p>
      <p>
        Backend API: <code>{API_URL}</code>
      </p>
    </section>
  )

  const renderPage = () => {
    if (activePage === 'documents') return renderDocuments()
    if (activePage === 'settings') return renderSettings()
    return renderAssistant()
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">A</div>
          <div>
            <h1>AegisAI</h1>
            <span>Intelligent Assistant</span>
          </div>
        </div>

        <button
          type="button"
          className="new-chat"
          onClick={() => {
            startNewChat()
            setActivePage('assistant')
          }}
        >
          <span>＋</span> New conversation
        </button>

        <div className="sidebar-section">
          <p className="section-title">Workspace</p>

          <button
            type="button"
            className={`sidebar-item ${activePage === 'assistant' ? 'active' : ''}`}
            onClick={() => setActivePage('assistant')}
          >
            <span>◈</span> AI Assistant
          </button>

          <button
            type="button"
            className={`sidebar-item ${activePage === 'documents' ? 'active' : ''}`}
            onClick={() => setActivePage('documents')}
          >
            <span>▣</span> Documents
          </button>

          <button
            type="button"
            className={`sidebar-item ${activePage === 'settings' ? 'active' : ''}`}
            onClick={() => setActivePage('settings')}
          >
            <span>⚙</span> Settings
          </button>
        </div>

        <div className="sidebar-bottom">
          <div className="status">
            <span className="status-dot" /> System online
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">AEGISAI</p>
            <h2>
              {activePage === 'assistant'
                ? 'AI Command Center'
                : activePage === 'documents'
                  ? 'Document Intelligence'
                  : 'Settings'}
            </h2>
          </div>
          <div className="topbar-status">
            <span className="status-dot" /> Online
          </div>
        </header>

        {renderPage()}
      </main>
    </div>
  )
}

export default App
