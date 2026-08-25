import { AxiosRequestConfig } from 'axios'
import { request } from './request'

/**
 * 用户注册
 */
export function register(
  params: {
    username: string
    password: string
  },
  options?: AxiosRequestConfig,
) {
  return request.post<{ message: string }>(
    '/auth/register',
    params,
    options,
  )
}

/**
 * 用户登录
 */
export function login(
  params: {
    username: string
    password: string
  },
  options?: AxiosRequestConfig,
) {
  return request.post<{
    access_token: string
    token_type: string
  }>('/auth/login', params, options)
}

/**
 * 用户登出
 */
export function logout(options?: AxiosRequestConfig) {
  return request.post<{ message: string }>(
    '/auth/logout',
    {},
    options,
  )
}

/**
 * 获取当前用户信息
 */
export function getCurrentUser(options?: AxiosRequestConfig) {
  return request.get<{
    user_id: number
    username: string
  }>('/auth/me', options)
}
