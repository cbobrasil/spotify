"""
Script one-off: busca o ID e o artista do álbum de cada música única já
presente no historico.csv, usando sp.tracks() em lotes de 50.

Sem isso, "top álbuns" não tinha como agrupar direito — o nome do álbum
sozinho não é único (usar (álbum, artistas da faixa) juntava errado,
porque cada faixa de um álbum pode ter participações diferentes, tipo
"Gorillaz, Sparks" numa música e "Gorillaz, Mark E. Smith" noutra do
mesmo álbum "The Mountain").

Rode uma vez. Músicas novas capturadas pelo historico_acumulado.py já
vêm com album_id direto na resposta do "recently played", sem precisar
rodar isto de novo — só é útil se aparecer alguma linha antiga sem
album_id preenchido.
"""

import csv
import os
from pathlib import Path

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

CSV_PATH = Path(__file__).parent.parent / "historico.csv"
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
SCOPE = "user-read-recently-played"

auth_manager = SpotifyOAuth(
    client_id=os.environ["SPOTIPY_CLIENT_ID"],
    client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"],
    scope=SCOPE,
)
print(f"Se o navegador não abrir automaticamente, acesse:\n{auth_manager.get_authorize_url()}\n")
sp = spotipy.Spotify(auth_manager=auth_manager)


if __name__ == "__main__":
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))

    faltando = sorted({l["track_id"] for l in linhas if l["track_id"] and not l.get("album_id")})
    print(f"{len(faltando)} música(s) única(s) sem album_id ainda.")

    albuns = {}
    for i in range(0, len(faltando), 50):
        lote = faltando[i : i + 50]
        resultado = sp.tracks(lote)
        for track in resultado["tracks"]:
            if track:
                albuns[track["id"]] = {
                    "album_id": track["album"]["id"] or "",
                    "album_artista": ", ".join(a["name"] for a in track["album"]["artists"]),
                }
        print(f"{min(i + 50, len(faltando))}/{len(faltando)} consultadas...")

    for linha in linhas:
        if not linha.get("album_id") and linha["track_id"] in albuns:
            linha["album_id"] = albuns[linha["track_id"]]["album_id"]
            linha["album_artista"] = albuns[linha["track_id"]]["album_artista"]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(linhas)

    print(f"historico.csv atualizado. {len(albuns)} álbum(ns) preenchido(s) nesta rodada.")
