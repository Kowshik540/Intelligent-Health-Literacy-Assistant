import { useState, useEffect } from 'react'
import { Menu, Search, TrendingUp, ThumbsUp, ThumbsDown, BarChart3 } from 'lucide-react'
import axios from 'axios'
import { Sidebar } from '../components/Sidebar'
import { DocumentCard } from '../components/DocumentCard'
import { FeedbackCard } from '../components/FeedbackCard'

const API = 'http://localhost:8000/api/v1'

interface FeedbackStats {
  total_feedback: number
  positive: number
  negative: number
  satisfaction_rate: number
  golden_dataset_size: number
}

interface FeedbackRecord {
  id: string
  original_question: string
  ai_answer: string
  is_positive: boolean
  created_at: string
  user_correction?: string
}

export function DashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [feedbackRecords, setFeedbackRecords] = useState<FeedbackRecord[]>([])
  const [filteredRecords, setFilteredRecords] = useState<FeedbackRecord[]>([])
  const [documents, setDocuments] = useState<any[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'positive' | 'negative'>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)

        const [statsRes, documentsRes] = await Promise.all([
          axios.get(`${API}/feedback/stats`),
          axios.get(`${API}/documents`),
        ])

        setStats(statsRes.data)
        const docList = documentsRes.data?.documents || []
        setDocuments(docList)
        setFeedbackRecords([])
        setFilteredRecords([])
      } catch (err: any) {
        if (err.response?.status === 404) {
          setError('The backend is available, but the document listing endpoint is not currently exposed.')
        } else {
          setError('Failed to load dashboard data. Make sure backend is running.')
        }
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // Filter and search feedback records
  useEffect(() => {
    let filtered = feedbackRecords

    // Apply type filter
    if (filterType !== 'all') {
      filtered = filtered.filter(r =>
        filterType === 'positive' ? r.is_positive : !r.is_positive
      )
    }

    // Apply search
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      filtered = filtered.filter(r =>
        r.original_question.toLowerCase().includes(term) ||
        r.ai_answer.toLowerCase().includes(term)
      )
    }

    setFilteredRecords(filtered)
  }, [feedbackRecords, searchTerm, filterType])

  const mappedDocuments = documents.map((doc) => ({
    title: doc.filename || 'Unnamed document',
    type: doc.file_type || 'pdf',
    status: (doc.status === 'completed' || doc.status === 'indexed' ? 'indexed' : doc.status === 'processing' ? 'processing' : doc.status === 'pending_approval' ? 'pending' : 'error') as 'indexed' | 'pending' | 'processing' | 'error',
    pageCount: undefined,
    chunkCount: doc.chunk_count ?? undefined,
    source: doc.publisher || 'Unspecified source',
    uploadedDate: doc.created_at || undefined,
  }))

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
              <h1 className="font-bold text-white">Dashboard</h1>
              <p className="text-sm text-slate-400">Documents & Analytics</p>
            </div>
          </div>
          <TrendingUp className="text-cyan-400" size={24} />
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-6 py-8">
            {error && (
              <div className="bg-red-500/10 border border-red-600/30 rounded-lg p-4 mb-8 text-red-400">
                {error}
              </div>
            )}

            {/* Feedback Statistics Cards */}
            {stats && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-12">
                <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-slate-400 text-sm font-medium mb-1">Total Responses</p>
                      <p className="text-3xl font-bold text-white">{stats.total_feedback}</p>
                    </div>
                    <BarChart3 className="text-slate-500" size={32} />
                  </div>
                </div>

                <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-slate-400 text-sm font-medium mb-1">Positive Feedback</p>
                      <p className="text-3xl font-bold text-green-400">{stats.positive}</p>
                    </div>
                    <ThumbsUp className="text-green-500" size={32} />
                  </div>
                </div>

                <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-slate-400 text-sm font-medium mb-1">Negative Feedback</p>
                      <p className="text-3xl font-bold text-red-400">{stats.negative}</p>
                    </div>
                    <ThumbsDown className="text-red-500" size={32} />
                  </div>
                </div>

                <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-slate-400 text-sm font-medium mb-1">Satisfaction Rate</p>
                      <p className="text-3xl font-bold text-cyan-400">{stats.satisfaction_rate}%</p>
                    </div>
                    <TrendingUp className="text-cyan-500" size={32} />
                  </div>
                </div>
              </div>
            )}

            {/* Documents Section */}
            <div className="mb-12">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-white mb-2">Medical Documents</h2>
                <p className="text-slate-400">
                  {mappedDocuments.length} medical documents indexed in the RAG system
                </p>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-slate-400">Loading documents...</div>
                </div>
              ) : mappedDocuments.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-700 bg-slate-800/60 px-6 py-10 text-center text-slate-400">
                  No documents have been indexed yet.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {mappedDocuments.map((doc, i) => (
                    <DocumentCard key={doc.title + i} {...doc} />
                  ))}
                </div>
              )}
            </div>

            {/* Feedback Analytics Section */}
            <div>
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-white mb-4">Feedback Analytics</h2>

                {stats && stats.total_feedback > 0 && (
                  <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 mb-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <p className="text-slate-400 text-sm mb-1">Positive</p>
                        <div className="flex items-baseline gap-1">
                          <span className="text-2xl font-bold text-green-400">{stats.positive}</span>
                          <span className="text-slate-500">
                            ({((stats.positive / stats.total_feedback) * 100).toFixed(0)}%)
                          </span>
                        </div>
                      </div>
                      <div>
                        <p className="text-slate-400 text-sm mb-1">Negative</p>
                        <div className="flex items-baseline gap-1">
                          <span className="text-2xl font-bold text-red-400">{stats.negative}</span>
                          <span className="text-slate-500">
                            ({((stats.negative / stats.total_feedback) * 100).toFixed(0)}%)
                          </span>
                        </div>
                      </div>
                      <div>
                        <p className="text-slate-400 text-sm mb-1">Satisfaction</p>
                        <p className="text-2xl font-bold text-cyan-400">{stats.satisfaction_rate}%</p>
                      </div>
                      <div>
                        <p className="text-slate-400 text-sm mb-1">Golden Dataset</p>
                        <p className="text-2xl font-bold text-purple-400">{stats.golden_dataset_size}</p>
                      </div>
                    </div>

                    {/* Simple Chart */}
                    <div className="mt-6 pt-6 border-t border-slate-700">
                      <p className="text-slate-400 text-sm mb-3">Feedback Distribution</p>
                      <div className="flex gap-2 h-8">
                        <div
                          className="bg-green-500 rounded"
                          style={{
                            width: `${(stats.positive / stats.total_feedback) * 100}%`,
                            minWidth: '4px',
                          }}
                          title={`Positive: ${stats.positive}`}
                        />
                        <div
                          className="bg-red-500 rounded"
                          style={{
                            width: `${(stats.negative / stats.total_feedback) * 100}%`,
                            minWidth: '4px',
                          }}
                          title={`Negative: ${stats.negative}`}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Recent Feedback Section */}
                <div className="mb-6">
                  <div className="flex flex-col md:flex-row gap-4 mb-4">
                    <div className="flex-1 relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                      <input
                        type="text"
                        placeholder="Search feedback..."
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                      />
                    </div>

                    <div className="flex gap-2">
                      {['all', 'positive', 'negative'].map(type => (
                        <button
                          key={type}
                          onClick={() => setFilterType(type as any)}
                          className={`px-4 py-2 rounded-lg font-medium text-sm transition ${
                            filterType === type
                              ? 'bg-cyan-500 text-slate-900'
                              : 'bg-slate-800 text-slate-300 border border-slate-700 hover:border-cyan-400'
                          }`}
                        >
                          {type === 'all' ? 'All' : type === 'positive' ? '👍 Positive' : '👎 Negative'}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Feedback List */}
                  {filteredRecords.length > 0 ? (
                    <div className="space-y-4">
                      {filteredRecords.map(record => (
                        <FeedbackCard
                          key={record.id}
                          question={record.original_question}
                          answer={record.ai_answer}
                          isPositive={record.is_positive}
                          timestamp={record.created_at}
                          userCorrection={record.user_correction}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-12 text-center">
                      <p className="text-slate-400 mb-2">
                        {searchTerm || filterType !== 'all'
                          ? 'No feedback records match your filters'
                          : 'No feedback records yet'}
                      </p>
                      <p className="text-slate-500 text-sm">
                        {stats && stats.total_feedback === 0
                          ? 'User feedback will appear here after interactions with the Assistant'
                          : 'Try adjusting your search or filters'}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* RLHF Pipeline Explanation */}
              <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-6 mt-8">
                <h3 className="font-semibold text-white mb-4">Understanding the Feedback Pipeline</h3>
                <div className="grid md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl mb-2">📚</div>
                    <p className="font-semibold text-white text-sm mb-1">Medical Documents</p>
                    <p className="text-xs text-slate-400">Provide knowledge base for RAG system</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl mb-2">🔍</div>
                    <p className="font-semibold text-white text-sm mb-1">RAG Retrieval</p>
                    <p className="text-xs text-slate-400">Fetch relevant medical passages</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl mb-2">🤖</div>
                    <p className="font-semibold text-white text-sm mb-1">AI Generation</p>
                    <p className="text-xs text-slate-400">Generate evidence-based answers</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl mb-2">👥</div>
                    <p className="font-semibold text-white text-sm mb-1">User Feedback</p>
                    <p className="text-xs text-slate-400">Evaluate and improve quality</p>
                  </div>
                </div>
                <p className="text-sm text-slate-400 mt-6 text-center">
                  Negative feedback with user corrections builds a Golden Dataset for fine-tuning and continuous improvement.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
