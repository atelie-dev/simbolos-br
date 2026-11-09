/**
 * Markup do card de símbolo, em função pura.
 *
 * É a **única** fonte do card: a página do município renderiza no build e o
 * formulário de relato renderiza no navegador, e os dois precisam ser o mesmo
 * card — não uma miniatura parecida. Se divergirem, o formulário deixa de
 * mostrar o que a pessoa viu.
 *
 * `opcoes.acoes: false` tira copiar/baixar/reportar, que não fazem sentido
 * dentro do formulário de relato.
 */

import { embedUrl } from "./urls";
import { host, kb, tier } from "./formato";

export type CardEntrada = { c: string; n: string };

export type CardItem = {
  licenca: string | null;
  balde: string | null;
  autor: string | null;
  origem: string | null;
  rendicoes: Record<string, { bytes: number }>;
  arte?: { l: number; a: number } | null;
  verificacao?: { estado?: string; em?: string } | null;
};

/**
 * A linha "Revisão" diz o que a última conferência concluiu, não um selo fixo.
 * `em` é ISO; o card mostra dia/mês — o ano está na versão do acervo.
 */
function revisao(verificacao?: { estado?: string; em?: string } | null): {
  texto: string;
  tom: string;
} {
  const estado = verificacao?.estado ?? "";
  const em = verificacao?.em ?? "";
  const quando = em.length >= 10 ? ` ${em.slice(8, 10)}/${em.slice(5, 7)}` : "";
  switch (estado) {
    case "igual":
    case "renomeado":
      return { texto: `conferido${quando}`, tom: "livre" };
    case "link_vivo":
      return { texto: `link vivo${quando}`, tom: "livre" };
    case "divergente":
      return { texto: "origem mudou", tom: "compartilha" };
    case "sumiu":
      return { texto: "origem sumiu", tom: "oficial" };
    case "link_morto":
      return { texto: "link morto", tom: "oficial" };
    default:
      return { texto: "não revisado", tom: "revisao" };
  }
}

export type CardOpcoes = {
  base: string;
  acoes?: boolean;
  /** `false` esconde o selo de tier — usado quando não há medida da arte. */
  selo?: boolean;
};

