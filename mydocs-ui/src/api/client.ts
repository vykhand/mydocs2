import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useAuth } from '@/auth/useAuth'

const toast = useToast()

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach Bearer token to every request
api.interceptors.request.use(async (config) => {
  try {
    const { getAccessToken, isAuthenticated } = useAuth()
    if (isAuthenticated.value) {
      const token = await getAccessToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
  } catch {
    // If token acquisition fails silently, let the request proceed
    // The backend will return 401 and the response interceptor handles it
  }
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expired or invalid — redirect to login
      const { logout } = useAuth()
      logout()
      return Promise.reject(error)
    }
    const detail = error.response?.data?.detail || 'An unexpected error occurred'
    console.error('API error:', detail)
    toast.error(detail)
    return Promise.reject(error)
  }
)

export default api
