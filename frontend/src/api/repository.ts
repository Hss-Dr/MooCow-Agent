import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(params?: {}, options?: AxiosRequestConfig) {
  return request.get<API.Repository[]>('/get_files/', {
    ...options,
    params,
  })
}

export function deleteFile(
  params?: Pick<API.Repository, 'file_name'>,
  options?: AxiosRequestConfig,
) {
  return request.delete<{ message: string }>('/delete_file/', {
    ...options,
    params,
  })
}
