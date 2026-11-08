import { defineConfig } from "astro/config";

// O serviço vive em coletivo.dev.br/simbolos; `base` mantém link e asset no
// mesmo prefixo em dev e produção. Os ativos vêm de outro host (ver lib/urls.ts).
export default defineConfig({
  site: "https://coletivo.dev.br",
  base: "/simbolos",
  output: "static",
  trailingSlash: "ignore",
  build: { assets: "_astro" },
});
