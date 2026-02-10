import axios from 'axios'
import { useToast } from 'vue-toastification'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  response => response,
  error => {
    const detail = error.response?.data?.detail || 'An unexpected error occurred'
    try {
      const toast = useToast()
      toast.error(detail)
    } catch {
      // Toast may not be available during SSR or early init
      console.error(detail)
    }
    return Promise.reject(error)
  }
)

export default api
