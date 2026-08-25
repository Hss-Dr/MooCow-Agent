import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import svgr from 'vite-plugin-svgr'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd()) as {
    VITE_API_BASE: string
    VITE_API_PROXY: string
  }

  console.log(env.VITE_API_BASE, '-->', env.VITE_API_PROXY)

  return {
    server: {
      port: 5181,
      host: 'localhost',

      proxy: {
        [env.VITE_API_BASE]: {
          target: env.VITE_API_PROXY,
          changeOrigin: true,
          secure: false,
          // 连本地时，需要重写路径，去掉 VITE_API_BASE 前缀
          rewrite: (path) =>
            path.replace(new RegExp(`^${env.VITE_API_BASE}`), ''),
        },
      },
    },
    resolve: {
      alias: [
        {
          find: /^@\//,
          replacement: '/src/',
        },
      ],
    },

    plugins: [
      react(),
      svgr(),
    ],
  }
})
