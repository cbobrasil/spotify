"""
Gera um dashboard estático (docs/index.html) a partir do historico.csv.

Rodado localmente ou pela Action do GitHub (que também publica o
resultado via GitHub Pages, servindo a pasta docs/ da branch main).

Ajuste TIMEZONE abaixo se "Padrões de horário/dia" não bater com o seu
fuso horário real.
"""

import csv
import html
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Europe/Lisbon")
CSV_PATH = Path(__file__).parent / "historico.csv"
OUT_PATH = Path(__file__).parent / "docs" / "index.html"
DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

# Paleta validada (dataviz skill) — ver referencia em references/palette.md
CORES_CATEGORICAS = ["#2a78d6", "#1baf7a", "#eda100", "#008300"]  # blue, aqua, yellow, green


def carregar_linhas():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        dt_utc = datetime.fromisoformat(linha["played_at"].replace("Z", "+00:00"))
        linha["dt_local"] = dt_utc.astimezone(TIMEZONE)
    return linhas


def compacto(n):
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    return f"{n / 1_000_000:.1f}M".replace(".0M", "M")


def teto_bonito(valor):
    if valor <= 0:
        return 1
    exp = math.floor(math.log10(valor))
    base = 10**exp
    for m in (1, 2, 5, 10):
        if valor <= m * base:
            return m * base
    return 10 * base


# ---------- agregações ----------

def calcular_stats(linhas):
    dts = [linha["dt_local"] for linha in linhas]
    return {
        "total_reproducoes": len(linhas),
        "artistas_unicos": len({linha["artistas"] for linha in linhas}),
        "musicas_unicas": len({linha["track_id"] for linha in linhas}),
        "primeiro_dt": min(dts) if dts else None,
        "ultimo_dt": max(dts) if dts else None,
        "primeiro_dia": min(dts).date() if dts else None,
        "ultimo_dia": max(dts).date() if dts else None,
    }


def calcular_heatmap(linhas):
    matriz = [[0] * 24 for _ in range(7)]
    for linha in linhas:
        dt = linha["dt_local"]
        matriz[dt.weekday()][dt.hour] += 1
    maximo = max((max(linha) for linha in matriz), default=0)
    return matriz, maximo


def dias_no_periodo(primeiro, ultimo):
    dias = []
    d = primeiro
    while d <= ultimo:
        dias.append(d)
        d = d.fromordinal(d.toordinal() + 1)
    return dias


def calcular_serie_diaria(linhas, dias):
    contagem = Counter(linha["dt_local"].date() for linha in linhas)
    return [(d, contagem.get(d, 0)) for d in dias]


def calcular_top_artistas_series(linhas, dias, n=4):
    total_por_artista = Counter(linha["artistas"] for linha in linhas)
    top = [nome for nome, _ in total_por_artista.most_common(n)]

    por_artista_dia = defaultdict(Counter)
    for linha in linhas:
        por_artista_dia[linha["artistas"]][linha["dt_local"].date()] += 1

    series = []
    for nome in top:
        pontos = [(d, por_artista_dia[nome].get(d, 0)) for d in dias]
        series.append({"nome": nome, "pontos": pontos, "total": total_por_artista[nome]})
    return series


def calcular_diversidade(linhas, dias):
    linhas_por_dia = defaultdict(list)
    for linha in linhas:
        linhas_por_dia[linha["dt_local"].date()].append(linha)

    vistos_tracks, vistos_artistas = set(), set()
    tracks_acumulado, artistas_acumulado = [], []
    for d in dias:
        for linha in linhas_por_dia.get(d, []):
            vistos_tracks.add(linha["track_id"])
            vistos_artistas.add(linha["artistas"])
        tracks_acumulado.append((d, len(vistos_tracks)))
        artistas_acumulado.append((d, len(vistos_artistas)))
    return tracks_acumulado, artistas_acumulado


# ---------- SVG ----------

