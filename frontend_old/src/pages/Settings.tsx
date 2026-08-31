import { Menu } from 'lucide-react'
import { useState } from 'react'
import { Sidebar } from '../components/Sidebar'

export function SettingsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen bg-slate-900">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col">
        <header className="border-b border-slate-700 bg-slate-800 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 hover:bg-slate-700 rounded transition"
            >
              <Menu size={20} />
            </button>
            <div>
              <h1 className="font-bold text-white">Settings</h1>
              <p className="text-sm text-slate-400">Preferences and account settings</p>
            </div>
          </div>
        </header>

        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-slate-400 text-lg mb-2">⚙️ Settings</p>
            <p className="text-slate-500 text-sm">Coming soon...</p>
          </div>
        </div>
      </div>
    </div>
  )
}
