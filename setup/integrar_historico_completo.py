"""
Importa o export "Extended Streaming History" do Spotify
(arquivos Streaming_History_Audio_*.json) e faz merge com o
historico.csv que já vínhamos acumulando pela Action de hora em hora.

Rode este script UMA VEZ, localmente, com a pasta do export extraída na
raiz do repositório (ajuste EXPORT_DIR abaixo se o nome da pasta for
outro). Depois é só commitar o historico.csv resultante — a Action
continua rodando normalmente a partir daí.

As linhas importadas ficam sem duration_ms (o export não traz a duração
"nominal" da faixa, só o ms_played de cada stream) — rode
setup/preencher_duracao.py em seguida pra preencher isso.

Ignora podcasts/audiobooks (não têm master_metadata_track_name) e
arquivos de vídeo (Streaming_History_Video_*.json) — focamos só em
músicas, que é o que o resto do projeto já acompanha.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
CSV_PATH = REPO_DIR / "historico.csv"
EXPORT_DIR = REPO_DIR / "spotify_history_until_20260712"
CSV_FIELDS = ["played_at", "track_id", "track_name", "artistas", "album", "duration_ms", "salvo_em"]


def chave_dedup(played_at_str, track_id):
    """Normaliza o timestamp pro segundo (sem milissegundos) porque o
    export do Spotify e a API "recently played" formatam o horário com
    precisões diferentes — sem isso, a mesma reprodução podia entrar
    duplicada."""
    dt = datetime.fromisoformat(played_at_str.replace("Z", "+00:00"))
    return (dt.replace(microsecond=0).isoformat(), track_id)


def carregar_csv_existente():
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def carregar_export():
    linhas = []
    arquivos = sorted(EXPORT_DIR.glob("Streaming_History_Audio_*.json"))
    for arquivo in arquivos:
        with open(arquivo, encoding="utf-8") as f:
            registros = json.load(f)
        for r in registros:
            if not r.get("master_metadata_track_name"):
                continue  # pula podcast/audiobook
            uri = r.get("spotify_track_uri") or ""
            track_id = uri.split(":")[-1] if uri else ""
            linhas.append(
                {
                    "played_at": r["ts"],
                    "track_id": track_id,
                    "track_name": r["master_metadata_track_name"],
                    "artistas": r.get("master_metadata_album_artist_name") or "",
                    "album": r.get("master_metadata_album_album_name") or "",
                    "duration_ms": "",
                }
            )
    return linhas, len(arquivos)


def mesclar(existentes, importadas):
    vistos = {}
    for linha in existentes:
        vistos[chave_dedup(linha["played_at"], linha["track_id"])] = linha

    agora = datetime.now(timezone.utc).isoformat()
    novas = 0
    for linha in importadas:
        chave = chave_dedup(linha["played_at"], linha["track_id"])
        if chave in vistos:
            continue
        linha["salvo_em"] = agora
        vistos[chave] = linha
        novas += 1

    todas = sorted(vistos.values(), key=lambda l: l["played_at"], reverse=True)
    return todas, novas


if __name__ == "__main__":
    existentes = carregar_csv_existente()
    importadas, qtd_arquivos = carregar_export()
    todas, novas = mesclar(existentes, importadas)

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(todas)

    print(f"{qtd_arquivos} arquivo(s) de export lidos, {len(importadas)} reproduções de música no export.")
    print(f"{novas} nova(s) reprodução(ões) incorporada(s) (o resto já estava no historico.csv).")
    print(f"historico.csv agora tem {len(todas)} linhas no total.")
