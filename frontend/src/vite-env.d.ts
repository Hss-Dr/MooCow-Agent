/// <reference types="vite/client" />
/// <reference types="vite-plugin-svgr/client" />

interface Window {
  $app: import('antd/es/app/context').useAppProps
  $showLoading: (options?: { title?: string }) => void
  $hideLoading: () => void
}
