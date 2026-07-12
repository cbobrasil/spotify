"""
Rode este script UMA VEZ, localmente (com navegador disponível), para
gerar um refresh_token que pode ser usado em ambientes sem navegador
(como GitHub Actions).

O refresh_token funciona como uma "senha de longa duração": com ele,
dá pra pedir novos access_tokens ao Spotify sem repetir o login.
Trate-o como um segredo — nunca cometa no git, guarde só como Secret
no GitHub (SPOTIFY_REFRESH_TOKEN).
"""

import os

from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SCOPE = "user-read-recently-played"

auth_manager = SpotifyOAuth(
    client_id=os.environ["SPOTIPY_CLIENT_ID"],
    client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"],
    scope=SCOPE,
)
print(f"Se o navegador não abrir automaticamente, acesse:\n{auth_manager.get_authorize_url()}\n")

token_info = auth_manager.get_access_token(as_dict=True)

print("\nAutenticado! Guarde o valor abaixo como Secret no GitHub,")
print("com o nome SPOTIFY_REFRESH_TOKEN. NÃO cometa isso em nenhum arquivo:\n")
print(token_info["refresh_token"])
