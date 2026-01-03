const { defineConfig } = require("@vue/cli-service");
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    proxy: {
      "/api": {
        target: "http://localhost:8081", // 后端服务的地址
        changeOrigin: true, // 确保跨域请求
        pathRewrite: {
          "^/api": "", // 如果后端路径不需要 `/api`，可以将其移除
        },
      },
    },
  },
});
