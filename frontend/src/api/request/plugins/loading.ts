import { AxiosRequestConfig, AxiosResponse } from 'axios'
import { IRequestPlugin } from './plugin'

function show() {
  window.$showLoading({
    title: '加载中...',
  })
}
function hide() {
  window.$hideLoading()
}

export const loadingPlugin: IRequestPlugin = {
  preinstall(instance) {
    instance.interceptors.response.use(
      (response) => {
        const config = response.config as AxiosRequestConfig
        if (config?.loading) hide()

        return response
      },
      (error) => {
        const response = error.response as AxiosResponse<any> | undefined

        const config = response?.config ?? error?.config
        const loading = config?.loading
        if (loading) hide()

        return Promise.reject(error)
      },
    )
  },

  postinstall(instance) {
    instance.interceptors.request.use((config) => {
      if (config.loading) show()

      return config
    })
  },
}
