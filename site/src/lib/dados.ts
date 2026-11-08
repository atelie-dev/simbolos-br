import { readFileSync } from "node:fs";
import { resolve } from "node:path";

/** Entrada do índice de busca (chaves curtas por causa do tamanho). */
export type Entrada = {
  c: string;
  n: string;
  u: string;
  e: string;
  s: string;
  b: number;
  f: number;
  t: number;
};

export type Rendicao = { bytes: number; sha256: string; lado?: number };

export type Item = {
  codigo_ibge: string;
  tipo: "brasao" | "bandeira";
  licenca: string | null;
  balde: string | null;
  autor: string | null;
  origem: string | null;
  formato_origem: string | null;
  sha256_origem: string | null;
  rendicoes: Record<string, Rendicao>;
  arte?: { l: number; a: number } | null;
};

const ler = <T>(rel: string): T =>
  JSON.parse(readFileSync(resolve(process.cwd(), rel), "utf8")) as T;

let cacheIndice: Entrada[] | null = null;
let cacheItens: Map<string, Item[]> | null = null;

export function indice(): Entrada[] {
  cacheIndice ??= ler<Entrada[]>("public/api/v1/municipios.json");
  return cacheIndice;
}

export function municipios(): Entrada[] {
  return indice().filter((e) => e.c.length === 7);
}

export function estados(): Entrada[] {
  return indice().filter((e) => e.c.length === 2);
}

/** Itens publicados agrupados por código IBGE (brasão e bandeira). */
export function itensPorCodigo(): Map<string, Item[]> {
  if (!cacheItens) {
    cacheItens = new Map();
    for (const item of ler<Item[]>("src/data/itens.json")) {
      const atual = cacheItens.get(item.codigo_ibge) ?? [];
      atual.push(item);
      cacheItens.set(item.codigo_ibge, atual);
    }
  }
  return cacheItens;
}

/**
 * T3 = vetorial. Nos rasters, o que importa é a arte, não o canvas de 512:
 * um brasão de 60 px dentro de um PNG 512 continua imprimindo mal.
 */
export const tier = (item: Item): { codigo: string; rotulo: string } => {
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
