import { FileText, CheckCircle, Clock, AlertCircle } from 'lucide-react'

interface DocumentCardProps {
  title: string
  type: string
  status: 'indexed' | 'pending' | 'processing' | 'error'
  pageCount?: number
  chunkCount?: number
  source?: string
  uploadedDate?: string
}

export function DocumentCard({
  title,
  type,
  status,
  pageCount,
  chunkCount,
  source,
  uploadedDate,
}: DocumentCardProps) {
  const statusConfig = {
    indexed: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-400/10', label: 'Indexed' },
    pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10', label: 'Pending' },
    processing: { icon: Clock, color: 'text-blue-400', bg: 'bg-blue-400/10', label: 'Processing' },
    error: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: 'Error' },
  }

  const config = statusConfig[status]
  const StatusIcon = config.icon

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 hover:border-slate-600 transition">
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <FileText className="text-slate-400 flex-shrink-0 mt-1" size={20} />
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white text-sm truncate">{title}</h3>
          <p className="text-xs text-slate-400 mt-1">{type.toUpperCase()}</p>
        </div>
      </div>

      {/* Status Badge */}
      <div className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium mb-3 ${config.bg} ${config.color}`}>
        <StatusIcon size={12} />
        {config.label}
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4 text-xs">
        {pageCount !== undefined && (
          <div className="bg-slate-900/50 rounded px-2 py-2">
            <p className="text-slate-500">Pages</p>
            <p className="font-semibold text-white">{pageCount}</p>
          </div>
        )}
        {chunkCount !== undefined && (
          <div className="bg-slate-900/50 rounded px-2 py-2">
            <p className="text-slate-500">Chunks</p>
            <p className="font-semibold text-white">{chunkCount.toLocaleString()}</p>
          </div>
        )}
        {source && (
          <div className="bg-slate-900/50 rounded px-2 py-2 col-span-2">
            <p className="text-slate-500">Source</p>
            <p className="font-semibold text-white truncate">{source}</p>
          </div>
        )}
        {uploadedDate && (
          <div className="bg-slate-900/50 rounded px-2 py-2 col-span-2">
            <p className="text-slate-500">Uploaded</p>
            <p className="font-semibold text-white">{new Date(uploadedDate).toLocaleDateString()}</p>
          </div>
        )}
      </div>

      {/* Action Button */}
      <button className="w-full px-3 py-2 text-xs font-medium text-cyan-400 hover:text-cyan-300 border border-slate-700 hover:border-cyan-400 rounded transition">
        View Details
      </button>
    </div>
  )
}
