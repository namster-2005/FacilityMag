import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getTicket, updateTicket, addComment, type Ticket } from '../lib/api'
import { useAuth } from '../lib/auth'
import Badge from '../components/Badge'
import Layout from '../components/Layout'

const NEXT_STATUS: Record<string, string> = {
  'Open': 'In Progress',
  'In Progress': 'Resolved',
}

export default function TicketDetail() {
  const { id }                        = useParams<{ id: string }>()
  const { user }                      = useAuth()
  const [ticket, setTicket]           = useState<Ticket | null>(null)
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState('')
  const [comment, setComment]         = useState('')
  const [submitting, setSubmitting]   = useState(false)
  const [statusLoading, setStatusLoading] = useState(false)

  async function load() {
    if (!id) return
    setLoading(true)
    try {
      const res = await getTicket(id)
      setTicket(res.data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error loading ticket')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  async function handleStatusAdvance() {
    if (!ticket || !id) return
    const next = NEXT_STATUS[ticket.status]
    if (!next) return
    setStatusLoading(true)
    try {
      await updateTicket(id, { status: next as Ticket['status'] })
      load()
    } finally {
      setStatusLoading(false)
    }
  }

  async function handleComment(e: React.FormEvent) {
    e.preventDefault()
    if (!id || !comment.trim()) return
    setSubmitting(true)
    try {
      await addComment(id, comment.trim())
      setComment('')
      load()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Error adding comment')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <Layout><div className="text-center py-20 text-gray-400">Loading…</div></Layout>
  if (error)   return <Layout><div className="text-red-600 p-4">{error}</div></Layout>
  if (!ticket) return null

  const canAdvance = !!NEXT_STATUS[ticket.status] && (user?.role === 'staff' || user?.role === 'admin')

  return (
    <Layout>
      <div className="space-y-6 max-w-3xl">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Link to="/tickets" className="hover:text-emerald-700">Tickets</Link>
          <span>/</span>
          <span className="font-mono">{ticket.id.slice(0, 8)}</span>
        </div>

        {/* Ticket card */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div className="flex items-start justify-between">
            <h1 className="text-xl font-bold text-gray-900 flex-1 mr-4">{ticket.title}</h1>
            <div className="flex gap-2 shrink-0">
              <Badge label={ticket.status} variant="status" />
              <Badge label={ticket.priority} variant="priority" />
            </div>
          </div>

          {ticket.description && <p className="text-sm text-gray-600">{ticket.description}</p>}

          <div className="grid grid-cols-2 gap-3 text-sm">
            <Detail label="Asset" value={<Link to={`/assets/${ticket.asset_id}`} className="text-emerald-700 hover:underline">{ticket.asset_id} — {ticket.asset_name}</Link>} />
            <Detail label="Reporter" value={ticket.reporter_name ?? '—'} />
            <Detail label="Assigned to" value={ticket.assignee_name ?? 'Unassigned'} />
            <Detail label="Due date" value={ticket.due_date ?? '—'} />
            {ticket.resolution_note && <Detail label="Resolution" value={ticket.resolution_note} />}
          </div>

          {canAdvance && (
            <button
              onClick={handleStatusAdvance}
              disabled={statusLoading}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              {statusLoading ? 'Updating…' : `Mark as ${NEXT_STATUS[ticket.status]}`}
            </button>
          )}
        </div>

        {/* Comments */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Comments ({ticket.comments?.length ?? 0})</h2>

          {(ticket.comments?.length ?? 0) > 0 && (
            <div className="space-y-3">
              {ticket.comments!.map(c => (
                <div key={c.id} className="bg-gray-50 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-gray-700">{c.user_name ?? 'User'}</span>
                    <span className="text-xs text-gray-400">{c.created_at?.replace('T', ' ')}</span>
                  </div>
                  <p className="text-sm text-gray-700">{c.body}</p>
                </div>
              ))}
            </div>
          )}

          {(user?.role === 'staff' || user?.role === 'admin') && (
            <form onSubmit={handleComment} className="space-y-2">
              <textarea
                value={comment}
                onChange={e => setComment(e.target.value)}
                rows={3}
                placeholder="Add a comment…"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
              <button
                type="submit"
                disabled={submitting || !comment.trim()}
                className="bg-slate-700 hover:bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 transition"
              >
                {submitting ? 'Posting…' : 'Post comment'}
              </button>
            </form>
          )}
        </div>
      </div>
    </Layout>
  )
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-gray-400 uppercase font-medium mb-0.5">{label}</div>
      <div className="text-sm text-gray-700">{value}</div>
    </div>
  )
}
