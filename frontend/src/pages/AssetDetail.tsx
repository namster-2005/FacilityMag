import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAsset, getAssetQR, updateAsset, listLocations, type Asset, type Location } from '../lib/api'
import { useAuth } from '../lib/auth'
import Badge from '../components/Badge'
import QRModal from '../components/QRModal'
import Layout from '../components/Layout'

export default function AssetDetail() {
  const { id }                          = useParams<{ id: string }>()
  const { user }                        = useAuth()
  const [asset, setAsset]               = useState<Asset | null>(null)
  const [locations, setLocations]       = useState<Location[]>([])
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState('')
  const [qr, setQr]                     = useState<string | null>(null)
  const [showQR, setShowQR]             = useState(false)
  const [editing, setEditing]           = useState(false)
  const [editData, setEditData]         = useState<Partial<Asset>>({})
  const [saving, setSaving]             = useState(false)

  async function load() {
    if (!id) return
    setLoading(true)
    try {
      const [assetRes, locRes] = await Promise.all([getAsset(id), listLocations()])
      setAsset(assetRes.data)
      setLocations(locRes.data)
      setEditData({ condition: assetRes.data.condition, location_id: assetRes.data.location_id })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error loading asset')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  async function loadQR() {
    if (!id) return
    try {
      const res = await getAssetQR(id)
      setQr(res.data.qr_base64)
      setShowQR(true)
    } catch { /* ignore */ }
  }

  async function handleSave() {
    if (!id || !asset) return
    setSaving(true)
    try {
      await updateAsset(id, editData)
      setEditing(false)
      load()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Error saving')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Layout><div className="text-center py-20 text-gray-400">Loading…</div></Layout>
  if (error)   return <Layout><div className="text-red-600 p-4">{error}</div></Layout>
  if (!asset)  return null

  return (
    <Layout>
      {showQR && qr && <QRModal qrBase64={qr} assetId={asset.id} onClose={() => setShowQR(false)} />}

      <div className="space-y-6 max-w-3xl">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Link to="/assets" className="hover:text-emerald-700">Assets</Link>
          <span>/</span>
          <span>{asset.id}</span>
        </div>

        {/* Asset card */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{asset.name}</h1>
              <div className="flex items-center gap-3 mt-2">
                <span className="text-xs font-mono text-gray-400 bg-gray-100 px-2 py-1 rounded">{asset.id}</span>
                <span className="text-sm text-gray-500">{asset.category}</span>
                <Badge label={asset.condition} variant="condition" />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={loadQR} className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
                📱 QR Code
              </button>
              {(user?.role === 'staff' || user?.role === 'admin') && !editing && (
                <button onClick={() => setEditing(true)} className="border border-emerald-200 text-emerald-700 rounded-lg px-3 py-2 text-sm hover:bg-emerald-50">
                  Edit
                </button>
              )}
            </div>
          </div>

          {/* Details */}
          <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
            <Detail label="Location" value={asset.location_name ?? '—'} />
            <Detail label="Serial Number" value={asset.serial_number ?? '—'} />
            <Detail label="Purchase Date" value={asset.purchase_date ?? '—'} />
            <Detail label="Last Updated" value={asset.updated_at?.split('T')[0] ?? '—'} />
          </div>

          {/* Edit form */}
          {editing && (
            <div className="mt-5 pt-5 border-t border-gray-100 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Condition</label>
                  <select value={editData.condition} onChange={e => setEditData(p => ({ ...p, condition: e.target.value as Asset['condition'] }))} className="w-full border rounded-lg px-3 py-2 text-sm">
                    {['Excellent','Good','Ok','Bad','Damaged'].map(c => <option key={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Location</label>
                  <select value={editData.location_id ?? ''} onChange={e => setEditData(p => ({ ...p, location_id: e.target.value }))} className="w-full border rounded-lg px-3 py-2 text-sm">
                    <option value="">—</option>
                    {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={handleSave} disabled={saving} className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm">{saving ? 'Saving…' : 'Save'}</button>
                <button onClick={() => setEditing(false)} className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm">Cancel</button>
              </div>
            </div>
          )}
        </div>

        {/* Open tickets */}
        {(asset.open_tickets?.length ?? 0) > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-3">Open Tickets</h2>
            <div className="space-y-2">
              {asset.open_tickets!.map(t => (
                <Link key={t.id} to={`/tickets/${t.id}`} className="flex items-center justify-between py-2 hover:bg-gray-50 -mx-2 px-2 rounded-lg">
                  <span className="text-sm text-gray-700">{t.title}</span>
                  <Badge label={t.status} variant="status" />
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Movement log */}
        {(asset.logs?.length ?? 0) > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-3">Activity Log</h2>
            <div className="space-y-3">
              {asset.logs!.map(log => (
                <div key={log.id} className="flex items-start gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-gray-300 mt-1.5 shrink-0" />
                  <div>
                    <div className="text-gray-700">{log.action}</div>
                    <div className="text-xs text-gray-400">{log.created_at?.replace('T', ' ')}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-gray-400 uppercase font-medium mb-0.5">{label}</div>
      <div className="text-sm text-gray-700">{value}</div>
    </div>
  )
}
