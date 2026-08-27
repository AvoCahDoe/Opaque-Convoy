const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json()
}

export function fetchScenarios() {
  return request('/scenarios')
}

export function fetchGraph(scenarioId) {
  return request(`/scenarios/${scenarioId}/graph`)
}

export function planRoutes(body) {
  return request('/plan', { method: 'POST', body: JSON.stringify(body) })
}

export function fetchTradeoff(scenarioId) {
  return request(`/scenarios/${scenarioId}/tradeoff`)
}
