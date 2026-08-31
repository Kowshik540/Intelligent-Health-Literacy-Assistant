import { useLocation, useNavigate } from 'react-router-dom'
import { Home, MessageCircle, BarChart3, FileText, Settings, User, Plus, ChevronRight } from 'lucide-react'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()

  const isActive = (path: string) => location.pathname === path

  const navItems = [
    { label: 'Home', icon: Home, path: '/' },
    { label: 'Assistant', icon: MessageCircle, path: '/assistant' },
    { label: 'Dashboard', icon: BarChart3, path: '/dashboard' },
    { label: 'Documents', icon: FileText, path: '/documents' },
    { label: 'Settings', icon: Settings, path: '/settings' },
  ]

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 w-64 bg-slate-900 border-r border-slate-700 flex flex-col z-50 transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Logo Section */}
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-cyan-400 rounded-lg flex items-center justify-center text-slate-900 font-bold text-sm">
              H
            </div>
            <div className="flex-1">
              <h1 className="font-bold text-white text-sm">Health Literacy</h1>
              <p className="text-xs text-slate-400">Assistant</p>
            </div>
          </div>
        </div>

        {/* New Chat Button */}
        <div className="p-4">
          <button
            onClick={() => {
              navigate('/assistant')
              onClose()
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-cyan-500 text-slate-900 rounded-lg font-semibold text-sm hover:bg-cyan-400 transition"
          >
            <Plus size={16} />
            New Chat
          </button>
        </div>

        {/* Recent Chats Placeholder */}
        <div className="px-4 mb-4">
          <p className="text-xs font-semibold text-slate-400 mb-2">RECENT CHATS</p>
          <p className="text-xs text-slate-500">No recent conversations</p>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 px-4 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.path}
              onClick={() => {
                navigate(item.path)
                onClose()
              }}
              className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium transition ${
                isActive(item.path)
                  ? 'bg-cyan-500/20 text-cyan-400'
                  : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              <item.icon size={18} />
              <span className="flex-1 text-left">{item.label}</span>
              {isActive(item.path) && <ChevronRight size={16} />}
            </button>
          ))}
        </nav>

        {/* User Profile Section */}
        <div className="p-4 border-t border-slate-700">
          <button className="w-full flex items-center gap-3 px-4 py-2 rounded-lg hover:bg-slate-800 transition">
            <User size={18} className="text-slate-400" />
            <div className="text-left">
              <p className="text-sm font-medium text-white">Guest User</p>
              <p className="text-xs text-slate-500">Secure session</p>
            </div>
          </button>
        </div>
      </aside>
    </>
  )
}
