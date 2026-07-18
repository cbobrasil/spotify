"""
Como o Spotify não expõe contagem histórica de "quantas vezes ouvi essa
música", a saída é construir nosso próprio histórico aos poucos.

A cada execução, este script busca as últimas 50 reproduções
(current_user_recently_played) e adiciona ao arquivo historico.csv as
que ainda não estavam lá (usando o timestamp "played_at" — que é único
por reprodução — para não duplicar).

Rode este script de tempos em tempos (ex: uma vez por dia) para ir
acumulando um histórico real. Como o Spotify só devolve as últimas 50
reproduções por chamada, se você ouvir muito mais que isso entre uma
execução e outra, algumas reproduções no meio podem ficar de fora.

Dois modos de autenticação:
  - Local (padrão): abre o navegador para você autorizar (fluxo normal).
  - CI / não-interativo: se a variável de ambiente SPOTIFY_REFRESH_TOKEN
    estiver definida (ex: rodando no GitHub Actions), usamos ela para
    pegar um access token novo sem precisar de navegador. Veja
    gerar_refresh_token.py para gerar esse valor uma única vez.
"""

import csv
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import spotipy
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SCOPE = "user-read-recently-played"
CSV_PATH = Path(__file__).parent / "historico.csv"
CSV_FIELDS = [
    "played_at",
    "track_id",
    "track_name",
    "artistas",
    "album",
    "album_id",
    "album_artista",
    "duration_ms",
    "salvo_em",
]

REFRESH_TOKEN = os.environ.get("SPOTIFY_REFRESH_TOKEN")

if REFRESH_TOKEN:
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIPY_CLIENT_ID"],
        client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
        redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
        scope=SCOPE,
        cache_handler=MemoryCacheHandler(),
    )
    token_info = auth_manager.refresh_access_token(REFRESH_TOKEN)
    sp = spotipy.Spotify(auth=token_info["access_token"])
else:
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIPY_CLIENT_ID"],
        client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"],
        scope=SCOPE,
    )
    print(f"Se o navegador não abrir automaticamente, acesse:\n{auth_manager.get_authorize_url()}\n")
    sp = spotipy.Spotify(auth_manager=auth_manager)


def chave_dedup(played_at_str, track_id):
    """Normaliza pro segundo (sem milissegundos), já que reproduções
    importadas do export completo do Spotify usam precisão diferente
    da API 'recently played'."""
    dt = datetime.fromisoformat(played_at_str.replace("Z", "+00:00"))
    return (dt.replace(microsecond=0).isoformat(), track_id)


def carregar_linhas_existentes():
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def buscar_reproducoes_recentes():
    resultado = sp.current_user_recently_played(limit=50)
    reproducoes = []
    for item in resultado["items"]:
        track = item["track"]
        reproducoes.append(
            {
                "played_at": item["played_at"],
                "track_id": track["id"],
                "track_name": track["name"],
                "artistas": ", ".join(a["name"] for a in track["artists"]),
                "album": track["album"]["name"],
                "album_id": track["album"]["id"] or "",
                "album_artista": ", ".join(a["name"] for a in track["album"]["artists"]),
                "duration_ms": track["duration_ms"],
            }
        )
    return reproducoes


def salvar_novas(reproducoes, linhas_existentes):
    vistos = {
        chave_dedup(linha["played_at"], linha["track_id"]): linha for linha in linhas_existentes
    }

    salvo_em = datetime.now(timezone.utc).isoformat()
    qtd_novas = 0
    for r in reproducoes:
        chave = chave_dedup(r["played_at"], r["track_id"])
        if chave in vistos:
            continue
        r["salvo_em"] = salvo_em
        vistos[chave] = r
        qtd_novas += 1

    if qtd_novas == 0:
        return 0

    todas = sorted(vistos.values(), key=lambda l: l["played_at"], reverse=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(todas)
    return qtd_novas


def mostrar_ranking():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))

    contagem = Counter((linha["track_name"], linha["artistas"]) for linha in linhas)
    print(f"\n=== Ranking acumulado até agora ({len(linhas)} reproduções registradas) ===")
    for (nome, artistas), vezes in contagem.most_common(None):
        print(f"{vezes:3d}x  {nome} — {artistas}")


if __name__ == "__main__":
    linhas_existentes = carregar_linhas_existentes()
    reproducoes = buscar_reproducoes_recentes()
    qtd_novas = salvar_novas(reproducoes, linhas_existentes)
    print(f"{qtd_novas} nova(s) reprodução(ões) adicionada(s) a {CSV_PATH.name}")
    mostrar_ranking()
