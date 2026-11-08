import { defineConfig } from "astro/config";

// O serviço vive em coletivo.dev.br/simbolos; `base` mantém link e asset no
// mesmo prefixo em dev e produção. Os ativos vêm de outro host (ver lib/urls.ts).
export default defineConfig({
  site: "https://coletivo.dev.br",
  base: "/simbolos",
  output: "static",
  // `file` gera municipios/3550308-sao-paulo.html em vez de pasta/index.html.
  // Com pasta, o Pages responde 308 para a versão com barra em toda URL.
  trailingSlash: "never",
  build: { format: "file", assets: "_astro" },
});
