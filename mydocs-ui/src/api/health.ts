import axios from 'axios'

export async function checkHealth(): Promise<{ status: string; latencyMs: number }> {
  const start = Date.now()
  try {
    const { data } = await axios.get('/health', { timeout: 5000 })
    return { status: data.status || 'ok', latencyMs: Date.now() - start }
  } catch {
    return { status: 'error', latencyMs: Date.now() - start }
  }
}
