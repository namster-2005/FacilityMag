import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboard, type DashboardData } from '../lib/api'
import Badge from '../components/Badge'
import Layout from '../components/Layout'

export default function Dashboard() {
  const [data, setData]       = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    getDashboard()
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Layout><div className="flex items-center justify-center h-64 text-gray-400">Loading…</div></Layout>
  if (error)   return <Layout><div className="text-red-600 p-4">{error}</div></Layout>
  if (!data)   return null

  const conditionColors: Record<string, string> = {
    Excellent: 'text-emerald-600', Good: 'text-green-600',
    Ok: 'text-yellow-600', Bad: 'text-orange-600', Damaged: 'text-red-600',
  }

  return (
    <Layout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Assets"        value={data.assets.total}           color="bg-slate-50" />
          <StatCard label="Open Tickets"        value={data.tickets.open}           color="bg-blue-50" />
          <StatCard label="Overdue Tickets"     value={data.tickets.overdue}        color={data.tickets.overdue > 0 ? 'bg-red-50' : 'bg-slate-50'} />
          <StatCard label="Overdue Maintenance" value={data.maintenance.overdue}    color={data.maintenance.overdue > 0 ? 'bg-red-50' : 'bg-slate-50'} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Condition breakdown */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-4">Asset Conditions</h2>
            <div className="space-y-2">
              {Object.entries(data.assets.by_condition).map(([condition, count]) => (
                <div key={condition} className="flex items-center justify-between">
                  <Badge label={condition} variant="condition" />
                  <span className={`font-semibold text-sm ${conditionColors[condition] ?? ''}`}>{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent tickets */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-4">Recent Tickets</h2>
            <div className="space-y-3">
              {data.tickets.recent.map(t => (
                <Link key={t.id} to={`/tickets/${t.id}`} className="flex items-center justify-between hover:bg-gray-50 -mx-2 px-2 py-1 rounded-lg">
                  <span className="text-sm text-gray-700 truncate flex-1 mr-2">{t.title}</span>
                  <Badge label={t.status} variant="status" />
                </Link>
              ))}
            </div>
          </div>

          {/* Assets needing attention */}
          {data.assets.need_attention.length > 0 && (
            <div className="bg-white rounded-xl border border-red-200 p-5">
              <h2 className="font-semibold text-red-700 mb-4">⚠️ Assets Needing Attention</h2>
              <div className="space-y-2">
                {data.assets.need_attention.map(a => (
                  <Link key={a.id} to={`/assets/${a.id}`} className="flex items-center justify-between hover:bg-red-50 -mx-2 px-2 py-1 rounded-lg">
                    <span className="text-sm text-gray-700">{a.name} ({a.id})</span>
                    <Badge label={a.condition} variant="condition" />
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Maintenance summary */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-4">Maintenance Overview</h2>
            <div className="space-y-3">
              <div className="flex justify-between text-sm"><span className="text-gray-500">Total tasks</span><span className="font-medium">{data.maintenance.total}</span></div>
              <div className="flex justify-between text-sm"><span className="text-gray-500">Overdue</span><span className={`font-medium ${data.maintenance.overdue > 0 ? 'text-red-600' : ''}`}>{data.maintenance.overdue}</span></div>
              <div className="flex justify-between text-sm"><span className="text-gray-500">Due within 7 days</span><span className="font-medium text-yellow-600">{data.maintenance.due_soon}</span></div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`${color} rounded-xl border border-gray-200 p-5`}>
      <div className="text-3xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  )
}
