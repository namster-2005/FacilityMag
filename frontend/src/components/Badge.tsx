interface BadgeProps {
  label: string
  variant?: 'condition' | 'status' | 'priority'
}

const conditionColors: Record<string, string> = {
  Excellent: 'bg-emerald-100 text-emerald-800',
  Good:      'bg-green-100 text-green-800',
  Ok:        'bg-yellow-100 text-yellow-800',
  Bad:       'bg-orange-100 text-orange-800',
  Damaged:   'bg-red-100 text-red-800',
}

const statusColors: Record<string, string> = {
  Open:        'bg-blue-100 text-blue-800',
  'In Progress': 'bg-indigo-100 text-indigo-800',
  Resolved:    'bg-green-100 text-green-800',
  Closed:      'bg-gray-100 text-gray-600',
  Pending:     'bg-yellow-100 text-yellow-800',
  Done:        'bg-green-100 text-green-800',
  Overdue:     'bg-red-100 text-red-800',
}

const priorityColors: Record<string, string> = {
  Emergency: 'bg-red-100 text-red-800',
  Urgent:    'bg-orange-100 text-orange-800',
  Standard:  'bg-blue-100 text-blue-800',
  Low:       'bg-gray-100 text-gray-600',
}

export default function Badge({ label, variant = 'status' }: BadgeProps) {
  const map = variant === 'condition'
    ? conditionColors
    : variant === 'priority'
    ? priorityColors
    : statusColors

  const cls = map[label] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}
