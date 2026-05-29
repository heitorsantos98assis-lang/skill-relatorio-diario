#!/usr/bin/env python3
"""
Relatorio semanal — consolida 7 dias + comparativo + cohort + tendencia.

Mostra:
  • Curva diaria (recebidas, respondidas, TPR) em sparkline
  • Top 10 clientes por interacao
  • Cohort: cliente novo vs recorrente
  • Comparativo vs semana anterior
  • Keywords de negocio (interesse, objecao, fechamento, reclamacao)
  • Hora pico e dia pico de demanda
  • Projecao: e se respondesse 100% em <5min?

Uso:
    python relatorio_semanal.py conversas.csv
    python relatorio_semanal.py conversas.csv --inicio 2026-05-18 --fim 2026-05-24

Criado pela Bravy.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median


DIAS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]


# Keywords agrupadas por categoria de NEGOCIO (nao operacional como na skill 08)
KEYWORDS_NEGOCIO = {
    "interesse": ["quero", "preciso", "como faço", "como funciona", "tem como", "consigo",
                  "me interessa", "vou querer", "fechar", "comprar"],
    "preco": ["preço", "preco", "quanto", "valor", "custa", "desconto", "barato", "caro",
              "promocao", "promoção", "parcelar", "boleto", "pix"],
    "objecao": ["mas eu", "porem", "porém", "todavia", "nao sei", "não sei", "vou pensar",
                "depois eu", "quem sabe", "talvez", "concorrente", "no x ta"],
    "fechamento": ["pode passar", "manda o link", "como pago", "qual chave pix",
                   "vou pagar", "ja paguei", "transferi", "boleto pago"],
    "reclamacao": ["nao chegou", "não chegou", "atrasado", "horrivel", "péssimo", "decepcionad",
                   "reclamar", "lixo", "merda", "vou processar"],
    "cancelamento": ["cancelar", "desistir", "estornar", "reembolso", "quero meu dinheiro"],
}


# ---------------------------------------------------------------------------
# Modelo + IO
# ---------------------------------------------------------------------------

@dataclass
class Msg:
    dt: datetime
    cliente: str
    direcao: str
    texto: str
    grupo: str = ""


def carregar(caminho: Path) -> list[Msg]:
    if not caminho.exists():
        sys.exit(f"erro: nao encontrado — {caminho}")
    msgs: list[Msg] = []
    with caminho.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                dt = datetime.strptime(row["data_hora"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, KeyError):
                continue
            d = (row.get("direcao") or "").strip().lower()
            if d not in {"recebida", "enviada"}:
                continue
            msgs.append(
                Msg(
                    dt=dt,
                    cliente=(row.get("cliente") or "").strip(),
                    direcao=d,
                    texto=row.get("mensagem") or "",
                    grupo=(row.get("grupo") or "").strip(),
                )
            )
    msgs.sort(key=lambda m: m.dt)
    return msgs


# ---------------------------------------------------------------------------
# Calculos
# ---------------------------------------------------------------------------

def kpi_periodo(msgs: list[Msg]) -> dict:
    recebidas = sum(1 for m in msgs if m.direcao == "recebida")
    aguardando: dict[str, datetime] = {}
    tprs: list[float] = []
    for m in msgs:
        if m.direcao == "recebida":
            aguardando.setdefault(m.cliente, m.dt)
        else:
            p = aguardando.pop(m.cliente, None)
            if p is not None:
                tprs.append((m.dt - p).total_seconds())
    return {
        "recebidas": recebidas,
        "respondidas": len(tprs),
        "tpr_mediana_s": median(tprs) if tprs else None,
        "taxa_resposta": round(len(tprs) / recebidas * 100, 1) if recebidas else 0,
        "em_aberto": len(aguardando),
    }


def kpis_diarios(msgs: list[Msg]) -> dict[date, dict]:
    por_dia: dict[date, list[Msg]] = defaultdict(list)
    for m in msgs:
        por_dia[m.dt.date()].append(m)
    return {d: kpi_periodo(ms) for d, ms in por_dia.items()}


def top_clientes(msgs: list[Msg], n: int = 10) -> list[dict]:
    contagem: dict[str, int] = defaultdict(int)
    for m in msgs:
        if m.direcao == "recebida":
            contagem[m.cliente] += 1
    return sorted(
        [{"cliente": c, "mensagens": q} for c, q in contagem.items()],
        key=lambda x: -x["mensagens"],
    )[:n]


def cohort_novo_vs_recorrente(msgs: list[Msg]) -> dict:
    """Cliente NOVO = primeira aparicao na janela. RECORRENTE = ja apareceu antes."""
    if not msgs:
        return {"novos": 0, "recorrentes": 0, "novos_lista": [], "ratio": 0}
    primeiro_evento: dict[str, datetime] = {}
    for m in msgs:
        primeiro_evento.setdefault(m.cliente, m.dt)

    inicio = msgs[0].dt.date()
    novos = [c for c, dt in primeiro_evento.items() if dt.date() == inicio or dt.date() == msgs[-1].dt.date()]
    # melhor: novos = quem nao aparece nos primeiros 24h
    janela_corte = msgs[0].dt + timedelta(hours=24)
    novos = [c for c, dt in primeiro_evento.items() if dt >= janela_corte]
    recorrentes = [c for c in primeiro_evento if c not in novos]
    return {
        "novos": len(novos),
        "recorrentes": len(recorrentes),
        "novos_lista": novos[:10],
        "ratio": round(len(novos) / max(len(primeiro_evento), 1) * 100, 1),
    }


def detectar_negocio(msgs: list[Msg]) -> dict[str, list[dict]]:
    """Agrupa mensagens recebidas por categoria de negocio."""
    out: dict[str, list[dict]] = defaultdict(list)
    for m in msgs:
        if m.direcao != "recebida":
            continue
        t = m.texto.lower()
        for cat, termos in KEYWORDS_NEGOCIO.items():
            if any(termo in t for termo in termos):
                out[cat].append({
                    "cliente": m.cliente,
                    "quando": m.dt,
                    "trecho": m.texto[:100],
                })
    return out


def hora_pico(msgs: list[Msg]) -> tuple[int, int]:
    """Hora do dia com mais mensagens recebidas."""
    contagem = defaultdict(int)
    for m in msgs:
        if m.direcao == "recebida":
            contagem[m.dt.hour] += 1
    if not contagem:
        return -1, 0
    h, q = max(contagem.items(), key=lambda x: x[1])
    return h, q


def projecao_resposta_rapida(msgs: list[Msg], target_s: int = 300) -> dict:
    """E se TODA primeira resposta fosse em <5min?"""
    aguardando: dict[str, datetime] = {}
    pares: list[tuple[float, bool]] = []  # (tpr_atual, era_<5min)
    for m in msgs:
        if m.direcao == "recebida":
            aguardando.setdefault(m.cliente, m.dt)
        else:
            p = aguardando.pop(m.cliente, None)
            if p is not None:
                tpr = (m.dt - p).total_seconds()
                pares.append((tpr, tpr <= target_s))
    if not pares:
        return {"ja_em_5min_pct": 0, "delta_se_100pct": 0}
    em_5min = sum(1 for _, ok in pares if ok)
    return {
        "ja_em_5min_pct": round(em_5min / len(pares) * 100, 1),
        "potencial_pct": round((len(pares) - em_5min) / len(pares) * 100, 1),
    }


# ---------------------------------------------------------------------------
# Formatacao
# ---------------------------------------------------------------------------

def fmt_seg(s: float | None) -> str:
    if s is None:
        return "—"
    s = int(s); h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    if h:
        return f"{h}h{m:02d}"
    if m:
        return f"{m}min"
    return f"{sec}s"


def sparkline(valores: list[float]) -> str:
    blocos = "▁▂▃▄▅▆▇█"
    nums = [v for v in valores if v is not None]
    if not nums:
        return "—" * len(valores)
    vmin, vmax = min(nums), max(nums)
    if vmax == vmin:
        return blocos[3] * len(valores)
    out = []
    for v in valores:
        if v is None:
            out.append(" ")
            continue
        idx = int((v - vmin) / (vmax - vmin) * (len(blocos) - 1))
        out.append(blocos[idx])
    return "".join(out)


def setinha(delta_pct: float, baixo_eh_bom: bool = False) -> str:
    if abs(delta_pct) < 1:
        return "▬"
    bom = delta_pct < 0 if baixo_eh_bom else delta_pct > 0
    return "▲" if bom else "▼"


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def renderizar(
    inicio: date, fim: date,
    kpis: dict, kpis_d: dict[date, dict],
    top: list[dict],
    cohort: dict,
    negocio: dict[str, list[dict]],
    pico_hora: int, pico_qtd: int,
    proj: dict,
    semana_passada_kpis: dict | None,
) -> str:
    L: list[str] = []
    L.append("═══════════════════════════════════════════════════════════════")
    L.append(f"RELATORIO SEMANAL — {inicio.strftime('%d/%m')} a {fim.strftime('%d/%m/%Y')}")
    L.append("═══════════════════════════════════════════════════════════════")
    L.append("")

    # ---- KPIs ----
    L.append("KPIs DA SEMANA")
    L.append(f"  Mensagens recebidas:     {kpis['recebidas']}")
    L.append(f"  Mensagens respondidas:   {kpis['respondidas']}  ({kpis['taxa_resposta']:.0f}%)")
    L.append(f"  Tempo medio de resposta: {fmt_seg(kpis['tpr_mediana_s'])}")
    L.append(f"  Conversas em aberto:     {kpis['em_aberto']}")
    L.append("")

    # ---- CURVA DIARIA ----
    dias_ord = sorted(kpis_d.keys())
    if dias_ord:
        L.append("CURVA DIARIA")
        recebidas_s = [kpis_d[d]["recebidas"] for d in dias_ord]
        respond_s = [kpis_d[d]["respondidas"] for d in dias_ord]
        tpr_s = [kpis_d[d]["tpr_mediana_s"] for d in dias_ord]
        L.append(f"  Recebidas    {sparkline(recebidas_s)}  (min {min(recebidas_s)} / max {max(recebidas_s)})")
        L.append(f"  Respondidas  {sparkline(respond_s)}  (min {min(respond_s)} / max {max(respond_s)})")
        L.append(f"  TPR          {sparkline(tpr_s)}  (max {fmt_seg(max([t for t in tpr_s if t is not None], default=None))})")
        L.append(f"               {''.join(DIAS_PT[d.weekday()][0] for d in dias_ord)}")
        L.append("")

    # ---- COMPARATIVO ----
    if semana_passada_kpis:
        a, b = kpis, semana_passada_kpis
        L.append("COMPARATIVO vs SEMANA ANTERIOR")

        def linha(lbl, va, vb, baixo_eh_bom=False, fmt=str):
            if va is None or vb is None or (isinstance(vb, (int, float)) and vb == 0):
                return None
            pct = (va - vb) / vb * 100 if vb else 0
            return f"  {lbl:<20} {fmt(va):>10}  ←  {fmt(vb):<10}  ({pct:+.0f}%)  {setinha(pct, baixo_eh_bom)}"
        for l in [
            linha("Recebidas", a["recebidas"], b["recebidas"]),
            linha("Respondidas", a["respondidas"], b["respondidas"]),
            linha("Taxa resposta %", a["taxa_resposta"], b["taxa_resposta"]),
            linha("TPR mediano", a["tpr_mediana_s"], b["tpr_mediana_s"], baixo_eh_bom=True, fmt=fmt_seg),
        ]:
            if l:
                L.append(l)
        L.append("")

    # ---- TOP CLIENTES ----
    if top:
        L.append("TOP 10 CLIENTES POR INTERACAO")
        nome_w = max(len(c["cliente"]) for c in top) + 2
        for i, c in enumerate(top, 1):
            L.append(f"  {i:>2}. {c['cliente'].ljust(nome_w)} {c['mensagens']:>3} msgs")
        L.append("")

    # ---- COHORT ----
    L.append("COHORT: NOVOS vs RECORRENTES")
    L.append(f"  Clientes que apareceram a primeira vez:  {cohort['novos']}  ({cohort['ratio']}%)")
    L.append(f"  Clientes ja conhecidos:                  {cohort['recorrentes']}")
    if cohort["novos_lista"]:
        L.append(f"  Exemplos de novos: {', '.join(cohort['novos_lista'][:5])}{' ...' if len(cohort['novos_lista']) > 5 else ''}")
    L.append("")

    # ---- KEYWORDS DE NEGOCIO ----
    L.append("KEYWORDS DE NEGOCIO DETECTADAS")
    if not negocio:
        L.append("  (nenhuma keyword reconhecida)")
    else:
        ordem = ["interesse", "preco", "objecao", "fechamento", "reclamacao", "cancelamento"]
        for cat in ordem:
            hits = negocio.get(cat, [])
            if not hits:
                continue
            L.append(f"  {cat.upper():<14} {len(hits):>3}  exemplo: '{hits[0]['trecho'][:60]}...' ({hits[0]['cliente']})")
    L.append("")

    # ---- PICO ----
    if pico_hora >= 0:
        L.append(f"PICO DE DEMANDA")
        L.append(f"  Hora mais cheia: {pico_hora:02d}h  ({pico_qtd} mensagens na semana)")
        if pico_hora < 9 or pico_hora >= 18:
            L.append(f"  ⚠ Fora do horario comercial — considere plantao ou mensagem automatica")
        L.append("")

    # ---- PROJECAO ----
    L.append("PROJECAO — Se TODA primeira resposta fosse em <5min")
    L.append(f"  Hoje voce ja responde em <5min em {proj['ja_em_5min_pct']}% das conversas")
    L.append(f"  Potencial: melhorar os outros {proj['potencial_pct']}%")
    L.append("  (TPR <5min e correlacionado com taxa de fechamento ~3x maior em B2C tipico)")
    L.append("")

    L.append("═══════════════════════════════════════════════════════════════")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Relatorio semanal — cohort, tendencia, keywords")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--inicio", type=str, default=None)
    parser.add_argument("--fim", type=str, default=None)
    args = parser.parse_args()

    msgs = carregar(args.csv)
    if not msgs:
        sys.exit("erro: csv vazio")

    fim = datetime.strptime(args.fim, "%Y-%m-%d").date() if args.fim else msgs[-1].dt.date()
    inicio = datetime.strptime(args.inicio, "%Y-%m-%d").date() if args.inicio else fim - timedelta(days=6)

    janela = [m for m in msgs if inicio <= m.dt.date() <= fim]
    janela_passada = [
        m for m in msgs
        if (inicio - timedelta(days=7)) <= m.dt.date() < inicio
    ]
    if not janela:
        sys.exit("erro: sem mensagens no periodo")

    kpis = kpi_periodo(janela)
    kpis_d = kpis_diarios(janela)
    top = top_clientes(janela, n=10)
    cohort = cohort_novo_vs_recorrente(janela)
    negocio = detectar_negocio(janela)
    h, q = hora_pico(janela)
    proj = projecao_resposta_rapida(janela)
    sp_kpis = kpi_periodo(janela_passada) if janela_passada else None

    print(renderizar(inicio, fim, kpis, kpis_d, top, cohort, negocio, h, q, proj, sp_kpis))


if __name__ == "__main__":
    main()
