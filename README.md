# Histórico Spotify

Projeto pessoal pra explorar a biblioteca [Spotipy](https://spotipy.readthedocs.io/) (Python) e construir, aos poucos, um histórico real de escuta

**Site publicado (atualiza sozinho a cada hora):**
👉 https://cbobrasil.github.io/spotify/

## Como funciona

Banco de dados via csv, estático. Duas fases:

### Fase 1 — setup (feito uma vez, manualmente, local)

Scripts em [`setup/`](setup/) — veja a seção [Scripts](#scripts) abaixo pra descrição de cada um.

1. Criar um app no [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) → gera `client_id`/`client_secret`.
2. Rodar `setup/gerar_refresh_token.py` uma vez: abre o navegador, você autoriza o app, e ele imprime um **refresh token** (uma espécie de "senha de longa duração" — com ele dá pra pedir novos access tokens sem repetir o login).
3. Cadastrar `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET` e `SPOTIFY_REFRESH_TOKEN` como **Secrets** do repositório no GitHub (Settings → Secrets and variables → Actions) — é assim que a Action consegue autenticar sozinha, sem navegador.
4. `setup/preencher_duracao.py` buscou a duração de todas as músicas já no histórico.
5. `setup/integrar_historico_completo.py` importou o export oficial do Spotify ("Extended Streaming History"), cobrindo desde dezembro/2021.

Esses passos já foram feitos — os scripts ficam guardados em `setup/` só pra caso precisem ser refeitos no futuro (ex: token revogado, ou pedir um novo export completo do Spotify).

### Fase 2 — automação (roda sozinha, a cada hora, via GitHub Actions)

Definida em [`.github/workflows/historico.yml`](.github/workflows/historico.yml):

1. **Gatilho**: `cron: "0 * * * *"` (todo minuto 0 de cada hora) ou disparo manual pela aba Actions (`workflow_dispatch`).
2. **Checkout** do repositório + setup do Python 3.12 + `pip install -r requirements.txt`.
3. **`python historico_acumulado.py`**: autentica usando o `SPOTIFY_REFRESH_TOKEN` (sem navegador), busca as últimas 50 reproduções via `current_user_recently_played`, e faz merge com o `historico.csv` existente — sem duplicar (dedup por `played_at` + `track_id`), sempre reordenando por data.
4. **`python gerar_dashboard.py`**: lê o `historico.csv` inteiro e regenera `docs/index.html` (estático — o filtro de datas do site roda em JavaScript, no navegador de quem visita, sem precisar de servidor).
5. **Commit + push** do `historico.csv` e `docs/index.html` atualizados, como o usuário `github-actions[bot]`.
6. Esse push na pasta `docs/` dispara automaticamente um novo deploy do **GitHub Pages**, atualizando o site em ~1-2 minutos.

## Scripts

Organizados por ciclo de vida: raiz = produção (rodado pela Action) ou estudo avulso; `setup/` = uso único ou manutenção pontual, não faz parte do pipeline automatizado.

**Raiz**

| Arquivo | O que faz | Quando roda |
|---|---|---|
| `historico_acumulado.py` | Busca reproduções recentes e atualiza o `historico.csv` | A cada hora, pela Action |
| `gerar_dashboard.py` | Gera o `docs/index.html` a partir do `historico.csv` | A cada hora, pela Action (logo após o script acima) |
| `top_musicas_artistas.py` | Top artistas/músicas por período (curto/médio/longo prazo) — usa o endpoint de "Top" do próprio Spotify, não tem relação com o `historico.csv` nem com o site | Manual, script de estudo/exploração da API |

**`setup/`**

| Arquivo | O que faz | Quando roda |
|---|---|---|
| `autenticacao.py` | Primeiro teste de login OAuth com a Spotipy — confirma que a autenticação funciona | Já cumpriu seu papel; superado por `historico_acumulado.py`, que já autentica + captura dados |
| `gerar_refresh_token.py` | Gera o refresh token usado pela Action | Uma vez, e de novo só se o token for revogado |
| `preencher_duracao.py` | Preenche a duração (`duration_ms`) das músicas do histórico | Uma vez, e de novo só se faltar duração em alguma linha |
| `integrar_historico_completo.py` | Importa o export "Extended Streaming History" do Spotify (pasta `spotify_history_until_YYYYMMDD/` na raiz) e mescla com o `historico.csv`, sem duplicar | Uma vez por export pedido; rode `preencher_duracao.py` em seguida pra preencher a duração das músicas novas importadas |

## Rodando localmente

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # preencha com seu client_id/client_secret do Spotify Developer Dashboard
.venv/bin/python historico_acumulado.py
.venv/bin/python gerar_dashboard.py
```

## Sobre os dados

O repositório é público, então `historico.csv` (música, artista, álbum, duração, data/hora) fica visível pra qualquer um. O export bruto do Spotify (que contém IP, país de conexão etc.) **não** é versionado — fica só localmente, ignorado pelo `.gitignore`.
