import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Database, Download, Upload, Pencil, Trash2, Save, X, Search,
  History, Inbox, CheckCircle2, CircleSlash, RefreshCw,
} from 'lucide-react'

import api from '../utils/api'

const DEFAULT_FORM = {
  question: '',
  answer: '',
  category: 'General',
  keywords: '',
  allowed_roles: ['admin', 'hr', 'intern'],
}

export default function QuestionBankPage() {
  const [questions, setQuestions] = useState([])
  const [history, setHistory] = useState([])
  const [queueItems, setQueueItems] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(DEFAULT_FORM)
  const [importText, setImportText] = useState('')
  const [queueNote, setQueueNote] = useState({})

  const loadAll = async () => {
    setLoading(true)
    setError('')
    try {
      const [questionsRes, historyRes, queueRes] = await Promise.all([
        api.get('/chat/questions'),
        api.get('/chat/questions/history'),
        api.get('/chat/questions/review-queue'),
      ])
      setQuestions(questionsRes.data.questions || [])
      setHistory(historyRes.data.history || [])
      setQueueItems(queueRes.data.items || [])
    } catch (err) {
      setError(err?.response?.data?.error || 'Unable to load question bank tools.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  const filteredQuestions = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return questions
    return questions.filter(item =>
      [item.question, item.category, ...(item.keywords || []), ...(item.allowed_roles || [])]
        .join(' ')
        .toLowerCase()
        .includes(needle)
    )
  }, [questions, query])

  const resetForm = () => {
    setEditingId(null)
    setForm(DEFAULT_FORM)
  }

  const startEdit = (item) => {
    setEditingId(item.id)
    setForm({
      question: item.question,
      answer: item.answer || '',
      category: item.category,
      keywords: (item.keywords || []).join(', '),
      allowed_roles: item.allowed_roles || ['admin', 'hr', 'intern'],
    })
  }

  const submitForm = async () => {
    const payload = {
      question: form.question.trim(),
      answer: form.answer.trim(),
      category: form.category.trim() || 'General',
      keywords: form.keywords.split(',').map(item => item.trim()).filter(Boolean),
      allowed_roles: form.allowed_roles,
    }
    if (!payload.question || !payload.answer) {
      setError('Question and answer are required.')
      return
    }

    try {
      if (editingId) {
        await api.put(`/chat/questions/${editingId}`, payload)
      } else {
        await api.post('/chat/questions', payload)
      }
      resetForm()
      loadAll()
    } catch (err) {
      setError(err?.response?.data?.error || 'Unable to save question.')
    }
  }

  const deleteQuestion = async (questionId) => {
    try {
      await api.delete(`/chat/questions/${questionId}`)
      if (editingId === questionId) resetForm()
      loadAll()
    } catch (err) {
      setError(err?.response?.data?.error || 'Unable to delete question.')
    }
  }

  const importQuestions = async () => {
    try {
      const parsed = JSON.parse(importText)
      await api.post('/chat/questions/import', { questions: parsed })
      setImportText('')
      loadAll()
    } catch (err) {
      setError(err?.response?.data?.error || 'Import failed. Use a valid JSON array.')
    }
  }

  const exportQuestions = async (format) => {
    const res = await api.get(`/chat/questions/export?format=${format}`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(res.data)
    const link = document.createElement('a')
    link.href = url
    link.download = format === 'csv' ? 'secureai-question-bank.csv' : 'secureai-question-bank.json'
    link.click()
    window.URL.revokeObjectURL(url)
  }

  const updateQueueItem = async (queueId, status) => {
    try {
      await api.patch(`/chat/questions/review-queue/${queueId}`, {
        status,
        resolution_note: queueNote[queueId] || '',
      })
      loadAll()
    } catch (err) {
      setError(err?.response?.data?.error || 'Unable to update review queue item.')
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <div className="px-6 py-6 space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white">Question Bank Operations</h1>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest mt-1">
              Manage dataset content, imports, review queue, and history
            </p>
          </div>
          <motion.button
            whileHover={{ rotate: 180 }}
            transition={{ duration: 0.35 }}
            onClick={loadAll}
            className="p-2 rounded-lg glass-light border border-white/8 text-slate-400 hover:text-accent"
          >
            <RefreshCw size={15} />
          </motion.button>
        </div>

        {error && (
          <div className="px-4 py-3 rounded-xl bg-danger/10 border border-danger/20 text-sm text-danger">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-[1.25fr_0.9fr] gap-6">
          <div className="space-y-6">
            <div className="glass rounded-2xl p-5 border border-white/5">
              <div className="flex items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-2">
                  <Database size={16} className="text-accent" />
                  <div>
                    <p className="text-sm font-bold text-white">Dataset Questions</p>
                    <p className="text-[10px] font-mono text-slate-500">{questions.length} questions saved</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => exportQuestions('json')} className="px-3 py-2 rounded-xl bg-white/5 border border-white/8 text-xs text-slate-300 hover:text-accent">
                    <Download size={12} className="inline mr-1.5" />JSON
                  </button>
                  <button onClick={() => exportQuestions('csv')} className="px-3 py-2 rounded-xl bg-white/5 border border-white/8 text-xs text-slate-300 hover:text-accent">
                    <Download size={12} className="inline mr-1.5" />CSV
                  </button>
                </div>
              </div>

              <div className="relative mb-4">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Search by question, category, role, or keyword..."
                  className="w-full pl-9 pr-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-accent/40"
                />
              </div>

              <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                {loading ? (
                  <p className="text-xs text-slate-500 font-mono">Loading dataset...</p>
                ) : filteredQuestions.map(item => (
                  <div key={item.id} className="rounded-2xl bg-bg-800/70 border border-white/8 p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm text-white font-semibold">{item.question}</p>
                        <p className="text-[10px] font-mono text-slate-500 mt-1">
                          {item.category} · roles: {(item.allowed_roles || []).join(', ')}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => startEdit(item)}
                          className="p-2 rounded-lg bg-white/5 border border-white/8 text-slate-400 hover:text-accent"
                        >
                          <Pencil size={13} />
                        </button>
                        <button
                          onClick={() => deleteQuestion(item.id)}
                          className="p-2 rounded-lg bg-white/5 border border-white/8 text-slate-400 hover:text-danger"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(item.keywords || []).map(keyword => (
                        <span key={keyword} className="px-2 py-1 rounded-lg text-[10px] font-mono bg-accent/10 text-accent border border-accent/20">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass rounded-2xl p-5 border border-white/5">
              <div className="flex items-center gap-2 mb-4">
                <Inbox size={16} className="text-warn" />
                <div>
                  <p className="text-sm font-bold text-white">Unanswered Review Queue</p>
                  <p className="text-[10px] font-mono text-slate-500">Queries captured when the dataset had no strong match</p>
                </div>
              </div>
              <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1">
                {queueItems.map(item => (
                  <div key={item.id} className="rounded-2xl bg-bg-800/70 border border-white/8 p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm text-white">{item.query}</p>
                        <p className="text-[10px] font-mono text-slate-500 mt-1">
                          seen {item.count} times · latest {item.latest_username} ({item.latest_role}) · {item.status}
                        </p>
                      </div>
                    </div>
                    <input
                      value={queueNote[item.id] || item.resolution_note || ''}
                      onChange={e => setQueueNote(prev => ({ ...prev, [item.id]: e.target.value }))}
                      placeholder="Resolution note"
                      className="w-full px-3 py-2 rounded-xl bg-bg-900 border border-white/8 text-sm text-white placeholder-slate-600"
                    />
                    <div className="flex gap-2">
                      <button onClick={() => updateQueueItem(item.id, 'resolved')} className="px-3 py-2 rounded-xl bg-success/10 border border-success/20 text-xs text-success">
                        <CheckCircle2 size={12} className="inline mr-1.5" />Resolve
                      </button>
                      <button onClick={() => updateQueueItem(item.id, 'ignored')} className="px-3 py-2 rounded-xl bg-white/5 border border-white/8 text-xs text-slate-300">
                        <CircleSlash size={12} className="inline mr-1.5" />Ignore
                      </button>
                    </div>
                  </div>
                ))}
                {!queueItems.length && <p className="text-xs text-slate-500 font-mono">No unanswered questions waiting for review.</p>}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="glass rounded-2xl p-5 border border-white/5">
              <p className="text-sm font-bold text-white mb-4">{editingId ? 'Edit Question' : 'Add Question'}</p>
              <div className="space-y-3">
                <input
                  value={form.question}
                  onChange={e => setForm(prev => ({ ...prev, question: e.target.value }))}
                  placeholder="Question"
                  className="w-full px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-sm text-white placeholder-slate-600"
                />
                <textarea
                  rows={5}
                  value={form.answer}
                  onChange={e => setForm(prev => ({ ...prev, answer: e.target.value }))}
                  placeholder="Answer"
                  className="w-full px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-sm text-white placeholder-slate-600 resize-none"
                />
                <input
                  value={form.category}
                  onChange={e => setForm(prev => ({ ...prev, category: e.target.value }))}
                  placeholder="Category"
                  className="w-full px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-sm text-white placeholder-slate-600"
                />
                <input
                  value={form.keywords}
                  onChange={e => setForm(prev => ({ ...prev, keywords: e.target.value }))}
                  placeholder="Keywords, comma separated"
                  className="w-full px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-sm text-white placeholder-slate-600"
                />
                <div className="flex flex-wrap gap-2">
                  {['admin', 'hr', 'intern'].map(role => (
                    <button
                      key={role}
                      onClick={() => setForm(prev => ({
                        ...prev,
                        allowed_roles: prev.allowed_roles.includes(role)
                          ? prev.allowed_roles.filter(item => item !== role)
                          : [...prev.allowed_roles, role],
                      }))}
                      className={`px-3 py-2 rounded-xl text-xs border ${
                        form.allowed_roles.includes(role)
                          ? 'bg-accent/10 border-accent/30 text-accent'
                          : 'bg-white/5 border-white/8 text-slate-300'
                      }`}
                    >
                      {role}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button onClick={submitForm} className="px-4 py-2 rounded-xl bg-accent text-bg-900 text-sm font-semibold">
                    <Save size={13} className="inline mr-1.5" />{editingId ? 'Save changes' : 'Add question'}
                  </button>
                  {editingId && (
                    <button onClick={resetForm} className="px-4 py-2 rounded-xl bg-white/5 border border-white/8 text-sm text-slate-300">
                      <X size={13} className="inline mr-1.5" />Cancel
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="glass rounded-2xl p-5 border border-white/5">
              <div className="flex items-center gap-2 mb-4">
                <Upload size={16} className="text-accent" />
                <div>
                  <p className="text-sm font-bold text-white">Bulk Import</p>
                  <p className="text-[10px] font-mono text-slate-500">Paste a JSON array of question objects</p>
                </div>
              </div>
              <textarea
                rows={8}
                value={importText}
                onChange={e => setImportText(e.target.value)}
                placeholder='[{"question":"...","answer":"...","category":"HR","keywords":["policy"],"allowed_roles":["admin","hr","intern"]}]'
                className="w-full px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-sm text-white placeholder-slate-600 resize-none"
              />
              <button onClick={importQuestions} className="mt-3 px-4 py-2 rounded-xl bg-accent text-bg-900 text-sm font-semibold">
                <Upload size={13} className="inline mr-1.5" />Import questions
              </button>
            </div>

            <div className="glass rounded-2xl p-5 border border-white/5">
              <div className="flex items-center gap-2 mb-4">
                <History size={16} className="text-accent" />
                <div>
                  <p className="text-sm font-bold text-white">Version History</p>
                  <p className="text-[10px] font-mono text-slate-500">Track who changed what in the dataset</p>
                </div>
              </div>
              <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                {history.map((item, index) => (
                  <div key={`${item.timestamp}-${index}`} className="rounded-xl bg-bg-800/70 border border-white/8 p-3">
                    <p className="text-sm text-white">{item.action} · {item.question_id}</p>
                    <p className="text-[10px] font-mono text-slate-500 mt-1">{item.actor} · {new Date(item.timestamp).toLocaleString()}</p>
                  </div>
                ))}
                {!history.length && <p className="text-xs text-slate-500 font-mono">No dataset changes recorded yet.</p>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
