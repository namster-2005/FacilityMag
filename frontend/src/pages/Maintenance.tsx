import { useEffect, useState } from 'react'
import { listMaintenance, createMaintenance, completeTask, listLocations, type MaintenanceTask, type Location } from '../lib/api'
import { useAuth } from '../lib/auth'
import Badge from '../components/Badge'
import Layout from '../components/Layout'

const FREQUENCIES = ['daily','weekly','monthly','quarterly','annual','once'] as const

export default function Maintenance() {
  const { user }                        = useAuth()
  const [tasks, setTasks]               = useState<MaintenanceTask[]>([])
  const [locations, setLocations]       = useState<Location[]>([])
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterFreq, setFilterFreq]     = useState('')
  const [overdueOnly, setOverdueOnly]   = useState(false)
  const [expanded, setExpanded]         = useState<string | null>(null)
  const [showForm, setShowForm]         = useState(false)
  const [newTask, setNewTask]           = useState<Partial<MaintenanceTask>>({ frequency: 'weekly' })
  const [saving, setSaving]             = useState(false)

  const today = new Date().toISOString().split('T')[0]

  async function load() {
    setLoading(true)
    const params: Record<string, string> = {}
    if (filterStatus) params.status    = filterStatus
    if (filterFreq)   params.frequency = filterFreq
    if (overdueOnly)  params.overdue   = 'true'
    try {
      const [taskRes, locRes] = await Promise.all([listMaintenance(params), listLocations()])
      setTasks(taskRes.data)
      setLocations(locRes.data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error loading tasks')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filterStatus, filterFreq, overdueOnly])

  async function handleComplete(taskId: string) {
    try {
      await completeTask(taskId)
      load()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Error completing task')
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await createMaintenance(newTask)
      setShowForm(false)
      setNewTask({ frequency: 'weekly' })
      load()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Error creating task')
    } finally {
      setSaving(false)
    }
  }

  const isOverdue = (t: MaintenanceTask) =>
    t.status === 'Overdue' || (t.next_due != null && t.next_due < today && t.status !== 'Done')

  return (
    <Layout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Maintenance</h1>
          {user?.role === 'admin' && (
            <button onClick={() => setShowForm(!showForm)} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
              + New Task
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 items-center">
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">All Statuses</option>
            {['Pending','In Progress','Done','Overdue'].map(s => <option key={s}>{s}</option>)}
          </select>
          <select value={filterFreq} onChange={e => setFilterFreq(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">All Frequencies</option>
            {FREQUENCIES.map(f => <option key={f}>{f}</option>)}
          </select>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={overdueOnly} onChange={e => setOverdueOnly(e.target.checked)} className="rounded" />
            Overdue only
          </label>
        </div>

        {/* New task form */}
        {showForm && (
          <form onSubmit={handleCreate} className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-gray-900">New Task</h3>
            <div className="grid grid-cols-2 gap-4">
              <input required placeholder="Title" value={newTask.title ?? ''} onChange={e => setNewTask(p => ({ ...p, title: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm col-span-2" />
              <select value={newTask.frequency} onChange={e => setNewTask(p => ({ ...p, frequency: e.target.value as MaintenanceTask['frequency'] }))} className="border rounded-lg px-3 py-2 text-sm">
                {FREQUENCIES.map(f => <option key={f}>{f}</option>)}
              </select>
              <input type="date" value={newTask.next_due ?? ''} onChange={e => setNewTask(p => ({ ...p, next_due: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
              <select value={newTask.location_id ?? ''} onChange={e => setNewTask(p => ({ ...p, location_id: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm">
                <option value="">No location</option>
                {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={saving} className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm">{saving ? 'Saving…' : 'Create'}</button>
              <button type="button" onClick={() => setShowForm(false)} className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm">Cancel</button>
            </div>
          </form>
        )}

        {/* Task list */}
        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading…</div>
        ) : error ? (
          <div className="text-red-600">{error}</div>
        ) : (
          <div className="space-y-3">
            {tasks.map(t => (
              <div key={t.id} className={`bg-white rounded-xl border p-4 ${isOverdue(t) ? 'border-red-300 bg-red-50' : 'border-gray-200'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <button onClick={() => setExpanded(expanded === t.id ? null : t.id)} className="text-gray-400 hover:text-gray-600 text-xs">
                      {expanded === t.id ? '▼' : '▶'}
                    </button>
                    <div>
                      <div className="font-medium text-gray-900 text-sm">{t.title}</div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {t.frequency} · {t.asset_name ? `${t.asset_name} · ` : ''}{t.location_name ?? ''}
                        {t.next_due && ` · Due: ${t.next_due}`}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge label={t.status} variant="status" />
                    {(user?.role === 'staff' || user?.role === 'admin') && t.status !== 'Done' && (
                      <button onClick={() => handleComplete(t.id)} className="bg-emerald-100 hover:bg-emerald-200 text-emerald-700 px-3 py-1.5 rounded-lg text-xs font-medium transition">
                        ✓ Complete
                      </button>
                    )}
                  </div>
                </div>

                {expanded === t.id && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    {t.description && <p className="text-sm text-gray-600 mb-2">{t.description}</p>}
                    {t.checklist_json && (() => {
                      try {
                        const items: string[] = JSON.parse(t.checklist_json)
                        if (items.length > 0) return (
                          <ul className="space-y-1">
                            {items.map((item, i) => (
                              <li key={i} className="flex items-center gap-2 text-sm text-gray-600">
                                <span className="w-4 h-4 border border-gray-300 rounded shrink-0" />
                                {item}
                              </li>
                            ))}
                          </ul>
                        )
                      } catch { return null }
                      return null
                    })()}
                    {t.assignee_name && <div className="text-xs text-gray-400 mt-2">Assigned to: {t.assignee_name}</div>}
                    {t.last_done_at && <div className="text-xs text-gray-400">Last done: {t.last_done_at.split('T')[0]}</div>}
                  </div>
                )}
              </div>
            ))}
            {tasks.length === 0 && <div className="text-center text-gray-400 py-8">No tasks found</div>}
          </div>
        )}
      </div>
    </Layout>
  )
}
