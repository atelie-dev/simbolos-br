{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  env = {
    PROJECT_NAME = "simbolos-br";

    # Contrato público. Trocar de domínio é mudar estas variáveis, não o código.
    SITE_BASE = "https://coletivo.dev.br";
    CDN_BASE = "https://simbolos.coletivo.dev.br";
    SERVICO_PATH = "/simbolos";

    # Python: use the devenv interpreter, never download one; nix store is
    # read-only so uv must copy instead of hardlink; keep the tree clean.
    UV_PYTHON_PREFERENCE = "only-system";
    UV_LINK_MODE = "copy";
    PYTHONDONTWRITEBYTECODE = "1";
    PYTHONUNBUFFERED = "1";

    # Deterministic, accent-aware collation for pt-BR names.
    LC_ALL = "C.UTF-8";
  };

  packages = with pkgs; [
    # repo / github
    git
    git-lfs
    gh
    # shell + data wrangling
    curl
    file
    jq
    yq-go
    ripgrep
    fd
    zip
    unzip
    zstd
    shellcheck
    # image pipeline: source SVG -> PNG -> JPG/WebP renditions
    resvg
    librsvg
    imagemagick
    libwebp
    oxipng
    jpegoptim
    svgo
    libxml2
    dejavu_fonts
    liberation_ttf
    # harvest: PDF vector extraction + queue state
    pkgs."poppler-utils"
    mupdf
    sqlite
    # python quality
    ruff
    # cloudflare (R2 + cache purge + pages)
    wrangler
  ];

  languages.python = {
    enable = true;
    package = pkgs.python315;
    uv.enable = true;
  };

  languages.javascript = {
    enable = true;
    package = pkgs.nodejs_26;
    pnpm.enable = true;
  };

  # nil + nixfmt
  languages.nix.enable = true;

  scripts = {
    setup.exec = ''
      set -euo pipefail
      if [ -f pyproject.toml ]; then uv sync -U; fi
      if [ -f package.json ]; then pnpm install; fi
      echo "dependências instaladas"
    '';

    dev.exec = ''
      set -euo pipefail
      if [ -f package.json ]; then
        exec pnpm dev "$@"
      else
        echo "sem package.json ainda — nada para servir" >&2
        exit 1
      fi
    '';

    build.exec = ''
      set -euo pipefail
      if [ -f package.json ]; then
        exec pnpm build "$@"
      else
        echo "sem package.json ainda — nada para compilar" >&2
        exit 1
      fi
    '';

    # Regenerate the IBGE catalog (states + municipalities).
    ibge.exec = ''
      set -euo pipefail
      if [ -f scripts/ibge_municipios.py ]; then
        exec uv run python scripts/ibge_municipios.py "$@"
      else
        echo "scripts/ibge_municipios.py ainda não existe" >&2
        exit 1
      fi
    '';

    # Validate + render + publish the asset pipeline.
    pipeline.exec = ''
      set -euo pipefail
      if [ -f pyproject.toml ]; then
        exec uv run python -m simbolos "$@"
      else
        echo "pipeline ainda não existe" >&2
        exit 1
      fi
    '';
  };

  enterShell = ''
    echo ""
    echo "  simbolos-br · brasões e bandeiras do Brasil"
    echo "  python $(python --version 2>&1 | cut -d' ' -f2)   node $(node --version)   resvg $(resvg --version 2>&1 | head -1)"
    echo "  setup · dev · build · ibge · pipeline"
    echo ""
  '';

  enterTest = ''
    set -euo pipefail
    python --version
    node --version
    pnpm --version
    resvg --version
    magick --version | head -1
    oxipng --version
    cwebp -version
    svgo --version
    wrangler --version
    jq --version
    echo "devenv ok"
  '';

  # See full reference at https://devenv.sh/reference/options/
}
