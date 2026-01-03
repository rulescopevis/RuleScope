import js from "@eslint/js";
import globals from "globals";
import vue from "eslint-plugin-vue";
import typescript from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import prettier from "eslint-config-prettier";
import { FlatCompat } from "@eslint/eslintrc";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
  baseDirectory: __dirname,
});

// 获取当前环境
const isProduction = process.env.NODE_ENV === "production";

export default [
  // 基础 JavaScript 配置
  js.configs.recommended,

  // Vue 3 配置
  ...compat.extends("plugin:vue/vue3-essential"),

  // TypeScript 配置
  {
    files: ["**/*.ts", "**/*.tsx", "**/*.vue"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: "module",
      },
      globals: {
        ...globals.node,
      },
    },
    plugins: {
      "@typescript-eslint": typescript,
      vue: vue,
    },
    rules: {
      // Console 和 debugger 规则
      "no-console": isProduction ? "warn" : "off",
      "no-debugger": isProduction ? "warn" : "off",

      // TypeScript 规则
      "@typescript-eslint/no-unused-vars": ["warn"],
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
      "@typescript-eslint/no-var-requires": "off",

      // 通用规则
      "no-undef": "error",
      "no-redeclare": "error",

      // Vue 规则
      "vue/no-parsing-error": "off",
    },
  },

  // Prettier 配置
  prettier,
];
