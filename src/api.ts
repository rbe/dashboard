export type DashboardFile = {
  path: string
  markdown: string
}

export async function loadDashboard(): Promise<DashboardFile> {
  const response = await fetch('/api/dashboard')
  if (!response.ok) throw new Error('load-failed')
  return response.json() as Promise<DashboardFile>
}

export async function saveDashboard(markdown: string): Promise<void> {
  const response = await fetch('/api/dashboard', {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ markdown }),
  })
  if (!response.ok) throw new Error('save-failed')
}
