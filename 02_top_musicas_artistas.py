"""
Segundo contato com a Spotipy: buscar seus artistas e músicas mais
ouvidos.

Como pedimos aqui um escopo (scope) diferente do primeiro script
(user-top-read), o Spotipy vai detectar que o token em cache não cobre
essa permissão e vai pedir login/autorização de novo automaticamente.
"""

import os

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SCOPE = "user-top-read"

auth_manager = SpotifyOAuth(
    client_id=os.environ["SPOTIPY_CLIENT_ID"],
    client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"],
    scope=SCOPE,
)
print(f"Se o navegador não abrir automaticamente, acesse:\n{auth_manager.get_authorize_url()}\n")

sp = spotipy.Spotify(auth_manager=auth_manager)

# time_range define o período considerado:
#   short_term  -> ~últimas 4 semanas
#   medium_term -> ~últimos 6 meses (padrão)
#   long_term   -> vários anos de histórico
# limit define quantos itens vêm na resposta (máximo 50 por chamada).
TIME_RANGE = "long_term"
LIMIT = 10

print(f"=== Top {LIMIT} artistas ({TIME_RANGE}) ===")
top_artists = sp.current_user_top_artists(time_range=TIME_RANGE, limit=LIMIT)
for i, artist in enumerate(top_artists["items"], start=1):
    generos = ", ".join(artist["genres"][:3]) or "sem gênero listado"
    print(f"{i:2d}. {artist['name']} — {generos}")

print(f"\n=== Top {LIMIT} músicas ({TIME_RANGE}) ===")
top_tracks = sp.current_user_top_tracks(time_range=TIME_RANGE, limit=LIMIT)
for i, track in enumerate(top_tracks["items"], start=1):
    artistas = ", ".join(a["name"] for a in track["artists"])
    print(f"{i:2d}. {track['name']} — {artistas}")
