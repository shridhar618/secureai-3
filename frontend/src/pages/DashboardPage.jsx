import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { format, formatDistanceToNow } from 'date-fns'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell } from 'recharts'
import {
  Activity, AlertTriangle, ChevronLeft, ChevronRight, Download, Eye, EyeOff,
  Filter, Lock, RefreshCw, Search, ShieldAlert, ShieldCheck, TrendingUp,
  UserX, Zap, Database, MessageCircleQuestion, ThumbsDown, Users, FileText, UserCheck, UserMinus,
} from 'lucide-react'

import api from '../utils/api'
import { formatRoleName } from '../utils/roles'

const STATUS_COLORS = { allowed: '#06d6a0', filtered: '#ffb703', blocked: '#ff4d6d' }
const RISK_COLORS = { low: '#06d6a0', medium: '#ffb703', high: '#ff4d6d' }

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="glass rounded-2xl p-5 border border-white/5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">{label}</p>
          <p className="text-3xl font-extrabold mt-1" style={{ color }}>{value}</p>
        </div>
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${color}18` }}>
          <Icon size={18} style={{ color }} />
        </div>
      </div>
    </div>
  )
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="glass rounded-xl px-3 py-2.5 border border-white/10 text-[11px] font-mono shadow-card">
      {label && <p className="text-slate-400 mb-1.5 font-semibold">{label}</p>}
      {payload.map((item, index) => (
        <div key={index} className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ background: item.fill || item.color }} />
          <span className="text-slate-400">{item.name}:</span>
          <span className="text-white font-bold">{item.value}</span>
        </div>
      ))}
    </div>
  )
}

function RiskBadge({ level }) {
  const styles = {
    low: 'text-success bg-success/10 border-success/20',
    medium: 'text-warn bg-warn/10 border-warn/20',
    high: 'text-danger bg-danger/10 border-danger/20',
  }
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold font-mono uppercase px-1.5 py-0.5 rounded border ${styles[level] || styles.low}`}>
      {level === 'high' && <Zap size={8} />}
      {level}
    </span>
  )
}

