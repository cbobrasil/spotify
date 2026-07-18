"""
Gera um dashboard estático (docs/index.html) a partir do historico.csv.

Diferente da primeira versão, aqui o Python só prepara os dados
(compactados em JSON, embutidos na página) — todo o cálculo dos
gráficos e o filtro de datas rodam em JavaScript no navegador. Isso é
necessário porque o filtro de período precisa recalcular tudo
dinamicamente, e um site estático não tem servidor pra fazer isso sob
demanda.

Rodado localmente ou pela Action do GitHub (que também publica o
resultado via GitHub Pages, servindo a pasta docs/ da branch main).

Ajuste TIMEZONE abaixo se os gráficos de horário/dia não baterem com o
seu fuso horário real.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Europe/Lisbon")
CSV_PATH = Path(__file__).parent / "historico.csv"
OUT_PATH = Path(__file__).parent / "docs" / "index.html"


def carregar_linhas():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def preparar_dados(linhas):
    """Compacta o histórico em duas estruturas pequenas:
    - tracks: tabela de músicas únicas (evita repetir nome/artista/álbum em cada play)
    - plays: [ordinal_dia_local, hora_local, minuto_local, indice_da_track]

    O "ordinal" é o número de dias desde 01/01/ano 1 (mesmo esquema do
    date.toordinal() do Python) já convertido pro fuso local — assim o
    JavaScript faz toda a matemática de calendário (dia da semana, mês,
    filtro por período) sem precisar lidar com fuso horário de verdade."""
    indice = {}
    tracks = []
    plays = []
    for linha in linhas:
        dt_utc = datetime.fromisoformat(linha["played_at"].replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone(TIMEZONE)

        track_id = linha["track_id"]
        if track_id not in indice:
            indice[track_id] = len(tracks)
            duration_ms = int(linha["duration_ms"]) if linha.get("duration_ms") else 0
            tracks.append(
                [
                    track_id,
                    linha["track_name"],
                    linha["artistas"],
                    duration_ms,
                    linha["album"],
                    linha.get("album_id") or "",
                    linha.get("album_artista") or "",
                ]
            )

        plays.append([dt_local.date().toordinal(), dt_local.hour, dt_local.minute, indice[track_id]])
    return tracks, plays


def json_seguro(obj):
    """json.dumps compacto, escapando '</' pra não fechar a tag <script> sem querer."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


