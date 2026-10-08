import axios from 'axios'

const api = axios.create({
  baseURL: '/',
  withCredentials: true,
  timeout: 60000,
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : detail?.[0]?.msg || err.message || '请求失败'
    err.userMessage = msg
    return Promise.reject(err)
  },
)

export default api
