// vite.config.ts
import react from "file:///sessions/jolly-focused-fermat/mnt/%ED%95%98%EB%84%A4%EC%8A%A4%20%EC%97%94%EC%A7%80%EB%8B%88%EC%96%B4%EB%A7%81/hachilles/src/hachilles/web/node_modules/@vitejs/plugin-react/dist/index.js";
import { defineConfig } from "file:///sessions/jolly-focused-fermat/mnt/%ED%95%98%EB%84%A4%EC%8A%A4%20%EC%97%94%EC%A7%80%EB%8B%88%EC%96%B4%EB%A7%81/hachilles/src/hachilles/web/node_modules/vite/dist/node/index.js";
var vite_config_default = defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: "dist"
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvc2Vzc2lvbnMvam9sbHktZm9jdXNlZC1mZXJtYXQvbW50L1x1RDU1OFx1QjEyNFx1QzJBNCBcdUM1RDRcdUM5QzBcdUIyQzhcdUM1QjRcdUI5QzEvaGFjaGlsbGVzL3NyYy9oYWNoaWxsZXMvd2ViXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCIvc2Vzc2lvbnMvam9sbHktZm9jdXNlZC1mZXJtYXQvbW50L1x1RDU1OFx1QjEyNFx1QzJBNCBcdUM1RDRcdUM5QzBcdUIyQzhcdUM1QjRcdUI5QzEvaGFjaGlsbGVzL3NyYy9oYWNoaWxsZXMvd2ViL3ZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9zZXNzaW9ucy9qb2xseS1mb2N1c2VkLWZlcm1hdC9tbnQvJUVEJTk1JTk4JUVCJTg0JUE0JUVDJThBJUE0JTIwJUVDJTk3JTk0JUVDJUE3JTgwJUVCJThCJTg4JUVDJTk2JUI0JUVCJUE3JTgxL2hhY2hpbGxlcy9zcmMvaGFjaGlsbGVzL3dlYi92aXRlLmNvbmZpZy50c1wiO2ltcG9ydCByZWFjdCBmcm9tIFwiQHZpdGVqcy9wbHVnaW4tcmVhY3RcIlxuaW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSBcInZpdGVcIlxuXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBwbHVnaW5zOiBbcmVhY3QoKV0sXG4gIHNlcnZlcjoge1xuICAgIHByb3h5OiB7XG4gICAgICBcIi9hcGlcIjoge1xuICAgICAgICB0YXJnZXQ6IFwiaHR0cDovL2xvY2FsaG9zdDo4MDAwXCIsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcbiAgICAgIH0sXG4gICAgfSxcbiAgfSxcbiAgYnVpbGQ6IHtcbiAgICBvdXREaXI6IFwiZGlzdFwiLFxuICB9LFxufSlcbiJdLAogICJtYXBwaW5ncyI6ICI7QUFBNGMsT0FBTyxXQUFXO0FBQzlkLFNBQVMsb0JBQW9CO0FBRTdCLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxNQUFNLENBQUM7QUFBQSxFQUNqQixRQUFRO0FBQUEsSUFDTixPQUFPO0FBQUEsTUFDTCxRQUFRO0FBQUEsUUFDTixRQUFRO0FBQUEsUUFDUixjQUFjO0FBQUEsTUFDaEI7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsT0FBTztBQUFBLElBQ0wsUUFBUTtBQUFBLEVBQ1Y7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