HTML_TEMPLATE = """<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Meu histórico Spotify</title>
<style>
  :root {
    --page: #f9f9f7; --surface-1: #fcfcfb;
    --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #898781;
    --grid: #e1e0d9; --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
    --series-1: #2a78d6; --series-2: #1baf7a; --series-3: #eda100; --series-4: #008300;
    --accent-bg: #eaf1fc; --accent-border: #2a78d6;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --page: #0d0d0d; --surface-1: #1a1a19;
      --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #898781;
      --grid: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
      --series-1: #3987e5; --series-2: #199e70; --series-3: #c98500; --series-4: #008300;
      --accent-bg: #16324f; --accent-border: #3987e5;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px; background: var(--page); color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .wrap { max-width: 780px; margin: 0 auto; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .subtitulo { color: var(--text-secondary); font-size: 13px; margin: 0 0 20px; }
  .filtros {
    display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px;
    background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px;
    padding: 10px 14px; margin-bottom: 20px;
  }
  .filtros-presets { display: flex; flex-wrap: wrap; gap: 6px; }
  .filtros-presets button {
    font: inherit; font-size: 12px; padding: 6px 10px; border-radius: 999px;
    border: 1px solid var(--border); background: transparent; color: var(--text-secondary);
    cursor: pointer;
  }
  .filtros-presets button:hover { background: var(--grid); }
  .filtros-presets button.ativo {
    background: var(--accent-bg); border-color: var(--accent-border);
    color: var(--text-primary); font-weight: 600;
  }
  .filtros-custom {
    display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary);
    padding-left: 12px; border-left: 1px solid var(--border);
  }
  .filtros-custom input[type="date"] {
    font: inherit; font-size: 12px; padding: 5px 6px; border-radius: 6px;
    border: 1px solid var(--border); background: var(--page); color: var(--text-primary);
  }
  .data-preview { color: var(--text-muted); font-variant-numeric: tabular-nums; }
  .filtros-custom button {
    font: inherit; font-size: 12px; padding: 6px 10px; border-radius: 6px;
    border: 1px solid var(--accent-border); background: var(--accent-bg); color: var(--text-primary);
    cursor: pointer;
  }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 28px; }
  .tile { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
  .tile-label { font-size: 12px; color: var(--text-secondary); }
  .tile-valor { font-size: 24px; font-weight: 600; margin-top: 4px; }
  .tile-valor-pequeno { font-size: 16px; }
  section { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px; margin-bottom: 20px; }
  section h2 { font-size: 15px; margin: 0 0 12px; }
  .grafico { width: 100%; height: auto; display: block; }
  .rotulo-eixo { font-size: 10px; fill: var(--text-muted); }
  .rotulo-direto { font-size: 11px; fill: var(--text-secondary); font-weight: 600; }
  .subcharts { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
  .subchart h3 { font-size: 13px; margin: 0 0 6px; font-weight: 600; }
  .muted { color: var(--text-muted); font-weight: 400; }
  .vazio { color: var(--text-muted); font-size: 13px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--grid); }
  th { color: var(--text-secondary); font-weight: 600; }
  td:last-child, th:last-child { text-align: right; font-variant-numeric: tabular-nums; }
  details summary { cursor: pointer; font-size: 13px; color: var(--text-secondary); }
  .comparacao-tiles { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }
  .comparacao-tiles .tile { flex: 1; min-width: 180px; }
  .delta { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Meu histórico Spotify</h1>
  <p class="subtitulo">Atualizado em __GERADO_EM__ · fuso __TIMEZONE_KEY__</p>

  <div class="filtros">
    <div class="filtros-presets">
      <button data-preset="7">7 dias</button>
      <button data-preset="30">30 dias</button>
      <button data-preset="90">90 dias</button>
      <button data-preset="ano">Este ano</button>
      <button data-preset="tudo" class="ativo">Tudo</button>
    </div>
    <div class="filtros-custom">
      <input type="date" id="data-inicio" lang="pt-BR" aria-label="Data inicial">
      <span class="data-preview" id="preview-inicio"></span>
      <span>até</span>
      <input type="date" id="data-fim" lang="pt-BR" aria-label="Data final">
      <span class="data-preview" id="preview-fim"></span>
      <button id="aplicar-custom" type="button">Aplicar</button>
    </div>
  </div>

  <div class="tiles" id="tiles"></div>

  <section id="secao-comparacao">
    <h2>Comparado ao período anterior</h2>
    <div id="comparacao"></div>
  </section>

  <section>
    <h2>Quando eu mais ouço música</h2>
    <div id="heatmap"></div>
  </section>

  <section>
    <h2>Dia da semana</h2>
    <div id="grafico-dia-semana"></div>
  </section>

  <section>
    <h2 id="titulo-serie">Reproduções</h2>
    <div id="grafico-total"></div>
  </section>

  <section>
    <h2>Top artistas no período</h2>
    <div class="subcharts" id="subcharts-artistas"></div>
  </section>

  <section>
    <h2>Top 15 músicas (tabela)</h2>
    <details open>
      <summary>Ver dados</summary>
      <table>
        <thead><tr><th>Música</th><th>Artista(s)</th><th>Vezes</th></tr></thead>
        <tbody id="tabela-musicas"></tbody>
      </table>
    </details>
  </section>

  <section>
    <h2>Top 15 álbuns (tabela)</h2>
    <details open>
      <summary>Ver dados</summary>
      <table>
        <thead><tr><th>Álbum</th><th>Artista(s)</th><th>Vezes</th></tr></thead>
        <tbody id="tabela-albuns"></tbody>
      </table>
    </details>
  </section>
</div>

<script>
(function () {
  "use strict";
  const TRACKS = __TRACKS_JSON__;
  const PLAYS = __PLAYS_JSON__;

  const DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
  const SEQ_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];
  const EPOCH_ORDINAL = 719163; // ordinal (estilo Python) de 1970-01-01
  const FORMATO_ROTULO = { dia: "dia", semana: "semana", mes: "mês" };

  function ordinalParaData(ordinal) {
    return new Date((ordinal - EPOCH_ORDINAL) * 86400000);
  }
  function dataParaOrdinal(ano, mes0, dia) {
    return Math.floor(Date.UTC(ano, mes0, dia) / 86400000) + EPOCH_ORDINAL;
  }
  function weekdayDe(ordinal) {
    return (ordinalParaData(ordinal).getUTCDay() + 6) % 7; // 0=Seg .. 6=Dom
  }
  function anoMesDe(ordinal) {
    const d = ordinalParaData(ordinal);
    return [d.getUTCFullYear(), d.getUTCMonth()];
  }

  function escapar(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function compacto(n) {
    if (n < 1000) return String(n);
    if (n < 1000000) return (n / 1000).toFixed(1).replace(".0", "") + "K";
    return (n / 1000000).toFixed(1).replace(".0", "") + "M";
  }

  function tetoBonito(valor) {
    if (valor <= 0) return 1;
    const exp = Math.floor(Math.log10(valor));
    const base = Math.pow(10, exp);
    for (const m of [1, 2, 5, 10]) {
      if (valor <= m * base) return m * base;
    }
    return 10 * base;
  }

  function escolherGranularidade(inicio, fim) {
    const totalDias = fim - inicio;
    if (totalDias <= 60) return "dia";
    if (totalDias <= 550) return "semana";
    return "mes";
  }

  function bucketDe(ordinal, granularidade) {
    if (granularidade === "dia") return ordinal;
    if (granularidade === "semana") return ordinal - weekdayDe(ordinal);
    const [ano, mes0] = anoMesDe(ordinal);
    return dataParaOrdinal(ano, mes0, 1);
  }

  function proximoBucket(ordinal, granularidade) {
    if (granularidade === "dia") return ordinal + 1;
    if (granularidade === "semana") return ordinal + 7;
    const [ano, mes0] = anoMesDe(ordinal);
    if (mes0 === 11) return dataParaOrdinal(ano + 1, 0, 1);
    return dataParaOrdinal(ano, mes0 + 1, 1);
  }

  function gerarBuckets(inicio, fim, granularidade) {
    const buckets = [];
    let atual = bucketDe(inicio, granularidade);
    const fimBucket = bucketDe(fim, granularidade);
    while (atual <= fimBucket) {
      buckets.push(atual);
      atual = proximoBucket(atual, granularidade);
    }
    return buckets;
  }

  function formatarData(ordinal, granularidade) {
    const d = ordinalParaData(ordinal);
    const dd = String(d.getUTCDate()).padStart(2, "0");
    const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
    if (granularidade === "mes") return mm + "/" + d.getUTCFullYear();
    return dd + "/" + mm;
  }

  /* Escolhe onde marcar o eixo X. Em vez de espalhar rótulos em pontos
     arbitrários (o que gerava datas soltas tipo "03/2022, 08/2023" sem
     contexto), marca nas fronteiras naturais do calendário: início de
     cada ano (granularidade mensal) ou início de cada mês (semanal). */
  function ticksEixoX(pontos, granularidade, areaW) {
    const n = pontos.length;
    if (n === 0) return [];

    if (granularidade === "mes") {
      let indices = [];
      pontos.forEach((pt, i) => {
        if (ordinalParaData(pt[0]).getUTCMonth() === 0) indices.push(i);
      });
      if (indices.length === 0) indices = [0, n - 1];
      return indices.map((i) => ({ i, rotulo: String(ordinalParaData(pontos[i][0]).getUTCFullYear()) }));
    }

    if (granularidade === "semana") {
      let indices = [];
      pontos.forEach((pt, i) => {
        if (ordinalParaData(pt[0]).getUTCDate() <= 7) indices.push(i);
      });
      if (indices.length === 0) indices = [0, n - 1];
      const maxTicks = Math.max(2, Math.floor(areaW / 55));
      if (indices.length > maxTicks) {
        const passo = Math.ceil(indices.length / maxTicks);
        indices = indices.filter((_, idx) => idx % passo === 0);
      }
      return indices.map((i) => {
        const d = ordinalParaData(pontos[i][0]);
        return { i, rotulo: String(d.getUTCMonth() + 1).padStart(2, "0") + "/" + d.getUTCFullYear() };
      });
    }

    // dia: período curto, mantém alguns pontos espaçados com dd/mm
    const nTicks = Math.min(5, n);
    const indicesSet = new Set();
    for (let k = 0; k < nTicks; k++) indicesSet.add(Math.round((k * (n - 1)) / Math.max(nTicks - 1, 1)));
    return [...indicesSet].sort((a, b) => a - b).map((i) => ({ i, rotulo: formatarData(pontos[i][0], granularidade) }));
  }

  function compararPlay(a, b) {
    if (a[0] !== b[0]) return a[0] - b[0];
    if (a[1] !== b[1]) return a[1] - b[1];
    return a[2] - b[2];
  }

  function formatarPlayCompleto(p) {
    const d = ordinalParaData(p[0]);
    const dd = String(d.getUTCDate()).padStart(2, "0");
    const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
    const hh = String(p[1]).padStart(2, "0");
    const mi = String(p[2]).padStart(2, "0");
    return dd + "/" + mm + "/" + d.getUTCFullYear() + " " + hh + ":" + mi;
  }

  function filtrarPlays(inicio, fim) {
    return PLAYS.filter((p) => p[0] >= inicio && p[0] <= fim);
  }

  function calcularStats(plays) {
    if (plays.length === 0) {
      return { total: 0, artistasUnicos: 0, musicasUnicas: 0, tempoMs: 0, primeiro: null, ultimo: null };
    }
    const artistas = new Set();
    const musicas = new Set();
    let tempoMs = 0;
    let primeiro = plays[0];
    let ultimo = plays[0];
    for (const p of plays) {
      const t = TRACKS[p[3]];
      musicas.add(t[0]);
      artistas.add(t[2]);
      tempoMs += t[3] || 0;
      if (compararPlay(p, primeiro) < 0) primeiro = p;
      if (compararPlay(p, ultimo) > 0) ultimo = p;
    }
    return { total: plays.length, artistasUnicos: artistas.size, musicasUnicas: musicas.size, tempoMs, primeiro, ultimo };
  }

  function formatarDuracaoStat(ms) {
    const minutosTotais = Math.round(ms / 60000);
    const dias = Math.floor(minutosTotais / (60 * 24));
    const horas = Math.floor((minutosTotais % (60 * 24)) / 60);
    const minutos = minutosTotais % 60;
    if (dias > 0) return `${dias}d ${horas}h`;
    if (horas > 0) return `${horas}h ${minutos}min`;
    return `${minutos}min`;
  }

  function formatarDuracaoCompacta(ms) {
    const minutosTotais = Math.round(ms / 60000);
    const horas = Math.floor(minutosTotais / 60);
    const minutos = minutosTotais % 60;
    if (horas > 0) return `${horas}h${String(minutos).padStart(2, "0")}`;
    return `${minutos}min`;
  }

  function calcularHeatmap(plays) {
    const matriz = Array.from({ length: 7 }, () => new Array(24).fill(0));
    const matrizMs = Array.from({ length: 7 }, () => new Array(24).fill(0));
    for (const p of plays) {
      const wd = weekdayDe(p[0]);
      matriz[wd][p[1]]++;
      matrizMs[wd][p[1]] += TRACKS[p[3]][3] || 0;
    }
    let maximo = 0;
    for (const linha of matriz) for (const v of linha) if (v > maximo) maximo = v;
    return { matriz, matrizMs, maximo };
  }

  function calcularPorDiaSemana(plays) {
    const contagem = new Array(7).fill(0);
    const duracao = new Array(7).fill(0);
    for (const p of plays) {
      const wd = weekdayDe(p[0]);
      contagem[wd]++;
      duracao[wd] += TRACKS[p[3]][3] || 0;
    }
    return { contagem, duracao };
  }

  function calcularStreaks(plays) {
    if (!plays.length) return { atual: 0, recorde: 0 };
    const dias = [...new Set(plays.map((p) => p[0]))].sort((a, b) => a - b);
    let recorde = 1;
    let atual = 1;
    for (let i = 1; i < dias.length; i++) {
      atual = dias[i] === dias[i - 1] + 1 ? atual + 1 : 1;
      if (atual > recorde) recorde = atual;
    }
    return { atual, recorde };
  }

  function topAlbuns(plays, n) {
    // Agrupa por album_id (o nome do álbum sozinho não é único, e o
    // "artistas" da faixa pode variar por participação — ex: mesmo
    // álbum, faixas com features diferentes). Cai pra álbum+artista do
    // álbum só se faltar o ID (ex: alguma faixa antiga sem backfill).
    const contagem = new Map();
    for (const p of plays) {
      const t = TRACKS[p[3]];
      const album = t[4];
      if (!album) continue;
      const albumId = t[5];
      const albumArtista = t[6] || t[2];
      const chave = albumId || album + "\\u0001" + albumArtista;
      const atual = contagem.get(chave);
      if (atual) atual.vezes++;
      else contagem.set(chave, { album, artista: albumArtista, vezes: 1 });
    }
    return [...contagem.values()]
      .sort((a, b) => b.vezes - a.vezes)
      .slice(0, n)
      .map((e) => [e.album, e.artista, e.vezes]);
  }

  function contarPorArtista(plays) {
    const m = new Map();
    for (const p of plays) {
      const artista = TRACKS[p[3]][2];
      m.set(artista, (m.get(artista) || 0) + 1);
    }
    return m;
  }

  /* Compara o período filtrado com o período imediatamente anterior, de
     mesma duração (ex: filtrando "últimos 30 dias", compara com os 30
     dias antes disso) — funciona com qualquer preset ou range custom. */
  function calcularComparacao(inicio, fim) {
    const duracaoDias = fim - inicio;
    const fimAnterior = inicio - 1;
    const inicioAnterior = fimAnterior - duracaoDias;
    if (fimAnterior < dadosMinOrdinal) return null;
    const plays = filtrarPlays(Math.max(inicioAnterior, dadosMinOrdinal), fimAnterior);
    return { inicioAnterior, fimAnterior, plays };
  }

  function formatarDelta(atual, anterior) {
    if (anterior === 0) return atual > 0 ? "novo" : "—";
    const pct = Math.round(((atual - anterior) / anterior) * 100);
    if (pct === 0) return "sem mudança";
    return (pct > 0 ? "+" : "") + pct + "% vs período anterior";
  }

  function calcularSeriePorBucket(plays, buckets, granularidade) {
    const contagem = new Map();
    const duracao = new Map();
    for (const p of plays) {
      const b = bucketDe(p[0], granularidade);
      contagem.set(b, (contagem.get(b) || 0) + 1);
      duracao.set(b, (duracao.get(b) || 0) + (TRACKS[p[3]][3] || 0));
    }
    return buckets.map((b) => [b, contagem.get(b) || 0, duracao.get(b) || 0]);
  }

  function calcularTopArtistas(plays, buckets, granularidade, n) {
    const totalPorArtista = new Map();
    for (const p of plays) {
      const artista = TRACKS[p[3]][2];
      totalPorArtista.set(artista, (totalPorArtista.get(artista) || 0) + 1);
    }
    const top = [...totalPorArtista.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map((e) => e[0]);

    const porArtistaBucket = new Map();
    const duracaoPorArtistaBucket = new Map();
    for (const nome of top) {
      porArtistaBucket.set(nome, new Map());
      duracaoPorArtistaBucket.set(nome, new Map());
    }
    for (const p of plays) {
      const artista = TRACKS[p[3]][2];
      if (!porArtistaBucket.has(artista)) continue;
      const b = bucketDe(p[0], granularidade);
      porArtistaBucket.get(artista).set(b, (porArtistaBucket.get(artista).get(b) || 0) + 1);
      const durMapa = duracaoPorArtistaBucket.get(artista);
      durMapa.set(b, (durMapa.get(b) || 0) + (TRACKS[p[3]][3] || 0));
    }

    return top.map((nome) => ({
      nome,
      total: totalPorArtista.get(nome),
      pontos: buckets.map((b) => [b, porArtistaBucket.get(nome).get(b) || 0, duracaoPorArtistaBucket.get(nome).get(b) || 0]),
    }));
  }

  function topMusicas(plays, n) {
    const contagem = new Map();
    for (const p of plays) {
      const t = TRACKS[p[3]];
      const chave = t[1] + "\\u0001" + t[2];
      contagem.set(chave, (contagem.get(chave) || 0) + 1);
    }
    return [...contagem.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, n)
      .map(([chave, vezes]) => {
        const [nome, artistas] = chave.split("\\u0001");
        return [nome, artistas, vezes];
      });
  }

  function svgLinha(series, opts) {
    opts = opts || {};
    const largura = opts.largura || 720;
    const altura = opts.altura || 200;
    const padEsq = 36, padDir = 16, padTopo = 16, padBaixo = 28;
    const granularidade = opts.granularidade || "dia";

    const todosValores = [];
    for (const s of series) for (const pt of s.pontos) todosValores.push(pt[1]);
    const yMax = tetoBonito(todosValores.length ? Math.max(...todosValores) : 1);
    const nPontos = series.length ? series[0].pontos.length : 0;

    const areaW = largura - padEsq - padDir;
    const areaH = altura - padTopo - padBaixo;

    function xDe(i) {
      if (nPontos <= 1) return padEsq + areaW / 2;
      return padEsq + (areaW * i) / (nPontos - 1);
    }
    function yDe(v) {
      return padTopo + areaH - (yMax ? (areaH * v) / yMax : 0);
    }

    const partes = [];
    [0, 0.5, 1].forEach((frac) => {
      const y = padTopo + areaH * (1 - frac);
      const valor = Math.round(yMax * frac);
      partes.push(`<line x1="${padEsq}" y1="${y.toFixed(1)}" x2="${largura - padDir}" y2="${y.toFixed(1)}" stroke="var(--grid)" stroke-width="1"/>`);
      partes.push(`<text x="${padEsq - 8}" y="${(y + 4).toFixed(1)}" text-anchor="end" class="rotulo-eixo">${valor}</text>`);
    });

    series.forEach((s, idx) => {
      const cor = `var(--series-${idx + 1})`;
      const pontos = s.pontos;
      if (!pontos.length) return;
      const coords = pontos.map((pt, i) => [xDe(i), yDe(pt[1])]);

      if (coords.length === 1) {
        const [x, y] = coords[0];
        partes.push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4" fill="${cor}" stroke="var(--surface-1)" stroke-width="2"/>`);
      } else {
        const pathLinha = "M " + coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" L ");
        const baseline = padTopo + areaH;
        const pathArea =
          `M ${coords[0][0].toFixed(1)},${baseline.toFixed(1)} L ` +
          coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" L ") +
          ` L ${coords[coords.length - 1][0].toFixed(1)},${baseline.toFixed(1)} Z`;
        partes.push(`<path d="${pathArea}" fill="${cor}" opacity="0.10" stroke="none"/>`);
        partes.push(`<path d="${pathLinha}" fill="none" stroke="${cor}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`);
        const [xf, yf] = coords[coords.length - 1];
        partes.push(`<circle cx="${xf.toFixed(1)}" cy="${yf.toFixed(1)}" r="4" fill="${cor}" stroke="var(--surface-1)" stroke-width="2"/>`);
      }

      pontos.forEach((pt, i) => {
        const [x, y] = coords[i];
        const tempo = formatarDuracaoCompacta(pt[2] || 0);
        const titulo = escapar(`${s.nome} — ${formatarData(pt[0], granularidade)}: ${pt[1]} reprodução(ões) · ${tempo}`);
        partes.push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="8" fill="transparent"><title>${titulo}</title></circle>`);
      });

      const [xf, yf] = coords[coords.length - 1];
      partes.push(`<text x="${(xf + 6).toFixed(1)}" y="${(yf + 4).toFixed(1)}" class="rotulo-direto">${pontos[pontos.length - 1][1]}</text>`);
    });

    if (nPontos > 0) {
      ticksEixoX(series[0].pontos, granularidade, areaW).forEach(({ i, rotulo }) => {
        const x = xDe(i);
        partes.push(`<text x="${x.toFixed(1)}" y="${altura - 6}" text-anchor="middle" class="rotulo-eixo">${rotulo}</text>`);
      });
    }

    return `<svg viewBox="0 0 ${largura} ${altura}" class="grafico">${partes.join("\\n")}</svg>`;
  }

  function svgHeatmap(matriz, matrizMs, maximo, largura) {
    largura = largura || 720;
    const cel = (largura - 60) / 24;
    const altura = 7 * (cel + 2) + 40;
    const partes = [];
    matriz.forEach((linha, linhaIdx) => {
      const y = linhaIdx * (cel + 2) + 10;
      partes.push(`<text x="44" y="${(y + cel / 2 + 4).toFixed(1)}" text-anchor="end" class="rotulo-eixo">${DIAS_SEMANA[linhaIdx]}</text>`);
      linha.forEach((valor, hora) => {
        const x = 50 + hora * (cel + 2);
        let cor = "var(--surface-1)";
        if (maximo > 0 && valor > 0) {
          const passo = Math.min(SEQ_RAMP.length - 1, Math.round((valor / maximo) * (SEQ_RAMP.length - 1)));
          cor = SEQ_RAMP[passo];
        }
        const tempo = formatarDuracaoCompacta(matrizMs[linhaIdx][hora]);
        const titulo = escapar(`${DIAS_SEMANA[linhaIdx]} ${String(hora).padStart(2, "0")}h: ${valor} reprodução(ões) · ${tempo}`);
        partes.push(`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${cel.toFixed(1)}" height="${cel.toFixed(1)}" rx="3" fill="${cor}" stroke="var(--border)" stroke-width="1"><title>${titulo}</title></rect>`);
      });
    });
    [0, 6, 12, 18, 23].forEach((hora) => {
      const x = 50 + hora * (cel + 2) + cel / 2;
      partes.push(`<text x="${x.toFixed(1)}" y="${altura - 6}" text-anchor="middle" class="rotulo-eixo">${hora}h</text>`);
    });
    return `<svg viewBox="0 0 ${largura} ${altura.toFixed(0)}" class="grafico">${partes.join("\\n")}</svg>`;
  }

  function svgBarras(valores, valoresMs, rotulos, largura) {
    largura = largura || 720;
    const altura = 180;
    const padEsq = 36, padDir = 16, padTopo = 12, padBaixo = 28;
    const areaW = largura - padEsq - padDir;
    const areaH = altura - padTopo - padBaixo;
    const n = valores.length;
    const maximo = tetoBonito(Math.max(...valores, 1));
    const slot = areaW / n;
    const largBarra = Math.min(28, slot - 10);

    const partes = [];
    [0, 0.5, 1].forEach((frac) => {
      const y = padTopo + areaH * (1 - frac);
      const valor = Math.round(maximo * frac);
      partes.push(`<line x1="${padEsq}" y1="${y.toFixed(1)}" x2="${largura - padDir}" y2="${y.toFixed(1)}" stroke="var(--grid)" stroke-width="1"/>`);
      partes.push(`<text x="${padEsq - 8}" y="${(y + 4).toFixed(1)}" text-anchor="end" class="rotulo-eixo">${valor}</text>`);
    });

    valores.forEach((v, i) => {
      const cx = padEsq + slot * i + slot / 2;
      const h = maximo ? (areaH * v) / maximo : 0;
      const y = padTopo + areaH - h;
      const tempo = formatarDuracaoCompacta(valoresMs[i] || 0);
      const titulo = escapar(`${rotulos[i]}: ${v} reprodução(ões) · ${tempo}`);
      partes.push(`<rect x="${(cx - largBarra / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${largBarra.toFixed(1)}" height="${Math.max(h, 0).toFixed(1)}" rx="4" fill="var(--series-1)"><title>${titulo}</title></rect>`);
      partes.push(`<text x="${cx.toFixed(1)}" y="${altura - 6}" text-anchor="middle" class="rotulo-eixo">${rotulos[i]}</text>`);
    });

    return `<svg viewBox="0 0 ${largura} ${altura}" class="grafico">${partes.join("\\n")}</svg>`;
  }

  function statTile(label, valor, pequeno) {
    const classe = pequeno ? "tile-valor tile-valor-pequeno" : "tile-valor";
    return `<div class="tile"><div class="tile-label">${escapar(label)}</div><div class="${classe}">${escapar(valor)}</div></div>`;
  }

  function tileComDelta(label, valor, deltaTexto) {
    return `<div class="tile"><div class="tile-label">${escapar(label)}</div><div class="tile-valor">${escapar(valor)}</div><div class="delta">${escapar(deltaTexto)}</div></div>`;
  }

  let dadosMinOrdinal = Infinity;
  let dadosMaxOrdinal = -Infinity;
  for (const p of PLAYS) {
    if (p[0] < dadosMinOrdinal) dadosMinOrdinal = p[0];
    if (p[0] > dadosMaxOrdinal) dadosMaxOrdinal = p[0];
  }

  function renderizar(inicio, fim) {
    const plays = filtrarPlays(inicio, fim);
    const stats = calcularStats(plays);
    const streaks = calcularStreaks(plays);
    const granularidade = plays.length ? escolherGranularidade(inicio, fim) : "dia";
    const buckets = plays.length ? gerarBuckets(inicio, fim, granularidade) : [];

    document.getElementById("tiles").innerHTML = [
      statTile("Reproduções registradas", compacto(stats.total)),
      statTile("Tempo ouvido", stats.total ? formatarDuracaoStat(stats.tempoMs) : "sem dados"),
      statTile("Sequência atual", stats.total ? `${streaks.atual} dia(s)` : "sem dados"),
      statTile("Maior sequência", stats.total ? `${streaks.recorde} dia(s)` : "sem dados"),
      statTile("Artistas únicos", compacto(stats.artistasUnicos)),
      statTile("Músicas únicas", compacto(stats.musicasUnicas)),
      statTile("Período coberto", stats.total ? formatarPlayCompleto(stats.primeiro) + " — " + formatarPlayCompleto(stats.ultimo) : "sem dados", true),
    ].join("");

    const comparacao = calcularComparacao(inicio, fim);
    if (!plays.length || !comparacao) {
      document.getElementById("comparacao").innerHTML = "<p class='vazio'>Sem período anterior suficiente pra comparar.</p>";
    } else {
      const statsAnterior = calcularStats(comparacao.plays);
      const artistasAtual = contarPorArtista(plays);
      const artistasAnterior = contarPorArtista(comparacao.plays);
      const topAtual = [...artistasAtual.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);

      const tiles = [
        tileComDelta("Reproduções", compacto(stats.total), formatarDelta(stats.total, statsAnterior.total)),
        tileComDelta("Tempo ouvido", formatarDuracaoStat(stats.tempoMs), formatarDelta(stats.tempoMs, statsAnterior.tempoMs)),
      ].join("");

      const linhas = topAtual
        .map(([nome, vezes]) => {
          const anterior = artistasAnterior.get(nome) || 0;
          return `<tr><td>${escapar(nome)}</td><td>${vezes}</td><td>${anterior}</td></tr>`;
        })
        .join("");

      document.getElementById("comparacao").innerHTML = `
        <div class="comparacao-tiles">${tiles}</div>
        <table>
          <thead><tr><th>Artista (top 5 no período)</th><th>Este período</th><th>Anterior</th></tr></thead>
          <tbody>${linhas}</tbody>
        </table>`;
    }

    const { matriz, matrizMs, maximo } = calcularHeatmap(plays);
    document.getElementById("heatmap").innerHTML = plays.length ? svgHeatmap(matriz, matrizMs, maximo) : "<p class='vazio'>Sem dados no período.</p>";

    const porDiaSemana = calcularPorDiaSemana(plays);
    document.getElementById("grafico-dia-semana").innerHTML = plays.length
      ? svgBarras(porDiaSemana.contagem, porDiaSemana.duracao, DIAS_SEMANA)
      : "<p class='vazio'>Sem dados no período.</p>";

    document.getElementById("titulo-serie").textContent = "Reproduções por " + (FORMATO_ROTULO[granularidade] || "dia");
    const serieTotal = plays.length ? calcularSeriePorBucket(plays, buckets, granularidade) : [];
    document.getElementById("grafico-total").innerHTML = serieTotal.length
      ? svgLinha([{ nome: "Reproduções", pontos: serieTotal }], { granularidade })
      : "<p class='vazio'>Sem dados no período.</p>";

    const topArtistas = plays.length ? calcularTopArtistas(plays, buckets, granularidade, 4) : [];
    document.getElementById("subcharts-artistas").innerHTML = topArtistas
      .map(
        (s) => `
      <div class="subchart">
        <h3>${escapar(s.nome)} <span class="muted">(${s.total}x)</span></h3>
        ${svgLinha([s], { altura: 140, granularidade })}
      </div>`
      )
      .join("");

    const musicas = topMusicas(plays, 15);
    document.getElementById("tabela-musicas").innerHTML = musicas
      .map(([nome, art, vezes]) => `<tr><td>${escapar(nome)}</td><td>${escapar(art)}</td><td>${vezes}</td></tr>`)
      .join("");

    const albuns = topAlbuns(plays, 15);
    document.getElementById("tabela-albuns").innerHTML = albuns
      .map(([nome, art, vezes]) => `<tr><td>${escapar(nome)}</td><td>${escapar(art)}</td><td>${vezes}</td></tr>`)
      .join("");
  }

  const botoesPreset = document.querySelectorAll("[data-preset]");
  const inputInicio = document.getElementById("data-inicio");
  const inputFim = document.getElementById("data-fim");
  const previewInicio = document.getElementById("preview-inicio");
  const previewFim = document.getElementById("preview-fim");

  function formatarInputDateBr(valor) {
    if (!valor) return "";
    const [ano, mes, dia] = valor.split("-");
    return dia + "/" + mes + "/" + ano;
  }

  function atualizarPreviews() {
    previewInicio.textContent = formatarInputDateBr(inputInicio.value);
    previewFim.textContent = formatarInputDateBr(inputFim.value);
  }

  inputInicio.addEventListener("change", atualizarPreviews);
  inputFim.addEventListener("change", atualizarPreviews);

  function marcarAtivo(botao) {
    botoesPreset.forEach((b) => b.classList.remove("ativo"));
    if (botao) botao.classList.add("ativo");
  }

  function hojeOrdinal() {
    const partes = new Intl.DateTimeFormat("en-CA", { timeZone: "__TIMEZONE_KEY__" }).format(new Date());
    const [ano, mes, dia] = partes.split("-").map(Number);
    return dataParaOrdinal(ano, mes - 1, dia);
  }

  function ordinalParaInputDate(ordinal) {
    const d = ordinalParaData(ordinal);
    return d.getUTCFullYear() + "-" + String(d.getUTCMonth() + 1).padStart(2, "0") + "-" + String(d.getUTCDate()).padStart(2, "0");
  }

  botoesPreset.forEach((botao) => {
    botao.addEventListener("click", () => {
      const preset = botao.dataset.preset;
      const hoje = Math.min(hojeOrdinal(), dadosMaxOrdinal);
      let inicio;
      let fim = hoje;
      if (preset === "tudo") {
        inicio = dadosMinOrdinal;
        fim = dadosMaxOrdinal;
      } else if (preset === "ano") {
        inicio = dataParaOrdinal(ordinalParaData(hoje).getUTCFullYear(), 0, 1);
      } else {
        inicio = hoje - Number(preset) + 1;
      }
      inicio = Math.max(inicio, dadosMinOrdinal);
      inputInicio.value = ordinalParaInputDate(inicio);
      inputFim.value = ordinalParaInputDate(fim);
      atualizarPreviews();
      marcarAtivo(botao);
      renderizar(inicio, fim);
    });
  });

  document.getElementById("aplicar-custom").addEventListener("click", () => {
    if (!inputInicio.value || !inputFim.value) return;
    const [ai, am, ad] = inputInicio.value.split("-").map(Number);
    const [bi, bm, bd] = inputFim.value.split("-").map(Number);
    marcarAtivo(null);
    renderizar(dataParaOrdinal(ai, am - 1, ad), dataParaOrdinal(bi, bm - 1, bd));
  });

  inputInicio.value = ordinalParaInputDate(dadosMinOrdinal);
  inputFim.value = ordinalParaInputDate(dadosMaxOrdinal);
  atualizarPreviews();
  renderizar(dadosMinOrdinal, dadosMaxOrdinal);
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    linhas = carregar_linhas()
    tracks, plays = preparar_dados(linhas)

    agora = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M")
    html = (
        HTML_TEMPLATE.replace("__TRACKS_JSON__", json_seguro(tracks))
        .replace("__PLAYS_JSON__", json_seguro(plays))
        .replace("__GERADO_EM__", agora)
        .replace("__TIMEZONE_KEY__", TIMEZONE.key)
    )

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado em {OUT_PATH} ({len(linhas)} reproduções, {len(tracks)} músicas únicas)")
