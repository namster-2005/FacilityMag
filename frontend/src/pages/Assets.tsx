import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAssets, listLocations, createAsset, type Asset, type Location } from '../lib/api'
import { useAuth } from '../lib/auth'
import Badge from '../components/Badge'
import Layout from '../components/Layout'

const CATEGORIES = ['All', 'Furniture', 'Equipment', 'Appliance'] as const
const CONDITIONS = ['', 'Excellent', 'Good', 'Ok', 'Bad', 'Damaged']

export default function Assets() {
  const { user }                          = useAuth()
  const [assets, setAssets]               = useState<Asset[]>([])
  const [locations, setLocations]         = useState<Location[]>([])
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState('')
  const [q, setQ]                         = useState('')
  const [category, setCategory]           = useState('All')
  const [condition, setCondition]         = useState('')
  const [locationId, setLocationId]       = useState('')
  const [showForm, setShowForm]           = useState(false)
  const [newAsset, setNewAsset]           = useState<Partial<Asset>>({ category: 'Furniture', condition: 'Good' })
  const [saving, setSaving]               = useState(false)

  async function load() {
    setLoading(true)
    const params: Record<string, string> = {}
    if (q)          params.q          = q
    if (category !== 'All') params.category    = category
    if (condition)  params.condition  = condition
    if (locationId) params.location_id = locationId
    try {
      const [assetRes, locRes] = await Promise.all([
        listAssets(params),
        listLocations(),
      ])
      setAssets(assetRes.data)
      setLocations(locRes.data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error loading assets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [q, category, condition, locationId])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await createAsset(newAsset)
      setShowForm(false)
      setNewAsset({ category: 'Furniture', condition: 'Good' })
      load()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Error creating asset')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Layout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Assets</h1>
          {user?.role === 'admin' && (
            <button
              onClick={() => setShowForm(!showForm)}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              + New Asset
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Search name or ID…"
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-52 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <select value={condition} onChange={e => setCondition(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
            {CONDITIONS.map(c => <option key={c} value={c}>{c || 'All Conditions'}</option>)}
          </select>
          <select value={locationId} onChange={e => setLocationId(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">All Locations</option>
            {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        </div>

        {/* Category tabs */}
        <div className="flex gap-1 border-b border-gray-200">
          {CATEGORIES.map(c => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition ${category === c ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
              {c}
            </button>
          ))}
        </div>

        {/* New asset form */}
        {showForm && (
          <form onSubmit={handleCreate} className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-gray-900">New Asset</h3>
            <div className="grid grid-cols-2 gap-4">
              <input required placeholder="Name" value={newAsset.name ?? ''} onChange={e => setNewAsset(p => ({ ...p, name: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
              <select value={newAsset.category} onChange={e => setNewAsset(p => ({ ...p, category: e.target.value as Asset['category'] }))} className="border rounded-lg px-3 py-2 text-sm">
                {['Furniture','Equipment','Appliance'].map(c => <option key={c}>{c}</option>)}
              </select>
              <select value={newAsset.location_id ?? ''} onChange={e => setNewAsset(p => ({ ...p, location_id: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm">
                <option value="">No location</option>
                {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
              <select value={newAsset.condition} onChange={e => setNewAsset(p => ({ ...p, condition: e.target.value as Asset['condition'] }))} className="border rounded-lg px-3 py-2 text-sm">
                {['Excellent','Good','Ok','Bad','Damaged'].map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={saving} className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium">{saving ? 'Saving…' : 'Create'}</button>
              <button type="button" onClick={() => setShowForm(false)} className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm">Cancel</button>
            </div>
          </form>
        )}

        {/* Table */}
        {loading ? (
          <div className="text-center text-gray-400 py-12">Loading…</div>
        ) : error ? (
          <div className="text-red-600 py-4">{error}</div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['ID','Name','Category','Location','Condition'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {assets.map(a => (
                  <tr key={a.id} className="hover:bg-gray-50 cursor-pointer">
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">
                      <Link to={`/assets/${a.id}`} className="text-emerald-700 font-semibold hover:underline">{a.id}</Link>
                    </td>
                    <td className="px-4 py-3">
                      <Link to={`/assets/${a.id}`} className="text-gray-900 hover:text-emerald-700">{a.name}</Link>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{a.category}</td>
                    <td className="px-4 py-3 text-gray-500">{a.location_name ?? '—'}</td>
                    <td className="px-4 py-3"><Badge label={a.condition} variant="condition" /></td>
                  </tr>
                ))}
                {assets.length === 0 && (
                  <tr><td colSpan={5} className="text-center text-gray-400 py-8">No assets found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  )
}