function ExplainDrawer({ log, onClose }) {
  if (!log) return null
  return (
    <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 24 }} className="fixed right-0 top-0 h-full w-96 glass border-l border-white/8 z-50 overflow-y-auto">
      <div className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">Explainability Report</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white">
            <EyeOff size={14} />
          </button>
        </div>
        <div className="glass-light rounded-xl p-3 space-y-2 text-xs font-mono">
          <div className="flex justify-between"><span className="text-slate-500">User</span><span className="text-white">{log.username}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Role</span><span className="text-white">{log.role}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Category</span><span className="text-white">{log.category || 'Unmatched'}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Time</span><span className="text-white">{format(new Date(log.timestamp), 'MMM dd HH:mm:ss')}</span></div>
          <div className="flex justify-between items-center"><span className="text-slate-500">Risk</span><RiskBadge level={log.risk_level || 'low'} /></div>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Query</p>
          <div className="glass-light rounded-xl p-3 text-xs text-slate-300 leading-relaxed">{log.query}</div>
        </div>
        {log.reason && (
          <div>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Reason</p>
            <div className="glass-light rounded-xl p-3 text-xs border border-warn/20 text-warn/90">{log.reason}</div>
          </div>
        )}
        {log.triggered_rules?.length > 0 && (
          <div>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Triggered Rules</p>
            <div className="space-y-1">
              {log.triggered_rules.map(rule => <div key={rule} className="px-3 py-2 rounded-lg bg-danger/8 border border-danger/15 text-danger/80 text-[11px]">{rule}</div>)}
            </div>
          </div>
        )}
        {log.filtered_response && (
          <div>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Delivered Response</p>
            <div className="glass-light rounded-xl p-3 text-[11px] text-slate-400 leading-relaxed max-h-48 overflow-y-auto">{log.filtered_response}</div>
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default function DashboardPage() {
  const [logs, setLogs] = useState([])
  const [stats, setStats] = useState(null)
  const [roles, setRoles] = useState([])
  const [adminUsers, setAdminUsers] = useState([])
  const [userSummary, setUserSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [filterUser, setFilterUser] = useState('')
  const [filterQuery, setFilterQuery] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterRisk, setFilterRisk] = useState('')
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedLog, setSelectedLog] = useState(null)
  const [userSearch, setUserSearch] = useState('')
  const [userRoleFilter, setUserRoleFilter] = useState('')
  const [userStatusFilter, setUserStatusFilter] = useState('')
  const [userMessage, setUserMessage] = useState('')
  const [userError, setUserError] = useState('')
  const [roleForm, setRoleForm] = useState({
    id: null,
    name: '',
    permissions: '{\n  "allowed_intents": ["general_info"],\n  "restricted_keywords": [],\n  "mask_pii": false,\n  "can_manage_roles": false\n}',
  })
  const [roleMessage, setRoleMessage] = useState('')
  const [roleError, setRoleError] = useState('')
  const [savingRole, setSavingRole] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [logsRes, statsRes, rolesRes, usersRes] = await Promise.all([
        api.get('/logs', {
          params: {
            page,
            per_page: 15,
            username: filterUser || undefined,
            query: filterQuery || undefined,
            category: filterCategory || undefined,
            status: filterStatus || undefined,
            risk_level: filterRisk || undefined,
          },
        }),
        api.get('/logs/stats'),
        api.get('/roles'),
        api.get('/admin/users', {
          params: {
            search: userSearch || undefined,
            role: userRoleFilter || undefined,
            status: userStatusFilter || undefined,
          },
        }),
      ])
      setLogs(logsRes.data.logs || [])
      setTotalPages(logsRes.data.pages || 1)
      setStats(statsRes.data)
      setRoles(rolesRes.data.roles || [])
      setAdminUsers(usersRes.data.users || [])
      setUserSummary(usersRes.data.summary || null)
    } finally {
      setLoading(false)
    }
  }, [page, filterUser, filterQuery, filterCategory, filterStatus, filterRisk, userSearch, userRoleFilter, userStatusFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const exportLogs = async () => {
    const res = await api.get('/logs/export', { responseType: 'blob' })
    const url = window.URL.createObjectURL(res.data)
    const link = document.createElement('a')
    link.href = url
    link.download = 'secureai-audit-logs.csv'
    link.click()
    window.URL.revokeObjectURL(url)
  }

  const statusPieData = stats ? [
    { name: 'Allowed', value: stats.allowed },
    { name: 'Filtered', value: stats.filtered },
    { name: 'Blocked', value: stats.blocked },
  ].filter(item => item.value > 0) : []

  const userBarData = stats?.by_user?.map(item => ({
    username: item.username,
    total: item.count,
    blocked: item.blocked,
  })) || []

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'logs', label: 'Audit Logs' },
    { id: 'threats', label: `Threats ${stats?.suspicious_users?.length ? `(${stats.suspicious_users.length})` : ''}` },
    { id: 'users', label: `Users ${adminUsers.length ? `(${adminUsers.length})` : ''}` },
    { id: 'roles', label: `Roles ${roles.length ? `(${roles.length})` : ''}` },
  ]

  const exportUsersPdf = async () => {
    const res = await api.get('/admin/users/export/pdf', { responseType: 'blob' })
    const url = window.URL.createObjectURL(res.data)
    const link = document.createElement('a')
    link.href = url
    link.download = 'secureai-admin-user-directory.pdf'
    link.click()
    window.URL.revokeObjectURL(url)
  }

  const updateUser = async (userId, payload, successMessage) => {
    setUserError('')
    setUserMessage('')
    try {
      await api.patch(`/admin/users/${userId}`, payload)
      setUserMessage(successMessage)
      fetchData()
    } catch (err) {
      setUserError(err?.response?.data?.error || 'Unable to update that user right now.')
    }
  }

  const resetRoleForm = (clearNotices = true) => {
    setRoleForm({
      id: null,
      name: '',
      permissions: '{\n  "allowed_intents": ["general_info"],\n  "restricted_keywords": [],\n  "mask_pii": false,\n  "can_manage_roles": false\n}',
    })
    if (clearNotices) {
      setRoleError('')
      setRoleMessage('')
    }
  }

  const editRole = role => {
    setRoleForm({
      id: role.id,
      name: role.name,
      permissions: JSON.stringify(role.permissions || {}, null, 2),
    })
    setRoleError('')
    setRoleMessage('')
    setActiveTab('roles')
  }

  const saveRole = async () => {
    setRoleError('')
    setRoleMessage('')

    let permissions
    try {
      permissions = JSON.parse(roleForm.permissions)
    } catch {
      setRoleError('Permissions must be valid JSON.')
      return
    }

    setSavingRole(true)
    try {
      if (roleForm.id) {
        await api.put(`/roles/${roleForm.id}`, { name: roleForm.name, permissions })
        setRoleMessage('Role updated successfully.')
      } else {
        await api.post('/roles', { name: roleForm.name, permissions })
        setRoleMessage('Role created successfully.')
      }
      resetRoleForm(false)
      fetchData()
    } catch (err) {
      setRoleError(err?.response?.data?.error || 'Unable to save role right now.')
    } finally {
      setSavingRole(false)
    }
  }

  const removeRole = async role => {
    setRoleError('')
    setRoleMessage('')
    try {
      await api.delete(`/roles/${role.id}`)
      setRoleMessage(`Deleted role ${formatRoleName(role.name)}.`)
      if (roleForm.id === role.id) {
        resetRoleForm()
      }
      fetchData()
    } catch (err) {
      setRoleError(err?.response?.data?.error || 'Unable to delete that role.')
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <AnimatePresence>
        {selectedLog && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSelectedLog(null)} className="fixed inset-0 bg-black/40 z-40 backdrop-blur-sm" />
            <ExplainDrawer log={selectedLog} onClose={() => setSelectedLog(null)} />
          </>
        )}
      </AnimatePresence>

      <div className="px-6 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Governance Dashboard</h1>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5 tracking-widest uppercase">Audit, analytics, dataset coverage, and review signals</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={exportLogs} className="px-3 py-2 rounded-lg glass-light border border-white/8 text-slate-400 hover:text-accent text-xs font-mono">
              <Download size={13} className="inline mr-1.5" />Export Logs
            </button>
            <motion.button whileHover={{ rotate: 180 }} transition={{ duration: 0.35 }} onClick={fetchData} className="p-2 rounded-lg glass-light border border-white/8 text-slate-400 hover:text-accent">
              <RefreshCw size={15} />
            </motion.button>
          </div>
        </div>

        <div className="flex gap-1 p-1 glass-light rounded-xl border border-white/6 w-fit">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`px-4 py-1.5 rounded-lg text-xs font-semibold ${activeTab === tab.id ? 'bg-accent text-bg-900 shadow-glow' : 'text-slate-400 hover:text-white'}`}>
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'overview' && stats && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard icon={Activity} label="Total Queries" value={stats.total} color="#00e5ff" />
              <StatCard icon={ShieldCheck} label="Allowed" value={stats.allowed} color="#06d6a0" />
              <StatCard icon={ShieldAlert} label="Filtered" value={stats.filtered} color="#ffb703" />
              <StatCard icon={Lock} label="Blocked" value={stats.blocked} color="#ff4d6d" />
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard icon={TrendingUp} label="High Risk Alerts" value={stats.high_risk_alerts} color="#ff4d6d" />
              <StatCard icon={Database} label="Dataset Questions" value={stats.question_bank_total || 0} color="#60a5fa" />
              <StatCard icon={MessageCircleQuestion} label="Open Review Queue" value={stats.unanswered_count || 0} color="#fb7185" />
              <StatCard icon={ThumbsDown} label="Low Quality Responses" value={stats.low_quality_responses?.length || 0} color="#f97316" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 glass rounded-2xl p-5 border border-white/5">
                <p className="text-xs font-bold text-white mb-1">Queries Per User</p>
                <p className="text-[10px] text-slate-600 font-mono mb-4">Total vs blocked breakdown</p>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={userBarData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="username" tick={{ fill: '#64748b', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                    <Tooltip content={<ChartTooltip />} />
                    <Bar dataKey="total" fill="#00e5ff" radius={[4, 4, 0, 0]} name="Total" />
                    <Bar dataKey="blocked" fill="#ff4d6d" radius={[4, 4, 0, 0]} name="Blocked" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="glass rounded-2xl p-5 border border-white/5">
                <p className="text-xs font-bold text-white mb-1">Response Status</p>
                <p className="text-[10px] text-slate-600 font-mono mb-3">Distribution</p>
                {statusPieData.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={150}>
                      <PieChart>
                        <Pie data={statusPieData} cx="50%" cy="50%" innerRadius={36} outerRadius={60} dataKey="value" stroke="none">
                          {statusPieData.map(entry => <Cell key={entry.name} fill={STATUS_COLORS[entry.name.toLowerCase()]} />)}
                        </Pie>
                        <Tooltip content={<ChartTooltip />} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="space-y-1.5">
                      {statusPieData.map(item => (
                        <div key={item.name} className="flex items-center justify-between text-[11px] font-mono">
                          <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full" style={{ background: STATUS_COLORS[item.name.toLowerCase()] }} /><span className="text-slate-400">{item.name}</span></div>
                          <span className="text-white font-bold">{item.value}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : <p className="text-slate-600 text-xs text-center py-8">No data yet</p>}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="glass rounded-2xl p-5 border border-white/5">
                <p className="text-xs font-bold text-white mb-3">Most Asked Questions</p>
                <div className="space-y-2">
                  {(stats.top_questions || []).map(item => (
                    <div key={item.question} className="px-3 py-2 rounded-xl bg-bg-800/70 border border-white/8">
                      <p className="text-sm text-white">{item.question}</p>
                      <p className="text-[10px] font-mono text-slate-500 mt-1">{item.count} exact asks</p>
                    </div>
                  ))}
                  {!stats.top_questions?.length && <p className="text-xs text-slate-500">No matched dataset usage yet.</p>}
                </div>
              </div>
              <div className="glass rounded-2xl p-5 border border-white/5">
                <p className="text-xs font-bold text-white mb-3">Blocked Queries By Role</p>
                <div className="space-y-2">
                  {Object.entries(stats.blocked_by_role || {}).map(([role, count]) => (
                    <div key={role} className="flex items-center justify-between px-3 py-2 rounded-xl bg-bg-800/70 border border-white/8">
                      <span className="text-sm text-slate-300 uppercase">{role}</span>
                      <span className="text-sm font-bold text-danger">{count}</span>
                    </div>
                  ))}
                  {!Object.keys(stats.blocked_by_role || {}).length && <p className="text-xs text-slate-500">No blocked activity by role yet.</p>}
                </div>
              </div>
              <div className="glass rounded-2xl p-5 border border-white/5">
                <p className="text-xs font-bold text-white mb-3">Open Unanswered Queries</p>
                <div className="space-y-2">
                  {(stats.open_unanswered || []).map(item => (
                    <div key={item.id} className="px-3 py-2 rounded-xl bg-bg-800/70 border border-white/8">
                      <p className="text-sm text-white">{item.query}</p>
                      <p className="text-[10px] font-mono text-slate-500 mt-1">{item.count} time(s) · latest {item.latest_username}</p>
                    </div>
                  ))}
                  {!stats.open_unanswered?.length && <p className="text-xs text-slate-500">No unanswered items in the queue.</p>}
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'logs' && (
          <>
            <div className="flex gap-2 flex-wrap items-center">
              {[
                { value: filterUser, setter: setFilterUser, placeholder: 'Filter user...', width: 'w-40' },
                { value: filterQuery, setter: setFilterQuery, placeholder: 'Search query...', width: 'w-44' },
                { value: filterCategory, setter: setFilterCategory, placeholder: 'Category...', width: 'w-36' },
              ].map(item => (
                <div key={item.placeholder} className="relative">
                  <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input value={item.value} onChange={e => { item.setter(e.target.value); setPage(1) }} placeholder={item.placeholder} className={`pl-8 pr-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-white placeholder-slate-600 focus:outline-none focus:border-accent/50 text-xs font-mono ${item.width}`} />
                </div>
              ))}
              {[
                { val: filterStatus, set: setFilterStatus, options: ['', 'allowed', 'filtered', 'blocked'], placeholder: 'Status' },
                { val: filterRisk, set: setFilterRisk, options: ['', 'low', 'medium', 'high'], placeholder: 'Risk' },
              ].map(item => (
                <div key={item.placeholder} className="relative">
                  <Filter size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <select value={item.val} onChange={e => { item.set(e.target.value); setPage(1) }} className="pl-7 pr-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-white focus:outline-none focus:border-accent/50 text-xs appearance-none">
                    <option value="">{item.placeholder}: All</option>
                    {item.options.slice(1).map(option => <option key={option} value={option}>{option}</option>)}
                  </select>
                </div>
              ))}
            </div>

            <div className="glass rounded-2xl border border-white/5 overflow-hidden">
              <div className="px-5 py-3.5 border-b border-white/5 flex items-center justify-between">
                <p className="text-xs font-bold text-white">Audit Log</p>
                <span className="text-[10px] text-slate-500 font-mono">{logs.length} entries shown</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-[11px] font-mono">
                  <thead>
                    <tr className="border-b border-white/5 text-slate-500 uppercase tracking-wider text-[10px]">
                      {['Time', 'User', 'Role', 'Category', 'Query', 'Status', 'Risk', 'Explain'].map(header => (
                        <th key={header} className="px-4 py-3 text-left font-semibold">{header}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr><td colSpan={8} className="text-center py-12 text-slate-600">Loading...</td></tr>
                    ) : !logs.length ? (
                      <tr><td colSpan={8} className="text-center py-12 text-slate-600">No logs match current filters</td></tr>
                    ) : logs.map(log => (
                      <tr key={log.id} className={`border-b border-white/5 transition-colors ${log.is_high_risk ? 'hover:bg-danger/5 bg-danger/3' : 'hover:bg-white/5'}`}>
                        <td className="px-4 py-3 text-slate-500 whitespace-nowrap">{format(new Date(log.timestamp), 'MM/dd HH:mm:ss')}</td>
                        <td className="px-4 py-3 text-slate-300 font-semibold">{log.username}</td>
                        <td className="px-4 py-3 text-slate-400 uppercase">{log.role}</td>
                        <td className="px-4 py-3 text-slate-400">{log.category || 'Unmatched'}</td>
                        <td className="px-4 py-3 text-slate-400 max-w-[180px] truncate">{log.query}</td>
                        <td className="px-4 py-3"><span className={`uppercase text-[10px] font-bold px-1.5 py-0.5 rounded border ${log.status === 'allowed' ? 'text-success bg-success/10 border-success/20' : log.status === 'filtered' ? 'text-warn bg-warn/10 border-warn/20' : 'text-danger bg-danger/10 border-danger/20'}`}>{log.status}</span></td>
                        <td className="px-4 py-3"><RiskBadge level={log.risk_level || 'low'} /></td>
                        <td className="px-4 py-3">
                          <button onClick={() => setSelectedLog(log)} className="p-1.5 rounded-lg bg-white/5 hover:bg-accent/10 text-slate-500 hover:text-accent border border-transparent hover:border-accent/20">
                            <Eye size={12} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-3 py-4 border-t border-white/5">
                  <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="p-1.5 rounded-lg hover:bg-white/5 text-slate-400 disabled:opacity-30">
                    <ChevronLeft size={14} />
                  </button>
                  <span className="text-[11px] text-slate-500 font-mono">Page {page} / {totalPages}</span>
                  <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="p-1.5 rounded-lg hover:bg-white/5 text-slate-400 disabled:opacity-30">
                    <ChevronRight size={14} />
                  </button>
                </div>
              )}
            </div>
          </>
        )}

        {activeTab === 'threats' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="glass rounded-2xl p-5 border border-white/5">
              <div className="flex items-center gap-2 mb-4">
                <UserX size={15} className="text-danger" />
                <h3 className="text-sm font-bold text-white">Suspicious Users</h3>
              </div>
              <div className="space-y-2">
                {(stats?.suspicious_users || []).map(user => (
                  <div key={user.id} className="flex items-center gap-3 px-4 py-3 rounded-xl border border-danger/20 bg-danger/5">
                    <div className="w-8 h-8 rounded-full bg-danger/20 border border-danger/30 flex items-center justify-center text-xs font-bold text-danger">{user.username[0].toUpperCase()}</div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-white">{user.username}</p>
                      <p className="text-[10px] text-slate-500 font-mono">{user.sensitive_query_count} sensitive quer{user.sensitive_query_count === 1 ? 'y' : 'ies'} · flagged {user.flagged_at ? formatDistanceToNow(new Date(user.flagged_at)) : 'recently'} ago</p>
                    </div>
                  </div>
                ))}
                {!stats?.suspicious_users?.length && <p className="text-xs text-slate-500">No suspicious users detected.</p>}
              </div>
            </div>

            <div className="glass rounded-2xl p-5 border border-white/5">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle size={15} className="text-danger" />
                <h3 className="text-sm font-bold text-white">Recent High-Risk Query Log</h3>
              </div>
              <div className="space-y-2">
                {(stats?.recent_high_risk || []).map(log => (
                  <button key={log.id} onClick={() => setSelectedLog(log)} className="w-full flex items-start gap-3 px-4 py-3 rounded-xl bg-danger/5 border border-danger/15 text-left hover:bg-danger/10">
                    <div className="w-8 h-8 rounded-xl bg-danger/20 border border-danger/30 flex items-center justify-center flex-shrink-0">
                      <AlertTriangle size={13} className="text-danger" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-white">{log.username}</span>
                        <RiskBadge level={log.risk_level || 'high'} />
                      </div>
                      <p className="text-[11px] text-slate-400 truncate font-mono">{log.query}</p>
                    </div>
                  </button>
                ))}
                {!stats?.recent_high_risk?.length && <p className="text-xs text-slate-500">No high-risk events logged.</p>}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'users' && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard icon={Users} label="Visible Users" value={userSummary?.total_users || 0} color="#60a5fa" />
              <StatCard icon={UserCheck} label="Active Users" value={userSummary?.active_users || 0} color="#06d6a0" />
              <StatCard icon={UserMinus} label="Inactive Users" value={userSummary?.inactive_users || 0} color="#f97316" />
              <StatCard icon={ShieldAlert} label="Suspicious Users" value={userSummary?.suspicious_users || 0} color="#ff4d6d" />
            </div>

            <div className="flex gap-2 flex-wrap items-center">
              <div className="relative">
                <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  value={userSearch}
                  onChange={e => setUserSearch(e.target.value)}
                  placeholder="Search username or email..."
                  className="pl-8 pr-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-white placeholder-slate-600 focus:outline-none focus:border-accent/50 text-xs font-mono w-56"
                />
              </div>
              <select value={userRoleFilter} onChange={e => setUserRoleFilter(e.target.value)} className="px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-white focus:outline-none focus:border-accent/50 text-xs">
                <option value="">All roles</option>
                {roles.map(role => <option key={role.id} value={role.name}>{formatRoleName(role.name)}</option>)}
              </select>
              <select value={userStatusFilter} onChange={e => setUserStatusFilter(e.target.value)} className="px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-white focus:outline-none focus:border-accent/50 text-xs">
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
              <button onClick={exportUsersPdf} className="px-3 py-2 rounded-lg glass-light border border-white/8 text-slate-300 hover:text-accent text-xs font-mono">
                <FileText size={13} className="inline mr-1.5" />Download PDF
              </button>
            </div>

            {userMessage && <div className="px-3 py-2 rounded-xl bg-success/10 border border-success/20 text-xs text-success">{userMessage}</div>}
            {userError && <div className="px-3 py-2 rounded-xl bg-danger/10 border border-danger/20 text-xs text-danger">{userError}</div>}

            <div className="glass rounded-2xl border border-white/5 overflow-hidden">
              <div className="px-5 py-3.5 border-b border-white/5 flex items-center justify-between">
                <p className="text-xs font-bold text-white">Registered Users</p>
                <span className="text-[10px] text-slate-500 font-mono">Passwords are securely hashed and cannot be exported as plaintext</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-[11px] font-mono">
                  <thead>
                    <tr className="border-b border-white/5 text-slate-500 uppercase tracking-wider text-[10px]">
                      {['User', 'Role', 'Status', 'Registered', 'Last Login', 'Counts', 'Face', 'Actions'].map(header => (
                        <th key={header} className="px-4 py-3 text-left font-semibold">{header}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {!adminUsers.length ? (
                      <tr><td colSpan={8} className="text-center py-12 text-slate-600">No users matched the current filters.</td></tr>
                    ) : adminUsers.map(user => (
                      <tr key={user.id} className="border-b border-white/5 hover:bg-white/5">
                        <td className="px-4 py-3">
                          <div className="space-y-1">
                            <div className="text-slate-200 font-semibold">{user.username}</div>
                            <div className="text-slate-500">{user.email}</div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={user.role}
                            onChange={e => updateUser(user.id, { role: e.target.value }, `Updated ${user.username}'s role.`)}
                            className="px-2 py-1.5 rounded-lg bg-bg-800 border border-white/8 text-white text-xs"
                          >
                            {roles.map(role => <option key={role.id} value={role.name}>{formatRoleName(role.name)}</option>)}
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`uppercase text-[10px] font-bold px-1.5 py-0.5 rounded border ${user.is_active ? 'text-success bg-success/10 border-success/20' : 'text-warn bg-warn/10 border-warn/20'}`}>
                            {user.is_active ? 'active' : 'inactive'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400 whitespace-nowrap">{user.created_at ? format(new Date(user.created_at), 'MM/dd/yyyy HH:mm') : '-'}</td>
                        <td className="px-4 py-3 text-slate-400 whitespace-nowrap">{user.last_login_at ? format(new Date(user.last_login_at), 'MM/dd/yyyy HH:mm') : 'Never'}</td>
                        <td className="px-4 py-3 text-slate-400">
                          <div>OK: {user.login_count || 0}</div>
                          <div>Fail: {user.failed_login_count || 0}</div>
                        </td>
                        <td className="px-4 py-3 text-slate-400">{user.has_face_profile ? 'Registered' : 'No face'}</td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => updateUser(user.id, { is_active: !user.is_active }, user.is_active ? `Deactivated ${user.username}.` : `Activated ${user.username}.`)}
                            className={`px-3 py-1.5 rounded-lg border text-xs ${user.is_active ? 'border-danger/20 text-danger' : 'border-success/20 text-success'}`}
                          >
                            {user.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {activeTab === 'roles' && (
          <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-4">
            <div className="glass rounded-2xl p-5 border border-white/5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-white">Enterprise Roles</h3>
                  <p className="text-[10px] text-slate-500 font-mono mt-1">Create or revise role permissions without code changes</p>
                </div>
                <button onClick={resetRoleForm} className="px-3 py-2 rounded-lg glass-light border border-white/8 text-slate-300 text-xs font-mono">
                  New Role
                </button>
              </div>

              <div className="space-y-3">
                {roles.map(role => (
                  <div key={role.id} className="rounded-2xl border border-white/8 bg-bg-800/60 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-white">{formatRoleName(role.name)}</p>
                        <p className="text-[10px] font-mono text-slate-500 mt-1">
                          intents: {(role.allowed_intents || []).join(', ') || 'none'} · keywords: {(role.restricted_keywords || []).length}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => editRole(role)} className="px-3 py-1.5 rounded-lg border border-white/8 text-xs text-slate-300 hover:text-accent hover:border-accent/20">
                          Edit
                        </button>
                        <button
                          onClick={() => removeRole(role)}
                          disabled={role.name === 'admin'}
                          className="px-3 py-1.5 rounded-lg border border-danger/20 text-xs text-danger disabled:opacity-40"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                      <div className="rounded-xl bg-white/5 border border-white/8 p-3">
                        <p className="text-slate-500 font-mono uppercase mb-2">Allowed Intents</p>
                        <div className="flex flex-wrap gap-2">
                          {(role.allowed_intents || []).map(intent => (
                            <span key={intent} className="px-2 py-1 rounded-lg bg-accent/10 border border-accent/20 text-accent">
                              {intent}
                            </span>
                          ))}
                          {!role.allowed_intents?.length && <span className="text-slate-500">None</span>}
                        </div>
                      </div>
                      <div className="rounded-xl bg-white/5 border border-white/8 p-3">
                        <p className="text-slate-500 font-mono uppercase mb-2">Restricted Keywords</p>
                        <div className="flex flex-wrap gap-2">
                          {(role.restricted_keywords || []).map(keyword => (
                            <span key={keyword} className="px-2 py-1 rounded-lg bg-danger/10 border border-danger/20 text-danger">
                              {keyword}
                            </span>
                          ))}
                          {!role.restricted_keywords?.length && <span className="text-slate-500">None</span>}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {!roles.length && <p className="text-xs text-slate-500">No roles available.</p>}
              </div>
            </div>

            <div className="glass rounded-2xl p-5 border border-white/5">
              <h3 className="text-sm font-bold text-white">{roleForm.id ? 'Edit Role' : 'Create Role'}</h3>
              <p className="text-[10px] text-slate-500 font-mono mt-1 mb-4">Permissions are stored as JSON and applied by the governance layer.</p>

              {roleMessage && <div className="mb-3 px-3 py-2 rounded-xl bg-success/10 border border-success/20 text-xs text-success">{roleMessage}</div>}
              {roleError && <div className="mb-3 px-3 py-2 rounded-xl bg-danger/10 border border-danger/20 text-xs text-danger">{roleError}</div>}

              <div className="space-y-3">
                <div>
                  <label className="block text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1.5">Role Name</label>
                  <input
                    value={roleForm.name}
                    onChange={e => setRoleForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="security analyst"
                    className="w-full px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-sm text-white placeholder-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1.5">Permissions JSON</label>
                  <textarea
                    rows={16}
                    value={roleForm.permissions}
                    onChange={e => setRoleForm(prev => ({ ...prev, permissions: e.target.value }))}
                    className="w-full px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-sm text-white placeholder-slate-600 resize-none font-mono"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={saveRole} disabled={savingRole} className="px-4 py-2 rounded-xl bg-accent text-bg-900 text-sm font-semibold disabled:opacity-50">
                    {savingRole ? 'Saving...' : roleForm.id ? 'Update Role' : 'Create Role'}
                  </button>
                  <button onClick={resetRoleForm} className="px-4 py-2 rounded-xl bg-white/5 border border-white/8 text-sm text-slate-300">
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