def svg_linha(series, largura=720, altura=200, pad_esq=36, pad_dir=16, pad_topo=16, pad_baixo=28):
    todos_valores = [v for s in series for _, v in s["pontos"]]
    y_max = teto_bonito(max(todos_valores, default=1))
    n_pontos = len(series[0]["pontos"]) if series else 0

    area_w = largura - pad_esq - pad_dir
    area_h = altura - pad_topo - pad_baixo

    def x_de(i):
        if n_pontos <= 1:
            return pad_esq + area_w / 2
        return pad_esq + (area_w * i / (n_pontos - 1))

    def y_de(v):
        return pad_topo + area_h - (area_h * v / y_max if y_max else 0)

    partes = []
    # gridlines horizontais (0, meio, topo)
    for frac in (0, 0.5, 1):
        y = pad_topo + area_h * (1 - frac)
        valor = round(y_max * frac)
        partes.append(
            f'<line x1="{pad_esq}" y1="{y:.1f}" x2="{largura - pad_dir}" y2="{y:.1f}" '
            f'stroke="var(--grid)" stroke-width="1"/>'
        )
        partes.append(
            f'<text x="{pad_esq - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'class="rotulo-eixo">{valor}</text>'
        )

    for idx, s in enumerate(series):
        cor = f"var(--series-{idx + 1})"
        pontos = s["pontos"]
        if not pontos:
            continue
        coords = [(x_de(i), y_de(v)) for i, (_, v) in enumerate(pontos)]

        if len(coords) == 1:
            x, y = coords[0]
            partes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{cor}" stroke="var(--surface-1)" stroke-width="2"/>')
        else:
            path_linha = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
            baseline = pad_topo + area_h
            path_area = (
                f"M {coords[0][0]:.1f},{baseline:.1f} "
                + " L ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
                + f" L {coords[-1][0]:.1f},{baseline:.1f} Z"
            )
            partes.append(f'<path d="{path_area}" fill="{cor}" opacity="0.10" stroke="none"/>')
            partes.append(f'<path d="{path_linha}" fill="none" stroke="{cor}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
            x_fim, y_fim = coords[-1]
            partes.append(f'<circle cx="{x_fim:.1f}" cy="{y_fim:.1f}" r="4" fill="{cor}" stroke="var(--surface-1)" stroke-width="2"/>')

        # pontos com <title> para hover nativo
        for (data_pt, valor_pt), (x, y) in zip(pontos, coords):
            titulo = escapar(f"{s['nome']} — {data_pt.strftime('%d/%m')}: {valor_pt}")
            partes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="transparent"><title>{titulo}</title></circle>')

        # rótulo direto no fim da linha
        x_fim, y_fim = coords[-1]
        partes.append(
            f'<text x="{x_fim + 6:.1f}" y="{y_fim + 4:.1f}" class="rotulo-direto">{s["pontos"][-1][1]}</text>'
        )

    # eixo x: poucas datas (início, meio, fim)
    if n_pontos > 0:
        indices_rotulo = sorted({0, n_pontos // 2, n_pontos - 1})
        for i in indices_rotulo:
            x = x_de(i)
            data_pt = series[0]["pontos"][i][0]
            partes.append(
                f'<text x="{x:.1f}" y="{altura - 6}" text-anchor="middle" class="rotulo-eixo">{data_pt.strftime("%d/%m")}</text>'
            )

    corpo = "\n".join(partes)
    return f'<svg viewBox="0 0 {largura} {altura}" class="grafico">{corpo}</svg>'


def svg_heatmap(matriz, maximo, largura=720):
    cel = (largura - 60) / 24
    altura = 7 * (cel + 2) + 40
    ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

    partes = []
    for linha_idx, linha in enumerate(matriz):
        y = linha_idx * (cel + 2) + 10
        partes.append(f'<text x="44" y="{y + cel / 2 + 4:.1f}" text-anchor="end" class="rotulo-eixo">{DIAS_SEMANA[linha_idx]}</text>')
        for hora, valor in enumerate(linha):
            x = 50 + hora * (cel + 2)
            if maximo == 0:
                cor = "var(--surface-1)"
            else:
                passo = min(len(ramp) - 1, round((valor / maximo) * (len(ramp) - 1)))
                cor = ramp[passo] if valor > 0 else "var(--surface-1)"
            titulo = escapar(f"{DIAS_SEMANA[linha_idx]} {hora:02d}h: {valor} reprodução(ões)")
            partes.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cel:.1f}" height="{cel:.1f}" rx="3" '
                f'fill="{cor}" stroke="var(--border)" stroke-width="1"><title>{titulo}</title></rect>'
            )

    for hora in (0, 6, 12, 18, 23):
        x = 50 + hora * (cel + 2) + cel / 2
        partes.append(f'<text x="{x:.1f}" y="{altura - 6}" text-anchor="middle" class="rotulo-eixo">{hora}h</text>')

    corpo = "\n".join(partes)
    return f'<svg viewBox="0 0 {largura} {altura:.0f}" class="grafico">{corpo}</svg>'


def legenda(series):
    itens = "".join(
        f'<span class="legenda-item"><i style="background:var(--series-{i + 1})"></i>{escapar(s["nome"])}</span>'
        for i, s in enumerate(series)
    )
    return f'<div class="legenda">{itens}</div>' if len(series) > 1 else ""


def escapar(s):
    return html.escape(str(s))


def stat_tile(label, valor, pequeno=False):
    classe = "tile-valor tile-valor-pequeno" if pequeno else "tile-valor"
    return f'''<div class="tile">
      <div class="tile-label">{escapar(label)}</div>
      <div class="{classe}">{escapar(valor)}</div>
    </div>'''


# ---------- montagem da página ----------

def montar_html(linhas):
    stats = calcular_stats(linhas)
    dias = dias_no_periodo(stats["primeiro_dia"], stats["ultimo_dia"]) if linhas else []

    heatmap_matriz, heatmap_max = calcular_heatmap(linhas)
    serie_total = calcular_serie_diaria(linhas, dias)
    top_artistas = calcular_top_artistas_series(linhas, dias, n=4)
    tracks_acum, artistas_acum = calcular_diversidade(linhas, dias)

    top_musicas = Counter((l["track_name"], l["artistas"]) for l in linhas).most_common(15)
    linhas_tabela = "".join(
        f"<tr><td>{escapar(nome)}</td><td>{escapar(art)}</td><td>{vezes}</td></tr>"
        for (nome, art), vezes in top_musicas
    )

    periodo = (
        f'{stats["primeiro_dt"].strftime("%d/%m %H:%M")} — {stats["ultimo_dt"].strftime("%d/%m %H:%M")}'
        if linhas
        else "sem dados"
    )

    tiles = "".join(
        [
            stat_tile("Reproduções registradas", compacto(stats["total_reproducoes"])),
            stat_tile("Artistas únicos", compacto(stats["artistas_unicos"])),
            stat_tile("Músicas únicas", compacto(stats["musicas_unicas"])),
            stat_tile("Período coberto", periodo, pequeno=True),
        ]
    )

    grafico_total = (
        svg_linha([{"nome": "Reproduções/dia", "pontos": serie_total}])
        if serie_total
        else "<p class='vazio'>Sem dados ainda.</p>"
    )

    subgraficos_artistas = "".join(
        f'''<div class="subchart">
          <h3>{escapar(s["nome"])} <span class="muted">({s["total"]}x)</span></h3>
          {svg_linha([s], altura=140)}
        </div>'''
        for s in top_artistas
    )

    serie_diversidade = [
        {"nome": "Músicas descobertas (acumulado)", "pontos": tracks_acum},
        {"nome": "Artistas descobertos (acumulado)", "pontos": artistas_acum},
    ]
    grafico_diversidade = svg_linha(serie_diversidade) if linhas else "<p class='vazio'>Sem dados ainda.</p>"

    agora = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M")

    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Meu histórico Spotify</title>
<style>
  :root {{
    --page: #f9f9f7; --surface-1: #fcfcfb;
    --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #898781;
    --grid: #e1e0d9; --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
    --series-1: #2a78d6; --series-2: #1baf7a; --series-3: #eda100; --series-4: #008300;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --page: #0d0d0d; --surface-1: #1a1a19;
      --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #898781;
      --grid: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
      --series-1: #3987e5; --series-2: #199e70; --series-3: #c98500; --series-4: #008300;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px; background: var(--page); color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  .wrap {{ max-width: 780px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .subtitulo {{ color: var(--text-secondary); font-size: 13px; margin: 0 0 24px; }}
  .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 28px; }}
  .tile {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }}
  .tile-label {{ font-size: 12px; color: var(--text-secondary); }}
  .tile-valor {{ font-size: 24px; font-weight: 600; margin-top: 4px; }}
  .tile-valor-pequeno {{ font-size: 16px; }}
  section {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px; margin-bottom: 20px; }}
  section h2 {{ font-size: 15px; margin: 0 0 12px; }}
  .grafico {{ width: 100%; height: auto; display: block; }}
  .rotulo-eixo {{ font-size: 10px; fill: var(--text-muted); }}
  .rotulo-direto {{ font-size: 11px; fill: var(--text-secondary); font-weight: 600; }}
  .legenda {{ display: flex; gap: 14px; margin-bottom: 10px; flex-wrap: wrap; }}
  .legenda-item {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }}
  .legenda-item i {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; }}
  .subcharts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
  .subchart h3 {{ font-size: 13px; margin: 0 0 6px; font-weight: 600; }}
  .muted {{ color: var(--text-muted); font-weight: 400; }}
  .vazio {{ color: var(--text-muted); font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--grid); }}
  th {{ color: var(--text-secondary); font-weight: 600; }}
  td:last-child, th:last-child {{ text-align: right; font-variant-numeric: tabular-nums; }}
  details summary {{ cursor: pointer; font-size: 13px; color: var(--text-secondary); }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Meu histórico Spotify</h1>
  <p class="subtitulo">Atualizado em {agora} · fuso {TIMEZONE.key}</p>

  <div class="tiles">{tiles}</div>

  <section>
    <h2>Quando eu mais ouço música</h2>
    {svg_heatmap(heatmap_matriz, heatmap_max)}
  </section>

  <section>
    <h2>Reproduções por dia</h2>
    {grafico_total}
  </section>

  <section>
    <h2>Top artistas ao longo do tempo</h2>
    <div class="subcharts">{subgraficos_artistas}</div>
  </section>

  <section>
    <h2>Descobrindo música nova</h2>
    {legenda(serie_diversidade)}
    {grafico_diversidade}
  </section>

  <section>
    <h2>Top 15 músicas (tabela)</h2>
    <details open>
      <summary>Ver dados</summary>
      <table>
        <thead><tr><th>Música</th><th>Artista(s)</th><th>Vezes</th></tr></thead>
        <tbody>{linhas_tabela}</tbody>
      </table>
    </details>
  </section>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    linhas = carregar_linhas()
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(montar_html(linhas), encoding="utf-8")
    print(f"Dashboard gerado em {OUT_PATH}")
