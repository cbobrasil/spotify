# Meu histórico Spotify

Projeto pessoal pra explorar a biblioteca [Spotipy](https://spotipy.readthedocs.io/) (Python) e construir, aos poucos, um histórico real de escuta — já que o Spotify não expõe isso pronto pela API.

**Site publicado (atualiza sozinho a cada hora):**
👉 https://cbobrasil.github.io/spotify/

## Como funciona

Não tem servidor nem banco de dados por trás — é tudo estático:

1. Uma **GitHub Action** roda de hora em hora e busca as últimas reproduções via API do Spotify (`current_user_recently_played`), acrescentando ao `historico.csv` sem duplicar.
2. A Action também regenera o dashboard (`docs/index.html`) a partir desse CSV.
3. O **GitHub Pages** publica o conteúdo da pasta `docs/` automaticamente a cada push.
4. O filtro de datas no site (7 dias, 30 dias, este ano, período customizado etc.) roda inteiramente no navegador (JavaScript) — o Python só prepara os dados, não existe backend pra consultar sob demanda.

Além da captura contínua, o histórico foi complementado uma vez com o export oficial do Spotify ("Extended Streaming History", pedido em Configurações de Privacidade da conta), cobrindo desde dezembro/2021.

## Scripts

| Arquivo | O que faz |
|---|---|
| `01_autenticacao.py` | Primeiro teste de login OAuth com o Spotify |
| `02_top_musicas_artistas.py` | Top artistas/músicas por período (curto/médio/longo prazo) |
| `03_historico_acumulado.py` | Busca reproduções recentes e atualiza o `historico.csv` (usado pela Action) |
| `gerar_dashboard.py` | Gera o `docs/index.html` a partir do `historico.csv` |
| `gerar_refresh_token.py` | Gera o refresh token usado pela Action (roda uma vez, localmente) |
| `preencher_duracao.py` | One-off: preenche a duração das músicas já existentes no histórico |

## Rodando localmente

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # preencha com seu client_id/client_secret do Spotify Developer Dashboard
.venv/bin/python 03_historico_acumulado.py
.venv/bin/python gerar_dashboard.py
```

## Sobre os dados

O repositório é público, então `historico.csv` (música, artista, álbum, duração, data/hora) fica visível pra qualquer um. O export bruto do Spotify (que contém IP, país de conexão etc.) **não** é versionado — fica só localmente, ignorado pelo `.gitignore`.
