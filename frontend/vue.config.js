const { defineConfig } = require("@vue/cli-service");
module.exports = defineConfig({
  transpileDependencies: true,
  chainWebpack: config => {
    // 强制移除打包时的 TypeScript 严格类型检查插件
    config.plugins.delete('fork-ts-checker');
  },
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
