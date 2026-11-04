import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { defineConfig } from '@rsbuild/core';
import { pluginReact } from '@rsbuild/plugin-react';
import { pluginTailwindcss } from '@rsbuild/plugin-tailwindcss';

const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [pluginReact(), pluginTailwindcss()],
  source: {
    alias: {
      '@': path.resolve(rootDir, 'src'),
    },
  },
  html: {
    title: 'DocuMind',
    favicon: path.resolve(rootDir, 'public/brand/documind-mark.png'),
    meta: {
      description: 'AI-powered document research assistant',
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    historyApiFallback: true,
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
