import { X } from 'lucide-react'

interface Citation {
  source: string
  page_number: string
  section_header: string
  relevance_score: number
  text_snippet: string
}

interface SourcePanelProps {
  citations: Citation[]
  isOpen: boolean
  onClose: () => void
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

function dedupeCitations(citations: Citation[]): Citation[] {
  const seen = new Set<string>()
  return citations.filter(c => {
    const key = `${c.source}-${c.section_header}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export function SourcePanel({ citations, isOpen, onClose }: SourcePanelProps) {
  const uniqueCitations = dedupeCitations(citations)

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <aside
        className={`fixed lg:static inset-y-0 right-0 w-80 bg-slate-900 border-l border-slate-700 flex flex-col z-50 transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h2 className="font-semibold text-white">Source Verification</h2>
          <button
            onClick={onClose}
            className="lg:hidden p-1 hover:bg-slate-800 rounded transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {uniqueCitations.length > 0 ? (
            uniqueCitations.map((citation, i) => (
              <div
                key={i}
                className="bg-slate-800 border border-slate-700 rounded-lg p-4 hover:border-cyan-500/50 transition"
              >
                {/* Source Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <p className="font-semibold text-cyan-400 text-sm mb-1">
                      {formatSource(citation.source)}
                    </p>
                    <p className="text-xs text-slate-400">
                      Page {citation.page_number} · Section: {citation.section_header.replace(/\(cid:\d+\)/g, '').replace(/\s+/g, ' ').trim().slice(0, 40)}
                    </p>
                  </div>
                  <div className="ml-2 px-2 py-1 bg-slate-700 rounded text-xs text-slate-300">
                    {(citation.relevance_score * 100).toFixed(0)}%
                  </div>
                </div>

                {/* Snippet */}
                <p className="text-sm text-slate-300 leading-relaxed line-clamp-3">
                  {citation.text_snippet.replace(/\(cid:\d+\)/g, '').replace(/\s+/g, ' ').slice(0, 200)}
                </p>

                {/* Action */}
                <button className="mt-3 text-xs font-medium text-cyan-400 hover:text-cyan-300 transition">
                  View Full Document →
                </button>
              </div>
            ))
          ) : (
            <div className="flex items-center justify-center h-full text-center">
              <div>
                <p className="text-sm text-slate-400 mb-2">No sources yet</p>
                <p className="text-xs text-slate-500">Ask a health question to see verified sources</p>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
