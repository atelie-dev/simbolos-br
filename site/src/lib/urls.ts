/**
 * Contrato público de URL. O host dos ativos é separado do site de propósito:
 * SVG é documento executável, e origem separada é defesa em camadas.
 */
export const CDN = import.meta.env.PUBLIC_CDN_BASE ?? "https://simbolos.coletivo.dev.br";
export const SITE = import.meta.env.PUBLIC_SITE_BASE ?? "https://coletivo.dev.br/simbolos";
export const GITHUB = "https://github.com/atelie-dev/simbolos-br";

// BASE_URL vem sem barra final ("/simbolos"); concatenar direto gera
// "/simbolosapi/...". Normalizar aqui, uma vez, evita o erro em cada página.
const bruto = import.meta.env.BASE_URL;
export const BASE = bruto.endsWith("/") ? bruto : `${bruto}/`;

export type Tipo = "brasao" | "bandeira";
export type Formato = "svg" | "png" | "jpg";

export const embedUrl = (codigo: string, tipo: Tipo, ext: Formato): string =>
  `${CDN}/embed/v1/${tipo}/${codigo}.${ext}`;

export const metaUrl = (codigo: string, tipo: Tipo): string =>
  `${CDN}/meta/v1/${tipo}/${codigo}.json`;

export const paginaMunicipio = (codigo: string, slug: string): string =>
  `${SITE}/municipios/${codigo}-${slug}`;
