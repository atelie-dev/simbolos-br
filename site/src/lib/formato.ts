/**
 * Formatação e classificação puras — sem `node:fs`.
 *
 * Ficam fora de `dados.ts` porque o card também é montado no navegador, e
 * `dados.ts` lê arquivos de build (`itens.json`). Um módulo só com o que é puro
 * evita arrastar `node:fs` para o bundle do cliente.
 */

export type ItemFormatavel = {
  rendicoes: Record<string, unknown>;
  arte?: { l: number; a: number } | null;
};

/**
 * T3 = vetorial. Nos rasters, o que importa é a arte, não o canvas de 512:
 * um brasão de 60 px dentro de um PNG 512 continua imprimindo mal.
 */
export const tier = (item: ItemFormatavel): { codigo: string; rotulo: string } => {
  if ("svg" in item.rendicoes) return { codigo: "T3", rotulo: "vetorial" };
  const lado = Math.max(item.arte?.l ?? 0, item.arte?.a ?? 0);
  if (lado >= 400) return { codigo: "T2", rotulo: `raster ${lado} px` };
  return { codigo: "T1", rotulo: lado ? `raster ${lado} px` : "raster pequeno" };
};

export const kb = (bytes: number): string => `${Math.round(bytes / 1024)} KB`;

export const host = (url: string | null): string => {
  if (!url) return "origem não registrada";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url.slice(0, 40);
  }
};
