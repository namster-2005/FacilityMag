// All API types and fetch functions — no fetch() calls anywhere else

const BASE = import.meta.env.VITE_API_URL ?? ''

// ── Types ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  name: string
  email: string
  role: 'admin' | 'staff' | 'guest'
}

export interface Location {
  id: string
  name: string
  type: 'site' | 'storage'
  address?: string
  created_at: string
}

export interface Asset {
  id: string
  name: string
  category: 'Furniture' | 'Equipment' | 'Appliance'
  description?: string
  location_id?: string
  location_name?: string
  condition: 'Excellent' | 'Good' | 'Ok' | 'Bad' | 'Damaged'
  qr_code_path?: string
  photo_path?: string
  serial_number?: string
  purchase_date?: string
  created_at: string
  updated_at: string
  logs?: AssetLog[]
  open_tickets?: Ticket[]
}

export interface AssetLog {
  id: string
  asset_id: string
  user_id?: string
  action: string
  from_condition?: string
  to_condition?: string
  from_location?: string
  to_location?: string
  note?: string
  created_at: string
}

export interface Ticket {
  id: string
  asset_id: string
  asset_name?: string
  asset_category?: string
  title: string
  description?: string
  issue_type?: string
  status: 'Open' | 'In Progress' | 'Resolved' | 'Closed'
  priority: 'Emergency' | 'Urgent' | 'Standard' | 'Low'
  reporter_id?: string
  reporter_name?: string
  assigned_to?: string
  assignee_name?: string
  resolution_note?: string
  due_date?: string
  created_at: string
  updated_at: string
  resolved_at?: string
  comments?: TicketComment[]
}

export interface TicketComment {
  id: string
  ticket_id: string
  user_id?: string
  user_name?: string
  body: string
  created_at: string
}

export interface MaintenanceTask {
  id: string
  title: string
  description?: string
  asset_id?: string
  asset_name?: string
  location_id?: string
  location_name?: string
  assigned_to?: string
  assignee_name?: string
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'annual' | 'once'
  checklist_json?: string
  status: 'Pending' | 'In Progress' | 'Done' | 'Overdue'
  next_due?: string
  last_done_at?: string
  created_at: string
  updated_at: string
}

export interface DashboardData {
  assets: {
    total: number
    by_condition: Record<string, number>
    by_category: Record<string, number>
    need_attention: Array<{ id: string; name: string; condition: string }>
  }
  tickets: {
    total: number
    open: number
    in_progress: number
    overdue: number
    by_priority: Record<string, number>
    recent: Array<{ id: string; title: string; status: string; priority: string; created_at: string }>
  }
  maintenance: {
    total: number
    overdue: number
    due_soon: number
  }
}

export interface ListResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getToken(): string | null {
  return localStorage.getItem('token')
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  auth = true,
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (auth) {
    const t = getToken()
    if (t) headers['Authorization'] = `Bearer ${t}`
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.error ?? `HTTP ${res.status}`)
  return json as T
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string) {
  return request<{ data: { token: string; user: User } }>('POST', '/api/auth/login', { email, password }, false)
}

export async function getMe() {
  return request<{ data: User }>('GET', '/api/auth/me')
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export async function getDashboard() {
  return request<{ data: DashboardData }>('GET', '/api/dashboard')
}

// ── Assets ────────────────────────────────────────────────────────────────────

export async function listAssets(params?: Record<string, string>) {
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  return request<ListResponse<Asset>>('GET', `/api/assets${qs}`)
}

export async function getAsset(id: string) {
  return request<{ data: Asset }>('GET', `/api/assets/${id}`)
}

export async function createAsset(data: Partial<Asset>) {
  return request<{ data: Asset }>('POST', '/api/assets', data)
}

export async function updateAsset(id: string, data: Partial<Asset>) {
  return request<{ data: Asset }>('PUT', `/api/assets/${id}`, data)
}

export async function deleteAsset(id: string) {
  return request<{ data: { deleted: boolean } }>('DELETE', `/api/assets/${id}`)
}

export async function getAssetQR(id: string) {
  return request<{ data: { qr_base64: string } }>('GET', `/api/assets/${id}/qr`)
}

export async function getAssetLogs(id: string) {
  return request<{ data: AssetLog[] }>('GET', `/api/assets/${id}/logs`)
}

export async function scanAsset(id: string) {
  return request<{ data: Asset & { open_tickets: number } }>('GET', `/api/assets/scan/${id}`, undefined, false)
}

// ── Tickets ───────────────────────────────────────────────────────────────────

export async function listTickets(params?: Record<string, string>) {
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  return request<ListResponse<Ticket>>('GET', `/api/tickets${qs}`)
}

export async function getTicket(id: string) {
  return request<{ data: Ticket }>('GET', `/api/tickets/${id}`)
}

export async function createTicket(data: Partial<Ticket>) {
  return request<{ data: Ticket }>('POST', '/api/tickets', data)
}

export async function updateTicket(id: string, data: Partial<Ticket>) {
  return request<{ data: Ticket }>('PUT', `/api/tickets/${id}`, data)
}

export async function deleteTicket(id: string) {
  return request<{ data: { deleted: boolean } }>('DELETE', `/api/tickets/${id}`)
}

export async function addComment(ticketId: string, body: string) {
  return request<{ data: TicketComment }>('POST', `/api/tickets/${ticketId}/comment`, { body })
}

export async function guestReport(data: {
  asset_id: string
  title: string
  description?: string
  reporter_name?: string
  priority?: string
}) {
  return request<{ data: Ticket }>('POST', '/api/tickets/guest', data, false)
}

// ── Maintenance ───────────────────────────────────────────────────────────────

export async function listMaintenance(params?: Record<string, string>) {
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  return request<ListResponse<MaintenanceTask>>('GET', `/api/maintenance${qs}`)
}

export async function getMaintenance(id: string) {
  return request<{ data: MaintenanceTask }>('GET', `/api/maintenance/${id}`)
}

export async function createMaintenance(data: Partial<MaintenanceTask>) {
  return request<{ data: MaintenanceTask }>('POST', '/api/maintenance', data)
}

export async function updateMaintenance(id: string, data: Partial<MaintenanceTask>) {
  return request<{ data: MaintenanceTask }>('PUT', `/api/maintenance/${id}`, data)
}

export async function completeTask(id: string) {
  return request<{ data: MaintenanceTask }>('POST', `/api/maintenance/${id}/complete`)
}

// ── Locations ─────────────────────────────────────────────────────────────────

export async function listLocations() {
  return request<{ data: Location[] }>('GET', '/api/locations')
}

export async function createLocation(data: Partial<Location>) {
  return request<{ data: Location }>('POST', '/api/locations', data)
}
