/**
 * Recebe relatos e contribuições do site e abre uma issue no repositório.
 *
 * O Worker **não aplica nada**: ele enfileira. A issue nasce com o rótulo
 * `aguardando-confirmacao`, e quem decide é uma pessoa com acesso ao repo.
 * O autor da issue é a App (`simbolos-br-relatos[bot]`), não uma pessoa — a
 * máquina se identifica como máquina.
 *
 * Forma do que chega: campos fechados, validados aqui. O item (código + tipo)
 * vem do índice do site; nunca é texto livre.
 */

const API = "https://api.github.com";
const FLUXOS = new Set(["relato", "contribuicao"]);
const TIPOS = new Set(["brasao", "bandeira"]);

// Lista fechada: cada motivo tem uma ação conhecida no acervo.
const MOTIVOS = new Set([
  "nao_e_o_simbolo",
  "tipo_trocado_brasao",
  "tipo_trocado_bandeira",
  "baixa_qualidade",
  "lixo_ou_marca",
  "corrompido",
  "desatualizado",
  "licenca",
  "outro",
]);

const CONTRIBUICOES = new Set(["simbolo", "ato_oficial", "vetor", "correcao"]);

const LIMITE_POR_HORA = 5;
const TEXTO_MAX = 800;
const CORPO_MAX = 8000;

const json = (corpo, status = 200) =>
  new Response(JSON.stringify(corpo), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });

const enc = new TextEncoder();

function texto(valor, max) {
  if (valor === undefined || valor === null) return "";
  const s = String(valor).trim();
  return s.length > max ? s.slice(0, max) : s;
}

function url_ok(valor) {
  const s = texto(valor, 500);
  if (!/^https?:\/\//i.test(s)) return null;
  try {
    new URL(s);
    return s;
  } catch {
    return null;
  }
}

function validar(d) {
  if (!d || typeof d !== "object") return { erro: "corpo invalido" };
  const fluxo = texto(d.fluxo, 20);
  if (!FLUXOS.has(fluxo)) return { erro: "fluxo invalido" };

  const codigo = texto(d.codigo, 7);
  if (!/^\d{7}$/.test(codigo)) return { erro: "codigo ibge invalido" };

  const tipo = texto(d.tipo, 10);
  if (!TIPOS.has(tipo)) return { erro: "tipo invalido" };

  const base = {
    fluxo,
    codigo,
    tipo,
    uf: texto(d.uf, 2).toUpperCase(),
    municipio: texto(d.municipio, 80),
    contato: texto(d.contato, 120),
  };

  if (fluxo === "relato") {
    const motivo = texto(d.motivo, 30);
    if (!MOTIVOS.has(motivo)) return { erro: "motivo invalido" };
    const detalhe = texto(d.detalhe, TEXTO_MAX);
    if (motivo === "outro" && detalhe.length < 10) {
      return { erro: "motivo outro exige descricao" };
    }
    return { dados: { ...base, motivo, detalhe } };
  }

  const contribuicao = texto(d.contribuicao, 20);
  if (!CONTRIBUICOES.has(contribuicao)) return { erro: "contribuicao invalida" };
  const url_fonte = url_ok(d.url_fonte);
  if (!url_fonte) return { erro: "fonte oficial e obrigatoria" };

  return {
    dados: {
      ...base,
      contribuicao,
      url_fonte,
      orgao: texto(d.orgao, 40),
      data: texto(d.data, 20),
      ato: texto(d.ato, 120),
      licenca: texto(d.licenca, 40),
      atribuicao: texto(d.atribuicao, 300),
      detalhe: texto(d.detalhe, TEXTO_MAX),
    },
  };
}

async function hashIp(ip) {
  const bruto = await crypto.subtle.digest("SHA-256", enc.encode(ip || "sem-ip"));
  return [...new Uint8Array(bruto)]
    .slice(0, 8)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function dentroDoLimite(env, ip) {
  const chave = `ip:${await hashIp(ip)}`;
  const atual = Number((await env.RELATOS.get(chave)) || 0);
  if (atual >= LIMITE_POR_HORA) return false;
  await env.RELATOS.put(chave, String(atual + 1), { expirationTtl: 3600 });
  return true;
}

async function verificarTurnstile(env, token, ip) {
  if (!token) return false;
  const corpo = new FormData();
  corpo.append("secret", env.TURNSTILE_SECRET);
  corpo.append("response", token);
  if (ip) corpo.append("remoteip", ip);
  const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    body: corpo,
  });
  if (!r.ok) return false;
  const d = await r.json();
  return d.success === true;
}

