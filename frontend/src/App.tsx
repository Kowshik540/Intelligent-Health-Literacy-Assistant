import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, FileText, ThumbsUp, ThumbsDown, Loader2, X, Check, Plus, Mic, MicOff, Volume2, VolumeX } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import axios from 'axios'
import './App.css'

const API = 'http://localhost:8003/api/v1'

interface Citation {
  source: string
  page_number: string
  section_header: string
  relevance_score: number
  text_snippet: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  clinical_answer?: string
  citations?: Citation[]
  is_emergency?: boolean
  pii_detected?: boolean
  message_id?: string
  sources?: string[]
}

// Remove citation brackets from display text
function cleanAnswer(text: string): string {
  return text.replace(/\[Source:[^\]]*\]/g, '').replace(/\n{3,}/g, '\n\n').trim()
}

// Format document names to be human-readable
function formatSource(source: string): string {
  return source
    .replace(/_/g, ' ')
    .replace('.txt', '')
    .replace('.pdf', '')
    .replace(/-eng$/, '')
    .replace(/^9789\d+\s*/i, 'WHO Guidelines ')
    .replace(/WHO-UCN-NCD-[\d.]+/i, 'WHO Diabetes Guidelines')
    .replace(/Vol(\d)/i, 'Vol. $1')
    .trim()
}

