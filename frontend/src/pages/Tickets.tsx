import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listTickets, listAssets, updateTicket, type Ticket, type Asset } from '../lib/api'
import { useAuth } from '../lib/auth'
import Badge from '../components/Badge'
import Layout from '../components/Layout'

const STATUSES  = ['', 'Open', 'In Progress', 'Resolved', 'Closed']
const PRIORITIES = ['', 'Emergency', 'Urgent', 'Standard', 'Low']

export default function Tickets() {
  const { user }                    = useAuth()
  const [tickets, setTickets]       = useState<Ticket[]>([])
  const [staff, setStaff]           = useState<Asset[]>([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState('')
  const [status, setStatus]         = useState('')
  const [priority, setPriority]     = useState('')
  const today                       = new Date().toISOString().split('T')[0]

  async function load() {
    setLoading(true)
    const params: Record<string, string> = {}
    if (status)   params.status   = status
    if (priority) params.priority = priority
    try {
      const res = await listTickets(params)
      setTickets(res.data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error loading tickets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [status, priority])

  async function handleAssign(ticketId: string, assignedTo: string) {
    try {
      await updateTicket(ticketId, { assigned_to: assignedTo })
      load()
    } catch { /* ignore */ }
  }

  const isOverdue = (t: Ticket) => t.due_date && t.due_date < today && !['Resolved','Closed'].includes(t.status)

  return (
    <Layout>
      <div className="space-y-5">
        <h1 className="text-2xl font-bold text-gray-900">Tickets</h1>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <select value={status} onChange={e => setStatus(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
            {STATUSES.map(s => <option key={s} value={s}>{s || 'All Statuses'}</option>)}
          </select>
          <select value={priority} onChange={e => setPriority(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
            {PRIORITIES.map(p => <option key={p} value={p}>{p || 'All Priorities'}</option>)}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading…</div>
        ) : error ? (
          <div className="text-red-600">{error}</div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Title','Asset','Status','Priority','Reporter','Due','Assigned'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tickets.map(t => (
                  <tr key={t.id} className={`hover:bg-gray-50 ${isOverdue(t) ? 'bg-red-50' : ''}`}>
                    <td className="px-4 py-3">
                      <Link to={`/tickets/${t.id}`} className="text-gray-900 hover:text-emerald-700 font-medium">{t.title}</Link>
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      <Link to={`/assets/${t.asset_id}`} className="hover:text-emerald-700">{t.asset_id}</Link>
                    </td>
                    <td className="px-4 py-3"><Badge label={t.status} variant="status" /></td>
                    <td className="px-4 py-3"><Badge label={t.priority} variant="priority" /></td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{t.reporter_name ?? '—'}</td>
                    <td className={`px-4 py-3 text-xs ${isOverdue(t) ? 'text-red-600 font-semibold' : 'text-gray-500'}`}>
                      {t.due_date ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{t.assignee_name ?? '—'}</td>
                  </tr>
                ))}
                {tickets.length === 0 && (
                  <tr><td colSpan={7} className="text-center text-gray-400 py-8">No tickets found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  )
}
