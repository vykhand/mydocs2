import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  response => response,
  error => {
    const detail = error.response?.data?.detail || 'An unexpected error occurred'
    console.error('API error:', detail)
    toast.error(detail)
    return Promise.reject(error)
  }
)

export default api