// Deduplicate citations by source+section
function dedupeCitations(citations: Citation[]): Citation[] {
  const seen = new Set<string>()
  return citations.filter(c => {
    const key = `${c.source}-${c.section_header}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

// Check if browser supports Speech Recognition
const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [citations, setCitations] = useState<Citation[]>([])
  const [showClinical, setShowClinical] = useState<Record<number, boolean>>({})
  const [feedbackGiven, setFeedbackGiven] = useState<Record<string, string>>({})
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [emergencyAlert, setEmergencyAlert] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Initialize Speech Recognition
  useEffect(() => {
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition()
      recognition.continuous = false
      recognition.interimResults = true
      recognition.lang = 'en-US'

      recognition.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join('')
        setInput(transcript)

        // Auto-send when speech ends (final result)
        if (event.results[0].isFinal) {
          setIsListening(false)
        }
      }

      recognition.onerror = () => {
        setIsListening(false)
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = recognition
    }
  }, [])

  const toggleListening = useCallback(() => {
    if (!recognitionRef.current) return

    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      setInput('')
      recognitionRef.current.start()
      setIsListening(true)
    }
  }, [isListening])

  // Text-to-Speech: read answer aloud
  const speakText = useCallback((text: string) => {
    if (isSpeaking) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
      return
    }

    const cleaned = cleanAnswer(text)
      .replace(/[#*_`]/g, '') // remove markdown chars
      .replace(/\n+/g, '. ')  // newlines to pauses

    const utterance = new SpeechSynthesisUtterance(cleaned)
    utterance.rate = 0.9
    utterance.pitch = 1
    utterance.lang = 'en-US'

    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    setIsSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }, [isSpeaking])

  // Stop speaking when component unmounts
  useEffect(() => {
    return () => { window.speechSynthesis.cancel() }
  }, [])

  const sendMessage = async (text?: string) => {
    const msg = text || input
    if (!msg.trim() || loading) return

    const userMsg: Message = { role: 'user', content: msg }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await axios.post(`${API}/chat/`, { message: msg }, { timeout: 300000 })
      const data = res.data
      const assistantMsg: Message = {
        role: 'assistant',
        content: data.simplified_answer,
        clinical_answer: data.clinical_answer,
        citations: data.citations,
        is_emergency: data.is_emergency,
        pii_detected: data.pii_detected,
        message_id: data.message?.id,
        sources: data.sources,
      }
      setMessages(prev => [...prev, assistantMsg])
      setCitations(dedupeCitations(data.citations || []))
      if (data.is_emergency) setEmergencyAlert(true)
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: err.code === 'ECONNABORTED'
          ? 'Request timed out. Please try again.'
          : 'Could not connect to server. Make sure backend is running.',
      }])
    }
    setLoading(false)
  }

  const submitFeedback = async (messageId: string, isPositive: boolean, question: string, answer: string) => {
    try {
      await axios.post(`${API}/feedback/`, {
        message_id: messageId,
        conversation_id: 'demo',
        is_positive: isPositive,
        original_question: question,
        ai_answer: answer,
      })
      setFeedbackGiven(prev => ({ ...prev, [messageId]: isPositive ? 'up' : 'down' }))
    } catch {}
  }

  const toggleClinical = (idx: number) => {
    setShowClinical(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <button className="icon-btn" onClick={() => { setMessages([]); setCitations([]); window.speechSynthesis.cancel(); setIsSpeaking(false) }}>
            <Plus size={18} />
          </button>
          <span className="app-title">Health Literacy Assistant</span>
        </div>
        <div className="header-right">
          {isSpeaking && (
            <button className="icon-btn speaking-btn" onClick={() => { window.speechSynthesis.cancel(); setIsSpeaking(false) }} title="Stop speaking">
              <VolumeX size={18} />
            </button>
          )}
          <button className="icon-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <FileText size={18} />
          </button>
        </div>
      </header>

      <div className="main-layout">
        <div className="chat-area">
          <div className="messages">
            {messages.length === 0 && (
              <div className="welcome">
                <h1>What can I help you with?</h1>
                <p>Ask any health question by typing or using voice. Answers are from verified WHO medical documents only.</p>
                <div className="suggestions">
                  {[
                    "What are the symptoms of diabetes?",
                    "How is hypertension treated?",
                    "I have high fever what should I do?",
                    "What causes headaches?",
                  ].map((q, i) => (
                    <button key={i} onClick={() => sendMessage(q)}>{q}</button>
                  ))}
                </div>
                {SpeechRecognition && (
                  <p className="voice-hint">Click the microphone icon to ask using your voice</p>
                )}
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`msg ${msg.role}`}>
                {msg.role === 'assistant' && <div className="msg-icon">H</div>}
                <div className="msg-content">
                  {msg.pii_detected && (
                    <div className="pii-bar">Personal info removed before processing.</div>
                  )}
                  {msg.is_emergency && (
                    <div className="emergency-bar">Emergency detected — contact emergency services (112/108) immediately.</div>
                  )}

                  {msg.role === 'assistant' && msg.clinical_answer && !msg.is_emergency ? (
                    <>
                      <div className="msg-text">
                        <ReactMarkdown>
                          {cleanAnswer(showClinical[i] ? msg.clinical_answer! : msg.content)}
                        </ReactMarkdown>
                      </div>
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="inline-sources">
                          {dedupeCitations(msg.citations).slice(0, 2).map((c, j) => (
                            <span key={j} className="source-chip">
                              {formatSource(c.source)} · Page {c.page_number}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="msg-actions">
                        <div className="toggle-group">
                          <button className={!showClinical[i] ? 'active' : ''} onClick={() => toggleClinical(i)}>Simple</button>
                          <button className={showClinical[i] ? 'active' : ''} onClick={() => toggleClinical(i)}>Clinical</button>
                        </div>
                        <div className="feedback-group">
                          <button className="speak-btn" onClick={() => speakText(showClinical[i] ? msg.clinical_answer! : msg.content)} title="Read aloud">
                            <Volume2 size={14} />
                          </button>
                          {msg.message_id && (
                            <>
                              {feedbackGiven[msg.message_id] ? (
                                <span className="fb-done"><Check size={12} /> Thanks</span>
                              ) : (
                                <>
                                  <button onClick={() => submitFeedback(msg.message_id!, true, messages[i-1]?.content || '', msg.content)}><ThumbsUp size={14} /></button>
                                  <button onClick={() => submitFeedback(msg.message_id!, false, messages[i-1]?.content || '', msg.content)}><ThumbsDown size={14} /></button>
                                </>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="msg-text">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="msg assistant">
                <div className="msg-icon">H</div>
                <div className="msg-content">
                  <div className="typing"><Loader2 size={14} className="spin" /> Searching documents...</div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="input-area">
            <div className="input-box">
              {SpeechRecognition && (
                <button
                  className={`voice-btn ${isListening ? 'listening' : ''}`}
                  onClick={toggleListening}
                  disabled={loading}
                  title={isListening ? 'Stop listening' : 'Start voice input'}
                >
                  {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
              )}
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage()}
                placeholder={isListening ? 'Listening...' : 'Message Health Assistant...'}
                disabled={loading}
                className={isListening ? 'listening-input' : ''}
              />
              <button onClick={() => sendMessage()} disabled={loading || !input.trim()}>
                <Send size={16} />
              </button>
            </div>
            {isListening && (
              <div className="listening-indicator">
                <span className="pulse-dot"></span> Listening — speak your health question...
              </div>
            )}
          </div>
        </div>

        {sidebarOpen && (
          <div className="sidebar">
            <div className="sidebar-top">
              <span>Sources</span>
              <button onClick={() => setSidebarOpen(false)}><X size={16} /></button>
            </div>
            <div className="sidebar-content">
              {citations.length > 0 ? (
                citations.map((c, i) => (
                  <div key={i} className="cite-card">
                    <div className="cite-header">
                      <span className="cite-file">{formatSource(c.source)}</span>
                      <span className={`cite-score ${c.relevance_score >= 0.5 ? 'high' : ''}`}>{(c.relevance_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="cite-meta">Page {c.page_number} · {c.section_header.replace(/\(cid:\d+\)/g, '').replace(/\s+/g, ' ').trim().slice(0, 40)}</div>
                    <div className="cite-text">{c.text_snippet.replace(/\(cid:\d+\)/g, '').replace(/\s+/g, ' ').slice(0, 150)}</div>
                  </div>
                ))
              ) : (
                <div className="sidebar-empty"><p>Source citations appear here when you ask a question.</p></div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Emergency Alert Modal */}
      {emergencyAlert && (
        <div className="emergency-overlay" onClick={() => setEmergencyAlert(false)}>
          <div className="emergency-modal" onClick={e => e.stopPropagation()}>
            <div className="emergency-modal-icon"></div>
            <h2>Medical Emergency Detected</h2>
            <p>Based on your message, you may need immediate medical help.</p>
            <div className="emergency-numbers">
              <a href="tel:112" className="emergency-call">
                <span className="call-number">112</span>
                <span className="call-label">Emergency (India)</span>
              </a>
              <a href="tel:108" className="emergency-call ambulance">
                <span className="call-number">108</span>
                <span className="call-label">Ambulance</span>
              </a>
              <a href="tel:9152987821" className="emergency-call helpline">
                <span className="call-number">9152987821</span>
                <span className="call-label">iCall Mental Health</span>
              </a>
            </div>
            <p className="emergency-warning">Do NOT rely on any AI system during a medical emergency.</p>
            <button className="emergency-close" onClick={() => setEmergencyAlert(false)}>I understand</button>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
