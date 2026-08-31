import { useNavigate } from 'react-router-dom'
import {
  CheckCircle,
  ShieldCheck,
  BookOpen,
  Lock,
  Lightbulb,
  ArrowRight,
} from 'lucide-react'

export function HomePage() {
  const navigate = useNavigate()

  const features = [
    {
      icon: CheckCircle,
      title: 'Verified Medical Sources',
      description: 'All answers grounded in trusted medical documents and WHO guidelines',
    },
    {
      icon: ShieldCheck,
      title: 'Evidence-Based Answers',
      description: 'Clinical accuracy with transparency and full source citations',
    },
    {
      icon: BookOpen,
      title: 'Source Citations',
      description: 'See exactly which medical document supports each answer',
    },
    {
      icon: Lock,
      title: 'Safety Guardrails',
      description: 'Emergency detection and privacy protection built-in',
    },
    {
      icon: Lightbulb,
      title: 'Plain-Language Explanations',
      description: 'Medical concepts explained in simple, understandable terms',
    },
    {
      icon: BookOpen,
      title: 'Continuous Learning',
      description: 'System improves based on user feedback and clinical review',
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950">
      {/* Hero Section */}
      <div className="max-w-5xl mx-auto px-6 py-20 text-center">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-2xl flex items-center justify-center">
            <span className="text-3xl font-bold text-slate-900">H</span>
          </div>
        </div>

        {/* Main Headline */}
        <h1 className="text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
          Understand Your Health.
          <br />
          <span className="bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            With Confidence.
          </span>
        </h1>

        {/* Supporting Text */}
        <p className="text-xl text-slate-300 mb-8 max-w-2xl mx-auto leading-relaxed">
          Get reliable, evidence-based medical information powered by verified medical documents.
          Ask any health question and receive answers backed by clinical research.
        </p>

        {/* CTA Button */}
        <button
          onClick={() => navigate('/assistant')}
          className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-semibold rounded-lg hover:from-cyan-400 hover:to-blue-400 transition transform hover:scale-105 text-lg mb-12"
        >
          Ask Health Assistant
          <ArrowRight size={20} />
        </button>

        {/* Trust Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-full">
          <ShieldCheck size={16} className="text-green-400" />
          <span className="text-sm text-slate-300">
            Powered by WHO Medical Guidelines
          </span>
        </div>
      </div>

      {/* Features Grid */}
      <div className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-white text-center mb-14">
          Why Choose This Assistant?
        </h2>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, i) => {
            const Icon = feature.icon
            return (
              <div
                key={i}
                className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 hover:border-cyan-500/50 transition group"
              >
                <div className="w-12 h-12 bg-cyan-500/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-cyan-500/20 transition">
                  <Icon className="text-cyan-400" size={24} />
                </div>
                <h3 className="font-semibold text-white mb-2 text-lg">
                  {feature.title}
                </h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            )
          })}
        </div>
      </div>

      {/* How It Works */}
      <div className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-white text-center mb-14">
          How It Works
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { step: '1', label: 'Ask', description: 'Tell us your health question' },
            { step: '2', label: 'Retrieve', description: 'Search medical documents' },
            { step: '3', label: 'Verify', description: 'Check against sources' },
            { step: '4', label: 'Explain', description: 'Get clear answers' },
          ].map((item, i) => (
            <div key={i}>
              <div className="bg-gradient-to-br from-cyan-500 to-blue-500 rounded-lg p-6 text-white text-center mb-3">
                <div className="text-3xl font-bold">{item.step}</div>
                <p className="font-semibold mt-2">{item.label}</p>
              </div>
              <p className="text-sm text-slate-400 text-center">{item.description}</p>
            </div>
          ))}
        </div>

        {/* Pipeline Explanation */}
        <div className="mt-12 bg-slate-800/30 border border-slate-700 rounded-lg p-8">
          <h3 className="font-semibold text-white mb-4 text-lg">Trusted Medical Knowledge</h3>
          <p className="text-slate-300 mb-4 leading-relaxed">
            This assistant uses a Retrieval-Augmented Generation (RAG) system to provide
            medically accurate answers. Every response is grounded in verified medical
            documents including WHO guidelines and clinical references. Our system:
          </p>
          <ul className="space-y-2 text-slate-300">
            <li className="flex items-center gap-3">
              <CheckCircle size={18} className="text-cyan-400 flex-shrink-0" />
              Retrieves relevant passages from verified medical sources
            </li>
            <li className="flex items-center gap-3">
              <CheckCircle size={18} className="text-cyan-400 flex-shrink-0" />
              Generates evidence-based explanations with citations
            </li>
            <li className="flex items-center gap-3">
              <CheckCircle size={18} className="text-cyan-400 flex-shrink-0" />
              Provides both clinical and simple-language versions
            </li>
            <li className="flex items-center gap-3">
              <CheckCircle size={18} className="text-cyan-400 flex-shrink-0" />
              Collects user feedback to continuously improve
            </li>
          </ul>
        </div>
      </div>

      {/* Medical Disclaimer */}
      <div className="border-t border-slate-700">
        <div className="max-w-5xl mx-auto px-6 py-12">
          <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-6">
            <h3 className="font-semibold text-red-400 mb-2 flex items-center gap-2">
              <AlertTriangle size={18} />
              Medical Disclaimer
            </h3>
            <p className="text-sm text-slate-400">
              This assistant is designed to provide general health information based on
              verified medical sources. It is NOT a substitute for professional medical advice,
              diagnosis, or treatment. Always consult with a qualified healthcare provider
              before making any health decisions. In case of medical emergencies, call 112 (India)
              or your local emergency number immediately.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// Icon component for disclaimer
function AlertTriangle(props: any) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M12 2L2 20h20L12 2z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}
