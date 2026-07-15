"""
Script one-off: busca a duração (duration_ms) de cada música única já
presente no historico.csv e preenche essa coluna, usando sp.tracks()
em lotes de 50 (limite da API por chamada).

Rode uma vez. Músicas novas capturadas pelo 03_historico_acumulado.py
já vêm com a duração direto na resposta do "recently played", sem
precisar rodar isto de novo — só é útil se aparecer alguma linha
antiga sem duration_ms preenchido.
"""

import csv
import os
from pathlib import Path

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

CSV_PATH = Path(__file__).parent / "historico.csv"
CSV_FIELDS = ["played_at", "track_id", "track_name", "artistas", "album", "duration_ms", "salvo_em"]
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

    faltando = sorted({l["track_id"] for l in linhas if l["track_id"] and not l.get("duration_ms")})
    print(f"{len(faltando)} música(s) única(s) sem duração ainda.")

    duracoes = {}
    for i in range(0, len(faltando), 50):
        lote = faltando[i : i + 50]
        resultado = sp.tracks(lote)
        for track in resultado["tracks"]:
            if track:
                duracoes[track["id"]] = track["duration_ms"]
        print(f"{min(i + 50, len(faltando))}/{len(faltando)} consultadas...")

    for linha in linhas:
        if not linha.get("duration_ms") and linha["track_id"] in duracoes:
            linha["duration_ms"] = duracoes[linha["track_id"]]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(linhas)

    print(f"historico.csv atualizado. {len(duracoes)} duração(ões) preenchida(s) nesta rodada.")
