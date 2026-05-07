import { useEffect, useState, FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { scanAsset, guestReport, type Asset } from '../lib/api'
import Badge from '../components/Badge'

type Step = 'loading' | 'asset' | 'form' | 'success' | 'error'

export default function Scan() {
  const { assetId }                   = useParams<{ assetId: string }>()
  const [step, setStep]               = useState<Step>('loading')
  const [asset, setAsset]             = useState<(Asset & { open_tickets: number }) | null>(null)
  const [errorMsg, setErrorMsg]       = useState('')
  const [name, setName]               = useState('')
  const [title, setTitle]             = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority]       = useState('Standard')
  const [submitting, setSubmitting]   = useState(false)

  useEffect(() => {
    if (!assetId) return
    scanAsset(assetId)
      .then(r => { setAsset(r.data); setStep('asset') })
      .catch(e => { setErrorMsg(e.message); setStep('error') })
  }, [assetId])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!assetId || !title.trim()) return
    setSubmitting(true)
    try {
      await guestReport({
        asset_id: assetId,
        title: title.trim(),
        description: description.trim() || undefined,
        reporter_name: name.trim() || undefined,
        priority,
      })
      setStep('success')
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-start justify-center p-4 pt-16">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <div className="text-2xl font-bold text-slate-900">AssetBase</div>
          <div className="text-sm text-gray-500">Facility Management</div>
        </div>

        {step === 'loading' && (
          <div className="bg-white rounded-2xl shadow p-8 text-center text-gray-400">Loading asset…</div>
        )}

        {step === 'error' && (
          <div className="bg-white rounded-2xl shadow p-8 text-center">
            <div className="text-red-500 text-4xl mb-3">❌</div>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Asset not found</h2>
            <p className="text-gray-500 text-sm">{errorMsg}</p>
          </div>
        )}

        {step === 'success' && (
          <div className="bg-white rounded-2xl shadow p-8 text-center">
            <div className="text-green-500 text-5xl mb-4">✓</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Thank you!</h2>
            <p className="text-gray-500 text-sm">Your report has been logged. Our team will look into it.</p>
          </div>
        )}

        {(step === 'asset' || step === 'form') && asset && (
          <div className="space-y-4">
            {/* Asset card */}
            <div className="bg-white rounded-2xl shadow p-5">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="font-bold text-gray-900 text-lg">{asset.name}</h2>
                  <div className="text-xs text-gray-400 font-mono">{asset.id}</div>
                </div>
                <Badge label={asset.condition} variant="condition" />
              </div>
              <div className="mt-3 text-sm text-gray-500 space-y-1">
                <div>Category: {asset.category}</div>
                {asset.location_name && <div>Location: {asset.location_name}</div>}
                <div>Open issues: {asset.open_tickets}</div>
              </div>
            </div>

            {/* Report form */}
            {step === 'asset' && (
              <button
                onClick={() => setStep('form')}
                className="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-3 rounded-xl transition"
              >
                Report an issue
              </button>
            )}

            {step === 'form' && (
              <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow p-6 space-y-4">
                <h3 className="font-semibold text-gray-900">Report an issue</h3>

                <div>
                  <label className="text-sm text-gray-600 mb-1 block">Your name (optional)</label>
                  <input value={name} onChange={e => setName(e.target.value)} placeholder="Guest User" className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" />
                </div>

                <div>
                  <label className="text-sm text-gray-600 mb-1 block">Issue title <span className="text-red-500">*</span></label>
                  <input required value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Chair wheel is broken" className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" />
                </div>

                <div>
                  <label className="text-sm text-gray-600 mb-1 block">Description</label>
                  <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} placeholder="Describe the issue…" className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" />
                </div>

                <div>
                  <label className="text-sm text-gray-600 mb-1 block">Priority</label>
                  <select value={priority} onChange={e => setPriority(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm">
                    {['Emergency','Urgent','Standard','Low'].map(p => <option key={p}>{p}</option>)}
                  </select>
                </div>

                <div className="flex gap-2">
                  <button type="submit" disabled={submitting} className="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-2.5 rounded-lg transition disabled:opacity-60">
                    {submitting ? 'Submitting…' : 'Submit report'}
                  </button>
                  <button type="button" onClick={() => setStep('asset')} className="bg-gray-100 text-gray-700 px-4 py-2.5 rounded-lg">
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
