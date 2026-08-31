import { ThumbsUp, ThumbsDown, AlertCircle } from 'lucide-react'

interface FeedbackCardProps {
  question: string
  answer: string
  isPositive: boolean
  timestamp: string
  userCorrection?: string
  source?: string
}

export function FeedbackCard({
  question,
  answer,
  isPositive,
  timestamp,
  userCorrection,
  source,
}: FeedbackCardProps) {
  const formattedDate = new Date(timestamp).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div
      className={`border rounded-lg p-4 bg-slate-900/30 transition ${
        isPositive
          ? 'border-green-600/30 hover:border-green-600/50'
          : 'border-red-600/30 hover:border-red-600/50'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {isPositive ? (
            <div className="flex items-center gap-1 px-2 py-1 bg-green-500/10 text-green-400 rounded text-xs font-medium">
              <ThumbsUp size={12} />
              Positive
            </div>
          ) : (
            <div className="flex items-center gap-1 px-2 py-1 bg-red-500/10 text-red-400 rounded text-xs font-medium">
              <ThumbsDown size={12} />
              Negative
            </div>
          )}
        </div>
        <span className="text-xs text-slate-400">{formattedDate}</span>
      </div>

      {/* Question */}
      <div className="mb-3">
        <p className="text-xs font-semibold text-slate-400 mb-1">Question</p>
        <p className="text-sm text-slate-200 line-clamp-2">{question}</p>
      </div>

      {/* AI Answer */}
      <div className="mb-3">
        <p className="text-xs font-semibold text-slate-400 mb-1">AI Answer</p>
        <p className="text-sm text-slate-300 line-clamp-2">{answer}</p>
      </div>

      {/* User Correction (for negative feedback) */}
      {!isPositive && userCorrection && (
        <div className="mb-3 p-3 bg-slate-800/50 border border-slate-700 rounded">
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle size={14} className="text-yellow-500" />
            <p className="text-xs font-semibold text-yellow-500">User Correction</p>
          </div>
          <p className="text-sm text-slate-200">{userCorrection}</p>
        </div>
      )}

      {/* Source */}
      {source && (
        <div className="text-xs">
          <p className="text-slate-400 mb-1">Citation</p>
          <p className="text-slate-300">{source}</p>
        </div>
      )}
    </div>
  )
}
