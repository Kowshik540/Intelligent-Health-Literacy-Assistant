import { useState } from 'react'
import { ThumbsUp, ThumbsDown, Volume2, Check, AlertCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface Citation {
  source: string
  page_number: string
  section_header: string
  relevance_score: number
  text_snippet: string
}

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  clinicalAnswer?: string
  citations?: Citation[]
  isEmergency?: boolean
  piiDetected?: boolean
  messageId?: string
  feedbackGiven?: string
  onFeedback?: (messageId: string, isPositive: boolean) => void
  onSpeak?: (text: string) => void
  isSpeaking?: boolean
}

function cleanAnswer(text: string): string {
  return text.replace(/\[Source:[^\]]*\]/g, '').replace(/\n{3,}/g, '\n\n').trim()
}

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

export function ChatMessage({
  role,
  content,
  clinicalAnswer,
  citations,
  isEmergency,
  piiDetected,
  messageId,
  feedbackGiven,
  onFeedback,
  onSpeak,
  isSpeaking,
}: ChatMessageProps) {
  const [showClinical, setShowClinical] = useState(false)
  const [showCitations, setShowCitations] = useState(false)

  const displayText = showClinical && clinicalAnswer ? clinicalAnswer : content

  return (
    <div
      className={`flex gap-4 px-6 py-4 ${
        role === 'user'
          ? 'justify-end bg-slate-800/50'
          : 'justify-start bg-slate-900/50'
      }`}
    >
      {/* Assistant Avatar */}
      {role === 'assistant' && (
        <div className="flex-shrink-0 w-8 h-8 bg-cyan-400 rounded-full flex items-center justify-center text-slate-900 font-bold text-sm">
          H
        </div>
      )}

      {/* Message Content */}
      <div
        className={`flex-1 max-w-2xl ${
          role === 'user' ? 'text-right' : 'text-left'
        }`}
      >
        {/* Notices */}
        {piiDetected && (
          <div className="mb-3 px-3 py-2 bg-yellow-500/10 border border-yellow-600/30 rounded text-xs text-yellow-600 flex items-center gap-2">
            <AlertCircle size={14} />
            Personal information removed before processing.
          </div>
        )}

        {isEmergency && (
          <div className="mb-3 px-3 py-2 bg-red-500/10 border border-red-600/30 rounded text-xs text-red-600 flex items-center gap-2">
            <AlertCircle size={14} />
            Emergency detected — contact emergency services (112/108) immediately.
          </div>
        )}

        {/* Message Bubble */}
        <div
          className={`inline-block px-4 py-3 rounded-lg ${
            role === 'user'
              ? 'bg-cyan-600 text-white'
              : 'bg-slate-800 text-slate-100 border border-slate-700'
          }`}
        >
          <div className="prose prose-sm max-w-none prose-invert">
            <ReactMarkdown>{cleanAnswer(displayText)}</ReactMarkdown>
          </div>
        </div>

        {/* Assistant Actions */}
        {role === 'assistant' && !isEmergency && (
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            {/* Mode Toggle */}
            {clinicalAnswer && (
              <div className="flex gap-1 bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
                <button
                  onClick={() => setShowClinical(false)}
                  className={`px-3 py-1 text-xs font-medium transition ${
                    !showClinical
                      ? 'bg-cyan-500 text-slate-900'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  Simple
                </button>
                <button
                  onClick={() => setShowClinical(true)}
                  className={`px-3 py-1 text-xs font-medium transition ${
                    showClinical
                      ? 'bg-cyan-500 text-slate-900'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  Clinical
                </button>
              </div>
            )}

            {/* Feedback Buttons */}
            {messageId && (
              <div className="flex gap-1">
                {feedbackGiven ? (
                  <div className="flex items-center gap-1 px-3 py-1 text-xs text-cyan-400 font-medium">
                    <Check size={14} />
                    Thanks for feedback
                  </div>
                ) : (
                  <>
                    <button
                      onClick={() => onFeedback?.(messageId, true)}
                      className="p-1.5 text-slate-400 hover:text-cyan-400 border border-slate-700 hover:border-cyan-400 rounded transition"
                      title="Helpful"
                    >
                      <ThumbsUp size={14} />
                    </button>
                    <button
                      onClick={() => onFeedback?.(messageId, false)}
                      className="p-1.5 text-slate-400 hover:text-red-400 border border-slate-700 hover:border-red-400 rounded transition"
                      title="Not helpful"
                    >
                      <ThumbsDown size={14} />
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Speak Button */}
            <button
              onClick={() => onSpeak?.(displayText)}
              className={`p-1.5 rounded border transition ${
                isSpeaking
                  ? 'text-cyan-400 border-cyan-400 bg-cyan-500/10'
                  : 'text-slate-400 border-slate-700 hover:text-cyan-400 hover:border-cyan-400'
              }`}
              title="Read aloud"
            >
              <Volume2 size={14} />
            </button>

            {/* Citations Button */}
            {citations && citations.length > 0 && (
              <button
                onClick={() => setShowCitations(!showCitations)}
                className="px-3 py-1 text-xs font-medium text-cyan-400 hover:text-cyan-300 border border-cyan-500/30 hover:border-cyan-400 rounded transition"
              >
                {citations.length} Source{citations.length !== 1 ? 's' : ''}
              </button>
            )}
          </div>
        )}

        {/* Inline Citations */}
        {showCitations && citations && citations.length > 0 && (
          <div className="mt-3 space-y-2 text-xs">
            {citations.slice(0, 2).map((c, i) => (
              <div key={i} className="bg-slate-800/50 border border-slate-700 rounded p-2">
                <p className="text-cyan-400 font-semibold mb-1">{formatSource(c.source)}</p>
                <p className="text-slate-400">Page {c.page_number} · {c.section_header.replace(/\(cid:\d+\)/g, '').slice(0, 60)}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* User Avatar */}
      {role === 'user' && (
        <div className="flex-shrink-0 w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center text-slate-300 font-bold text-sm">
          U
        </div>
      )}
    </div>
  )
}
