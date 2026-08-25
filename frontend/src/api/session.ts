import { AxiosRequestConfig } from 'axios'
import { request } from './request'

/**
 * 获取会话列表
 */
export function list(params?: {}, options?: AxiosRequestConfig) {
  return request.get<API.SessionListResponse>(`/session/sessions`, {
    ...options,
    params,
  })
}

/**
 * 获取会话消息历史
 */
export function detail(
  params: {
    session_id: string
  },
  options?: AxiosRequestConfig,
) {
  return request.get<API.Message[]>(
    `/session/messages/${params.session_id}`,
    {
      ...options,
    },
  )
}

/**
 * 创建新会话
 */
export function create(
  params?: { session_name?: string },
  options?: AxiosRequestConfig,
) {
  return request.post<API.SessionCreateResponse>(
    `/session/create`,
    {},
    {
      ...options,
      params,
    },
  )
}

/**
 * 删除会话
 */
export function remove(
  sessionId: string,
  options?: AxiosRequestConfig,
) {
  return request.delete<{ message: string }>(
    `/session/delete/${sessionId}`,
    options,
  )
}

/**
 * 重命名会话
 */
export function rename(
  sessionId: string,
  params: { session_name: string },
  options?: AxiosRequestConfig,
) {
  return request.put<{ message: string }>(
    `/session/rename/${sessionId}`,
    params,
    options,
  )
}

/**
 * AI聊天（SSE流）
 */
export function chat(
  params: {
    id: string
    message: string
    web_search?: boolean
    deep_think?: boolean
    attachments?: string[]
  },
  options?: AxiosRequestConfig,
) {
  const { id, ..._params } = params
  return request.post<ReadableStream>(
    '/ai_search/',
    {
      ..._params,
    },
    {
      headers: {
        Accept: 'text/event-stream',
      },
      responseType: 'stream',
      adapter: 'fetch',
      loading: false,
      params: {
        session_id: id,
      },
      ...options,
    },
  )
}

export function upload(params: { files: File }, options?: AxiosRequestConfig) {
  const form = new FormData()
  form.append('files', params.files)
  return request.post<API.Result<{ file_id: string; url: string }>>(
    `/upload_files/`,
    form,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      ...options,
    },
  )
}

