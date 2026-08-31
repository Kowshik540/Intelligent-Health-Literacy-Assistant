import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, Menu, Mic, MicOff } from 'lucide-react'
import axios from 'axios'
import { Sidebar } from '../components/Sidebar'
import { ChatMessage } from '../components/ChatMessage'

const API = 'http://localhost:8000/api/v1'

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

const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

export function AssistantPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sourcePanelOpen, setSourcePanelOpen] = useState(true)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [citations, setCitations] = useState<Citation[]>([])
  const [feedbackGiven, setFeedbackGiven] = useState<Record<string, string>>({})
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [emergencyAlert, setEmergencyAlert] = useState(false)
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

  const speakText = useCallback((text: string) => {
    if (isSpeaking) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
      return
    }

    const cleaned = text.replace(/[#*_`]/g, '').replace(/\n+/g, '. ')

    const utterance = new SpeechSynthesisUtterance(cleaned)
    utterance.rate = 0.9
    utterance.pitch = 1
    utterance.lang = 'en-US'

    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    setIsSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }, [isSpeaking])

  useEffect(() => {
    return () => {
      window.speechSynthesis.cancel()
    }
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
      const conversationId = data.conversation_id || activeConversationId
      if (conversationId) setActiveConversationId(conversationId)

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
      setCitations(data.citations || [])
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

  const submitFeedback = async (messageId: string, isPositive: boolean) => {
    const messageIdx = messages.findIndex(m => m.message_id === messageId)
    const userQuestion = messageIdx > 0 ? messages[messageIdx - 1].content : ''
    const aiAnswer = messages[messageIdx].content

    const conversationId = activeConversationId || 'unknown-conversation'

    try {
      await axios.post(`${API}/feedback/`, {
        message_id: messageId,
        conversation_id: conversationId,
        is_positive: isPositive,
        original_question: userQuestion,
        ai_answer: aiAnswer,
      })
      setFeedbackGiven(prev => ({ ...prev, [messageId]: isPositive ? 'up' : 'down' }))
    } catch {}
  }

  return (
    <div className="flex h-screen bg-slate-900">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="border-b border-slate-700 bg-slate-800 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 hover:bg-slate-700 rounded transition"
            >
              <Menu size={20} />
            </button>
            <div>
              <h1 className="font-bold text-white">Health Literacy Assistant</h1>
              <p className="text-sm text-slate-400">Ask any health question</p>
            </div>
          </div>
          <button
            onClick={() => setSourcePanelOpen(!sourcePanelOpen)}
            className="hidden lg:block px-4 py-2 text-sm font-medium text-cyan-400 hover:text-cyan-300 border border-slate-700 hover:border-cyan-400 rounded transition"
          >
            {sourcePanelOpen ? 'Hide Sources' : 'Show Sources'}
          </button>
        </header>

        {/* Chat Container */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Area */}
          <div className="flex-1 flex flex-col">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-1">
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center px-6 text-center">
                  <div className="w-16 h-16 bg-cyan-400/10 rounded-full flex items-center justify-center mb-4">
                    <span className="text-3xl">💬</span>
                  </div>
                  <h2 className="text-2xl font-bold text-white mb-2">
                    What can I help you with?
                  </h2>
                  <p className="text-slate-400 mb-8 max-w-md">
                    Ask any health question by typing or using your voice. Answers are from verified medical documents only.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-md">
                    {[
                      'What are the symptoms of diabetes?',
                      'How is hypertension treated?',
                      'I have high fever what should I do?',
                      'What causes headaches?',
                    ].map((q, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(q)}
                        className="text-left px-4 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-cyan-400 rounded text-sm text-slate-300 hover:text-white transition"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                  {SpeechRecognition && (
                    <p className="text-xs text-slate-500 mt-6">
                      💡 Click the microphone icon below to ask using your voice
                    </p>
                  )}
                </div>
              )}

              {messages.map((msg, i) => (
                <ChatMessage
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  clinicalAnswer={msg.clinical_answer}
                  citations={msg.citations}
                  isEmergency={msg.is_emergency}
                  piiDetected={msg.pii_detected}
                  messageId={msg.message_id}
                  feedbackGiven={msg.message_id ? feedbackGiven[msg.message_id] : undefined}
                  onFeedback={(id, isPositive) => submitFeedback(id, isPositive)}
                  onSpeak={speakText}
                  isSpeaking={isSpeaking}
                />
              ))}

              {loading && (
                <div className="flex gap-4 px-6 py-4">
                  <div className="w-8 h-8 bg-cyan-400 rounded-full flex items-center justify-center text-slate-900 font-bold flex-shrink-0">
                    H
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="animate-spin">⏳</div>
                    <span className="text-slate-400">Searching documents...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t border-slate-700 bg-slate-800 p-6">
              <div className="max-w-3xl mx-auto">
                {isListening && (
                  <div className="mb-3 flex items-center gap-2 text-cyan-400 text-sm">
                    <span className="inline-block w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></span>
                    Listening — speak your health question...
                  </div>
                )}
                <div className="flex gap-3">
                  {SpeechRecognition && (
                    <button
                      onClick={toggleListening}
                      disabled={loading}
                      className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition ${
                        isListening
                          ? 'bg-red-600 text-white hover:bg-red-700'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      } disabled:opacity-50`}
                      title={isListening ? 'Stop listening' : 'Start voice input'}
                    >
                      {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                    </button>
                  )}
                  <div className="flex-1 flex gap-2">
                    <input
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && sendMessage()}
                      placeholder={isListening ? 'Listening...' : 'Message Health Assistant...'}
                      disabled={loading}
                      className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 disabled:opacity-50"
                    />
                    <button
                      onClick={() => sendMessage()}
                      disabled={loading || !input.trim()}
                      className="px-4 py-2 bg-cyan-500 text-white rounded-lg font-medium hover:bg-cyan-600 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Source Panel (Desktop) */}
          <div className="hidden lg:block w-80 border-l border-slate-700 bg-slate-800 flex flex-col">
            <div className="p-4 border-b border-slate-700">
              <h2 className="font-semibold text-white text-sm">Medical Sources</h2>
              <p className="text-xs text-slate-400 mt-1">Citation verification</p>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {citations.length > 0 ? (
                citations.map((c, i) => (
                  <div key={i} className="bg-slate-700/50 border border-slate-600 rounded p-3 hover:border-cyan-500/50 transition">
                    <p className="text-xs font-semibold text-cyan-400 mb-1">
                      {c.source.replace(/_/g, ' ').replace('.txt', '').replace('.pdf', '').slice(0, 30)}
                    </p>
                    <p className="text-xs text-slate-400 mb-2">
                      Page {c.page_number} · {c.section_header.replace(/\(cid:\d+\)/g, '').slice(0, 40)}
                    </p>
                    <p className="text-xs text-slate-300 line-clamp-2">
                      {c.text_snippet.replace(/\(cid:\d+\)/g, '').slice(0, 150)}
                    </p>
                  </div>
                ))
              ) : (
                <div className="flex items-center justify-center h-full text-center">
                  <div>
                    <p className="text-sm text-slate-400">No sources yet</p>
                    <p className="text-xs text-slate-500 mt-1">
                      Ask a question to see verified sources
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Emergency Alert Modal */}
      {emergencyAlert && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
          onClick={() => setEmergencyAlert(false)}
        >
          <div
            className="bg-slate-800 border border-red-600/30 rounded-lg p-8 max-w-md text-center"
            onClick={e => e.stopPropagation()}
          >
            <div className="text-4xl mb-4">🚨</div>
            <h2 className="text-xl font-bold text-red-400 mb-2">Medical Emergency Detected</h2>
            <p className="text-slate-300 mb-6">
              Based on your message, you may need immediate medical help.
            </p>
            <div className="space-y-3 mb-6">
              <a
                href="tel:112"
                className="block px-4 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition"
              >
                Call 112 (Emergency)
              </a>
              <a
                href="tel:108"
                className="block px-4 py-3 bg-orange-600 text-white rounded-lg font-semibold hover:bg-orange-700 transition"
              >
                Call 108 (Ambulance)
              </a>
            </div>
            <p className="text-xs text-red-400 mb-4">
              Do NOT rely on any AI system during a medical emergency.
            </p>
            <button
              onClick={() => setEmergencyAlert(false)}
              className="px-4 py-2 text-slate-400 hover:text-white transition"
            >
              I understand
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