const esc = (valor: unknown): string =>
  String(valor ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

const BALDE: Record<string, string> = {
  livre: "livre",
  compartilha: "compartilha",
  oficial: "oficial",
  pendente: "pendente",
};

/**
 * Selo oficial da CC, com link para a escritura da licença.
 *
 * Os arquivos ficam em `public/cc/` (88×31, do licensebuttons.net): carregar de
 * terceiro a cada visita entregaria o IP do visitante a quem serve o selo. Nas
 * licenças sem selo (NOASSERTION), o texto do balde já diz o que se sabe.
 */
const LICENCAS: Record<string, { arquivo: string; nome: string; deed: string }> = {
  "CC0-1.0": {
    arquivo: "cc/cc-zero.png",
    nome: "CC0 1.0",
    deed: "https://creativecommons.org/publicdomain/zero/1.0/",
  },
  "CC-BY-SA-4.0": {
    arquivo: "cc/by-sa.png",
    nome: "CC BY-SA 4.0",
    deed: "https://creativecommons.org/licenses/by-sa/4.0/",
  },
};

export function cardHtml(
  entrada: CardEntrada,
  tipo: "brasao" | "bandeira",
  item: CardItem | undefined,
  opcoes: CardOpcoes,
): string {
  const rotulo = tipo === "brasao" ? "Brasão" : "Bandeira";
  const artigo = tipo === "brasao" ? "o" : "a";
  const linkContribuir = `${esc(opcoes.base)}contribuir?cod=${esc(entrada.c)}&amp;tipo=${tipo}`;

  if (!item) {
    // O vazio tem a mesma anatomia do card cheio (prévia + info): assim os dois
    // lados ficam alinhados, em vez de um bloco de texto solto ao lado de um
    // card. A CTA só aparece fora do formulário de relato — lá ela apontaria
    // para a própria página em que a pessoa está.
    const cta =
      opcoes.acoes === false
        ? ""
        : `<div class="acoes"><a class="btn" href="${linkContribuir}">Indicar a fonte oficial</a></div>`;
    return `<article class="card vazio">
  <div class="xadrez" aria-hidden="true">
    <svg viewBox="0 0 24 28" width="104" height="120" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 1.6 22 5.2v8.6c0 6.6-4.2 10.9-10 12.6C6.2 24.7 2 20.4 2 13.8V5.2L12 1.6Z" />
      <path d="M12 9.6v6.8" />
      <path d="M8.6 13h6.8" />
    </svg>
  </div>
  <div class="info">
    <h2>${rotulo}</h2>
    <p class="muted">Ainda não temos ${artigo} ${rotulo.toLowerCase()} de ${esc(entrada.n)}.</p>
    <p class="nota">Ausente não quer dizer inexistente: muitas prefeituras publicam ${artigo} ${rotulo.toLowerCase()} só em PDF, num decreto ou no site antigo.</p>
    ${cta}
  </div>
</article>`;
  }

  const formatos = (["svg", "png", "jpg"] as const).filter((f) => item.rendicoes[f]);
  const principal = item.rendicoes.svg ? "svg" : "png";
  const alvo = embedUrl(entrada.c, tipo, principal);
  const alt = `${rotulo} de ${entrada.n}`;
  const snippet = `<img src="${alvo}" alt="${alt}" width="192" height="192">`;

  let selo = "";
  if (opcoes.selo !== false) {
    const t = tier(item);
    selo = `<span class="selo selo--tier">${t.codigo} · ${esc(t.rotulo)}</span>`;
  }

  const acoes =
    opcoes.acoes === false
      ? ""
      : `<div class="acoes">
          <button type="button" class="btn btn--ghost" data-papel="url" data-copiar="${esc(alvo)}">Copiar URL</button>
          <button type="button" class="btn btn--ghost" data-papel="snippet" data-copiar="${esc(snippet)}">Copiar &lt;img&gt;</button>
          <a class="btn" data-baixar href="${esc(alvo)}" target="_blank" rel="noopener">Baixar ${principal.toUpperCase()}</a>
          <a class="btn btn--ghost" href="${linkContribuir}">Reportar problema</a>
        </div>`;

  // Toda linha aparece sempre: quando o valor falta, o card diz que falta, em
  // vez de encolher. Sem isso, dois cards lado a lado têm áreas brancas com
  // alturas diferentes.
  const autor = item.autor
    ? `<dd>${esc(item.autor)}</dd>`
    : `<dd class="ausente">não registrado</dd>`;
  const lic = LICENCAS[item.licenca ?? ""];
  const rev = revisao(item.verificacao);
  const licencaTexto = item.licenca
    ? `<code>${esc(item.licenca)}</code>`
    : `<span class="ausente">não declarada</span>`;
  const seloLic = lic
    ? `<a class="lic-badge" href="${esc(lic.deed)}" rel="license noopener"><img src="${esc(opcoes.base)}${lic.arquivo}" alt="${esc(lic.nome)}" width="88" height="31" loading="lazy" /></a>`
    : "";
  const origem = item.origem
    ? `<a href="${esc(item.origem)}" rel="noopener">${esc(host(item.origem))}</a>`
    : "não registrada";

  return `<article class="card simbolo">
  <div class="xadrez">
    <img data-previa src="${esc(embedUrl(entrada.c, tipo, principal))}" alt="${esc(alt)}" width="320" height="320" decoding="async" />
  </div>
  <div class="info">
    <div class="info-topo">
      <h2>${rotulo}</h2>
      ${selo}
    </div>
    <dl class="detalhes">
      <div><dt>Licença</dt><dd class="licenca"><span class="selo selo--${esc(item.balde ?? "")}">${esc(BALDE[item.balde ?? ""] ?? "?")}</span> ${licencaTexto} ${seloLic}</dd></div>
      <div><dt>Autor</dt>${autor}</div>
      <div><dt>Origem</dt><dd>${origem}</dd></div>
      <div><dt>Formatos</dt><dd class="num formatos">${formatos
        .map(
          (f) =>
            `<button type="button" class="fmt" data-fmt data-ext="${f}" data-url="${esc(
              embedUrl(entrada.c, tipo, f),
            )}" aria-pressed="${f === principal}">${f.toUpperCase()} <span>${kb(
              item.rendicoes[f].bytes,
            )}</span></button>`,
        )
        .join(" ")}</dd></div>
      <div><dt>Revisão</dt><dd><span class="selo selo--${rev.tom}">${esc(rev.texto)}</span></dd></div>
    </dl>
    ${acoes}
  </div>
</article>`;
}
