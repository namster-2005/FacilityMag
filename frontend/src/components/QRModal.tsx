interface QRModalProps {
  qrBase64: string
  assetId: string
  onClose: () => void
}

export default function QRModal({ qrBase64, assetId, onClose }: QRModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl p-6 max-w-xs w-full text-center"
        onClick={e => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-1">QR Code</h3>
        <p className="text-sm text-gray-500 mb-4">Asset {assetId}</p>
        <img src={qrBase64} alt={`QR for ${assetId}`} className="mx-auto w-48 h-48" />
        <p className="text-xs text-gray-400 mt-3">Scan to report an issue</p>
        <button
          onClick={onClose}
          className="mt-4 w-full bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg py-2 text-sm font-medium transition"
        >
          Close
        </button>
      </div>
    </div>
  )
}