function b64url(bytes) {
  let s = "";
  const u = new Uint8Array(bytes);
  for (let i = 0; i < u.length; i += 1) s += String.fromCharCode(u[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function importarChave(pem) {
  const corpo = String(pem)
    .replace(/-----[^-]+-----/g, "")
    .replace(/\s+/g, "");
  const der = Uint8Array.from(atob(corpo), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey(
    "pkcs8",
    der,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );
}

async function jwtApp(env) {
  const agora = Math.floor(Date.now() / 1000);
  const cabecalho = b64url(enc.encode(JSON.stringify({ alg: "RS256", typ: "JWT" })));
  const corpo = b64url(
    enc.encode(
      JSON.stringify({ iat: agora - 60, exp: agora + 540, iss: env.GITHUB_APP_ID }),
    ),
  );
  const chave = await importarChave(env.GITHUB_PRIVATE_KEY);
  const assinatura = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    chave,
    enc.encode(`${cabecalho}.${corpo}`),
  );
  return `${cabecalho}.${corpo}.${b64url(assinatura)}`;
}

const cabecalhosGh = (jwt) => ({
  authorization: `Bearer ${jwt}`,
  accept: "application/vnd.github+json",
  "user-agent": "simbolos-relatos",
});

async function tokenInstalacao(env) {
  const cache = await env.RELATOS.get("gh:token");
  if (cache) return cache;

  const jwt = await jwtApp(env);
  let id = await env.RELATOS.get("gh:installation");
  if (!id) {
    const r = await fetch(`${API}/app/installations`, { headers: cabecalhosGh(jwt) });
    if (!r.ok) throw new Error(`instalacoes ${r.status}`);
    const lista = await r.json();
    if (!Array.isArray(lista) || lista.length === 0) throw new Error("app sem instalacao");
    id = String(lista[0].id);
    await env.RELATOS.put("gh:installation", id, { expirationTtl: 21600 });
  }

  const r = await fetch(`${API}/app/installations/${id}/access_tokens`, {
    method: "POST",
    headers: cabecalhosGh(jwt),
  });
  if (!r.ok) throw new Error(`token ${r.status}`);
  const { token } = await r.json();
  await env.RELATOS.put("gh:token", token, { expirationTtl: 3000 });
  return token;
}

function tituloIssue(d) {
  const ref = d.municipio ? `${d.municipio}/${d.uf}` : d.codigo;
  const assunto =
    d.fluxo === "relato" ? d.motivo : `contribuicao:${d.contribuicao}`;
  return `[${d.fluxo}] ${ref} — ${d.tipo} — ${assunto}`.slice(0, 200);
}

function corpoIssue(d) {
  const linhas = [
    `**Município:** ${d.municipio} (${d.uf}) — código ${d.codigo}`,
    `**Tipo:** ${d.tipo}`,
  ];
  if (d.fluxo === "relato") {
    linhas.push(`**Motivo:** ${d.motivo}`);
    if (d.detalhe) linhas.push(`**Detalhe:** ${d.detalhe}`);
  } else {
    linhas.push(`**O que traz:** ${d.contribuicao}`);
    linhas.push(`**Fonte oficial:** ${d.url_fonte}`);
    if (d.orgao) linhas.push(`**Órgão:** ${d.orgao}`);
    if (d.data) linhas.push(`**Data:** ${d.data}`);
    if (d.ato) linhas.push(`**Ato:** ${d.ato}`);
    if (d.licenca) linhas.push(`**Licença sugerida:** ${d.licenca}`);
    if (d.atribuicao) linhas.push(`**Atribuição:** ${d.atribuicao}`);
    if (d.detalhe) linhas.push(`**Detalhe:** ${d.detalhe}`);
  }
  if (d.contato) linhas.push(`**Contato:** ${d.contato}`);

  linhas.push(
    "",
    `**Arquivo no CDN:** https://simbolos.coletivo.dev.br/embed/v1/${d.tipo}/${d.codigo}.png`,
    "",
    "---",
    "",
    "<!-- relato:inicio -->",
    "```json",
    JSON.stringify(d, null, 1),
    "```",
    "<!-- relato:fim -->",
    "",
    "**Nada foi aplicado.** Confirmar exige uma pessoa com acesso ao repositório:",
    "aplicar com `simbolos rejeitar` / `simbolos importar`, e fechar esta issue",
    "citando o commit.",
  );
  return linhas.join("\n");
}

async function criarIssue(env, d) {
  const token = await tokenInstalacao(env);
  const r = await fetch(`${API}/repos/${env.GITHUB_REPO}/issues`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      accept: "application/vnd.github+json",
      "user-agent": "simbolos-relatos",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      title: tituloIssue(d),
      body: corpoIssue(d),
      labels: [d.fluxo, "aguardando-confirmacao"],
    }),
  });
  if (!r.ok) throw new Error(`issue ${r.status}: ${(await r.text()).slice(0, 160)}`);
  return r.json();
}

export default {
  async fetch(req, env) {
    if (req.method !== "POST") return json({ erro: "use POST" }, 405);

    const tamanho = Number(req.headers.get("content-length") || 0);
    if (tamanho > CORPO_MAX) return json({ erro: "corpo grande" }, 413);

    let dados;
    try {
      dados = await req.json();
    } catch {
      return json({ erro: "json invalido" }, 400);
    }

    const { dados: limpo, erro } = validar(dados);
    if (erro) return json({ erro }, 400);

    const ip = req.headers.get("CF-Connecting-IP");
    if (!(await verificarTurnstile(env, dados.turnstile, ip))) {
      return json({ erro: "verificacao anti-robo falhou" }, 403);
    }
    if (!(await dentroDoLimite(env, ip))) {
      return json({ erro: "muitos envios; tente mais tarde" }, 429);
    }

    // Mesmo item, mesmo motivo, em 24 h: não abre outra issue.
    const assinatura = `${limpo.codigo}:${limpo.tipo}:${limpo.motivo || limpo.contribuicao}`;
    if (await env.RELATOS.get(`dup:${assinatura}`)) {
      return json({ ok: true, duplicado: true });
    }

    try {
      const issue = await criarIssue(env, limpo);
      await env.RELATOS.put(`dup:${assinatura}`, "1", { expirationTtl: 86400 });
      return json({ ok: true, numero: issue.number, url: issue.html_url });
    } catch (e) {
      return json({ erro: "nao foi possivel registrar agora", detalhe: String(e).slice(0, 120) }, 502);
    }
  },
};
