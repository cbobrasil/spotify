"""
Primeiro contato com a Spotipy: autenticar e confirmar que a conexão
com a sua conta do Spotify funciona.

Fluxo usado aqui: Authorization Code Flow (via SpotifyOAuth), que é o
indicado quando queremos acessar dados PESSOAIS do usuário (não apenas
dados públicos, como catálogo de músicas).

Na primeira execução, uma aba do navegador vai abrir pedindo pra você
autorizar o app "CBO" a acessar sua conta. Depois disso, a Spotipy
guarda um token em cache (arquivo .cache) e não pede login de novo
até o token expirar.
"""

import os

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

# "Escopos" (scopes) definem quais permissões estamos pedindo ao usuário.
# Aqui pedimos apenas para ler o perfil básico da conta.
SCOPE = "user-read-private user-read-email"

auth_manager = SpotifyOAuth(
    client_id=os.environ["SPOTIPY_CLIENT_ID"],
    client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"],
    scope=SCOPE,
)

# Se o navegador não abrir sozinho (ex: rodando num terminal sem GUI),
# copie e cole esta URL manualmente no seu navegador.
print(f"Se o navegador não abrir automaticamente, acesse:\n{auth_manager.get_authorize_url()}\n")

sp = spotipy.Spotify(auth_manager=auth_manager)

me = sp.current_user()

print("Autenticado com sucesso!")
print(f"Nome: {me['display_name']}")
print(f"ID:   {me['id']}")
print(f"Plano: {me['product']}")
print(f"Seguidores: {me['followers']['total']}")
