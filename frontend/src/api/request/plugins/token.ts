import type { AxiosInstance } from 'axios'
import { userState } from '@/store/user'
import type { IRequestPlugin } from './plugin'

/**
 * Token拦截器插件
 * 自动在请求头中添加Authorization token
 */
export const tokenPlugin: IRequestPlugin = {
  install(instance: AxiosInstance) {
    instance.interceptors.request.use(
      (config) => {
        const token = userState.token
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      },
    )

    // 响应拦截器：处理401未授权
    instance.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token过期或无效，清除本地token
          userState.token = null
          userState.username = null
          // 跳转到登录页
          window.location.href = '/login'
        }
        return Promise.reject(error)
      },
    )
  }
}
