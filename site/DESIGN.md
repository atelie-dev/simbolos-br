# DESIGN — Acervo de Símbolos

> Direção: **artesania editorial** — um acervo público que parece feito à mão por
> quem se importa, não gerado por quem preencheu um template.
>
> O ateliê assina o cuidado; o coletivo assina o aberto. A interface é a prova
> visível disso.

Este arquivo é lei para toda tela do site. Componente que contraria a direção é
defeito, não preferência.

## Tipografia

| Papel | Família | Pesos | Uso |
|---|---|---|---|
| Display | **Bricolage Grotesque** | 600, 800 | h1, h2, números grandes |
| Texto | **Source Sans 3** | 400, 600 | corpo, UI, tabelas |

- Escala: `12 / 14 / 16 / 20 / 28 / 44` px (rem: 0.75 / 0.875 / 1 / 1.25 / 1.75 / 2.75).
- Corpo: line-height **1.55**; títulos **1.15**; `text-wrap: balance` em h1/h2.
- Micro-rótulo: 11px, uppercase, `letter-spacing: .08em`, peso 600.
- Números de cobertura e contagens: **`font-variant-numeric: tabular-nums`**, sempre.
- Máximo de 65–72ch de largura em prosa.
- Autohospedadas em `public/fonts/` (sem requisição a terceiros). `font-display: swap`.

## Cor

Base neutra quente + **um** accent.

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--bg` | `#FDF6EE` | `#191512` | fundo |
| `--surface` | `#FFFFFF` | `#221C18` | cartões |
| `--ink` | `#241C17` | `#F5EDE6` | texto |
| `--muted` | `#7A6A5E` | `#A59486` | texto secundário |
| `--border` | `#EEDFD1` | `#3A302A` | divisórias, contorno |
| `--accent` | `#B4552D` | `#D97757` | terracota: ação principal, links, foco |
| `--accent-soft` | `#F6E3D8` | `#3A241C` | fundo de destaque |

Regras:
- O accent marca **uma** ação por região. Se aparecer em tudo, não é hierarquia.
- Proibido azul/roxo de framework e gradiente azul→roxo.
- Texto secundário nunca abaixo de 4.5:1.
- Selo de licença e selo de tier são **semânticos**, nunca do accent:

| Selo | Token | Cor |
|---|---|---|
| `livre` | `--ok` | verde `#2F6B47` |
| `compartilha` | `--warn` | âmbar `#8A5A12` |
| `oficial` | `--stop` | vinho `#8C2F39` |
| `não revisado` | neutro | `--muted` sobre `--border` |
| `verificado` | `--ok` | verde |

## Forma

- Raio: `4` (selo) / `10` (input, chip) / `14` (cartão) / `999` (pílula).
- **Uma** estratégia de sombra: suave em duas camadas, só em cartão elevado.
  `0 1px 2px rgba(36,28,23,.05), 0 10px 30px rgba(36,28,23,.06)`. Nunca em
  elemento inline, nunca em conjunto com borda forte.
- Grade de 4px; passos 4/8/12/16/24/32/48/64.
- Landing: uma ideia por seção, respiro. Densidade fica nas tabelas de cobertura.

## Movimento

- `180ms cubic-bezier(.2,.7,.3,1)`; só `transform` e `opacity`.
- Sem bounce, sem parallax, sem scrollytelling.
- `prefers-reduced-motion: reduce` desliga tudo (obrigatório).

## Estados obrigatórios

Todo elemento interativo entrega: `hover`, `focus-visible`, `disabled`,
`loading`. Foco visível é `outline: 2px solid var(--accent); outline-offset: 2px`.
Faltar foco é defeito.

Estados de página que precisam existir desenhados: sem resultado de busca,
município sem símbolo, item aguardando procedência, erro de rede do índice.

## Voz

- Frases curtas, voz ativa, sem superlativo. "Não temos ainda" é melhor que
  "em breve".
- Nunca prometer o que o dado não sustenta: cobertura sempre com numerador e
  denominador.
- Nunca sugerir vínculo com governo, IBGE ou prefeitura.

## O teste

Tire um screenshot: passaria como foto de produto numa página de marketing? Se
parecer "um dashboard feito por IA", a direção está errada — não o padding.
