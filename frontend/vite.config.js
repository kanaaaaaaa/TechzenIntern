import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"


export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5175,
    host: "0.0.0.0",
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://0.0.0.0:8000",
        changeOrigin: true,
      },
    },
  },
})

