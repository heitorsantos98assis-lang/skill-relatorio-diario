#!/usr/bin/env python3
"""
Relatorio diario do WhatsApp — resumo da operacao do dia.

Uso:
    python relatorio_diario.py conversas.csv
    python relatorio_diario.py conversas.csv --data 2026-05-24
    python relatorio_diario.py conversas.csv --vip vips.txt

CSV de entrada (cabecalho minimo):
    data_hora,atendente,cliente,direcao,mensagem
    (coluna `grupo` opcional, habilita a secao "Volume por grupo")

Criado pela HL.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------

@dataclass
class Mensagem:
    data_hora: datetime
    atendente: str
    cliente: str
    direcao: str
    mensagem: str
    grupo: str = ""


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def carregar_csv(caminho: Path) -> list[Mensagem]:
    if not caminho.exists():
        sys.exit(f"erro: arquivo nao encontrado — {caminho}")

    mensagens: list[Mensagem] = []
    with caminho.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        obrigatorias = {"data_hora", "cliente", "direcao", "mensagem"}
        faltando = obrigatorias - set(reader.fieldnames or [])
        if faltando:
            sys.exit(f"erro: colunas faltando no CSV: {sorted(faltando)}")

        for n, row in enumerate(reader, start=2):
            try:
                dt = _parse_data(row["data_hora"])
            except ValueError as e:
                print(f"aviso: linha {n} ignorada — {e}", file=sys.stderr)
                continue
            direcao = (row["direcao"] or "").strip().lower()
            if direcao not in {"recebida", "enviada"}:
                continue
            mensagens.append(
                Mensagem(
                    data_hora=dt,
                    atendente=(row.get("atendente") or "").strip(),
                    cliente=(row["cliente"] or "").strip(),
                    direcao=direcao,
                    mensagem=row["mensagem"] or "",
                    grupo=(row.get("grupo") or "").strip(),
                )
            )
    if not mensagens:
        sys.exit("erro: nenhuma mensagem valida no CSV")
    mensagens.sort(key=lambda m: m.data_hora)
    return mensagens


def _parse_data(valor: str) -> datetime:
    formatos = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    )
    for fmt in formatos:
        try:
            return datetime.strptime(valor.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"data invalida: '{valor}'")


def carregar_vips(caminho: Path | None) -> set[str]:
    if not caminho:
        return set()
    if not caminho.exists():
        print(f"aviso: VIPs nao encontrado — {caminho}", file=sys.stderr)
        return set()
    return {linha.strip() for linha in caminho.read_text(encoding="utf-8").splitlines() if linha.strip()}


# ---------------------------------------------------------------------------
# Calculo
# ---------------------------------------------------------------------------

@dataclass
class ResumoDia:
    dia: date
    recebidas: int
    respondidas: int
    em_aberto: int
    em_aberto_2h: list[tuple[str, datetime]] = field(default_factory=list)
    tpr_mediana_s: float | None = None
    vips: list[dict] = field(default_factory=list)
    volume_grupo: dict[str, dict[str, int]] = field(default_factory=dict)
    primeira_msg_dia: datetime | None = None
    ultima_msg_dia: datetime | None = None

    @property
    def taxa_resposta(self) -> float:
        if not self.recebidas:
            return 0.0
        return round(self.respondidas / self.recebidas * 100, 1)


def filtrar_dia(mensagens: list[Mensagem], dia: date) -> list[Mensagem]:
    return [m for m in mensagens if m.data_hora.date() == dia]


def calcular_resumo(mensagens_dia: list[Mensagem], vips: set[str], corte: datetime) -> ResumoDia:
    if not mensagens_dia:
        sys.exit("erro: nenhuma mensagem no dia solicitado")

    dia = mensagens_dia[0].data_hora.date()

    # contadores
    recebidas = sum(1 for m in mensagens_dia if m.direcao == "recebida")

    # TPR por par-cliente (primeira recebida do dia -> primeira enviada subsequente)
    aguardando: dict[str, datetime] = {}
    tprs: list[float] = []
    respondidos: set[str] = set()

    for m in mensagens_dia:
        if m.direcao == "recebida":
            aguardando.setdefault(m.cliente, m.data_hora)
            continue
        primeira = aguardando.pop(m.cliente, None)
        if primeira is not None:
            delta = (m.data_hora - primeira).total_seconds()
            if delta >= 0:
                tprs.append(delta)
                respondidos.add(m.cliente)

    # respondidas = total de respostas que casaram com uma recebida do dia
    respondidas = len(tprs)
    em_aberto_clientes = list(aguardando.items())
    em_aberto = len(em_aberto_clientes)
    em_aberto_2h = [(c, dt) for c, dt in em_aberto_clientes if (corte - dt) >= timedelta(hours=2)]
    em_aberto_2h.sort(key=lambda x: x[1])

    # VIPs do dia
    vip_status: list[dict] = []
    for c in vips:
        chegou = next((m for m in mensagens_dia if m.cliente == c and m.direcao == "recebida"), None)
        if not chegou:
            continue
        # primeira resposta apos
        resp = next(
            (m for m in mensagens_dia if m.cliente == c and m.direcao == "enviada" and m.data_hora >= chegou.data_hora),
            None,
        )
        vip_status.append(
            {
                "cliente": c,
                "chegou": chegou.data_hora,
                "respondido_em_s": (resp.data_hora - chegou.data_hora).total_seconds() if resp else None,
                "ainda_aberto": c in aguardando,
            }
        )
    vip_status.sort(key=lambda v: v["chegou"])

    # volume por grupo
    volume: dict[str, dict[str, int]] = defaultdict(lambda: {"recebidas": 0, "respondidas": 0})
    if any(m.grupo for m in mensagens_dia):
        for m in mensagens_dia:
            grupo = m.grupo or "(sem grupo)"
            if m.direcao == "recebida":
                volume[grupo]["recebidas"] += 1
            else:
                volume[grupo]["respondidas"] += 1

    return ResumoDia(
        dia=dia,
        recebidas=recebidas,
        respondidas=respondidas,
        em_aberto=em_aberto,
        em_aberto_2h=em_aberto_2h,
        tpr_mediana_s=median(tprs) if tprs else None,
        vips=vip_status,
        volume_grupo=dict(volume),
        primeira_msg_dia=mensagens_dia[0].data_hora,
        ultima_msg_dia=mensagens_dia[-1].data_hora,
    )


# ---------------------------------------------------------------------------
# Formatacao
# ---------------------------------------------------------------------------

def fmt_seg(seg: float | None) -> str:
    if seg is None:
        return "—"
    seg = int(seg)
    h, r = divmod(seg, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h{m:02d}"
    if m:
        return f"{m}min{s:02d}s" if s and m < 5 else f"{m}min"
    return f"{s}s"


def setinha(delta_pct: float, melhor_quando: str) -> str:
    """Devolve seta com semantica de melhora/piora."""
    if abs(delta_pct) < 1:
        return "▬"
    if (melhor_quando == "alto" and delta_pct > 0) or (melhor_quando == "baixo" and delta_pct < 0):
        return "▲"
    return "▼"


def montar_relatorio(resumo: ResumoDia, anterior: ResumoDia | None) -> str:
    L: list[str] = []
    L.append("═══════════════════════════════════════════")
    L.append(f"RESUMO DO DIA — {resumo.dia.strftime('%d/%m/%Y')}")
    L.append("═══════════════════════════════════════════")
    L.append("")

    # ---- VISAO GERAL ----
    L.append("VISAO GERAL")
    L.append(f"- Mensagens recebidas:   {resumo.recebidas:>4}")
    L.append(
        f"- Mensagens respondidas: {resumo.respondidas:>4}  ({resumo.taxa_resposta:.0f}%)"
    )
    L.append(f"- Tempo medio de resposta: {fmt_seg(resumo.tpr_mediana_s)}")
    em_aberto_pct = 0 if not resumo.recebidas else round(resumo.em_aberto / resumo.recebidas * 100)
    L.append(f"- Conversas em aberto:    {resumo.em_aberto:>3}  ({em_aberto_pct}%)")
    L.append("")

    # ---- EVOLUCAO ----
    if anterior:
        L.append("EVOLUCAO vs DIA ANTERIOR")
        for label, a, b, melhor in [
            ("Recebidas  ", anterior.recebidas, resumo.recebidas, "alto"),
            ("Respondidas", anterior.respondidas, resumo.respondidas, "alto"),
            ("TPR        ", anterior.tpr_mediana_s, resumo.tpr_mediana_s, "baixo"),
        ]:
            if a is None or b is None or a == 0:
                continue
            pct = (b - a) / a * 100
            L.append(f"- {label}: {pct:+5.0f}%  {setinha(pct, melhor)}")
        L.append("")

    # ---- EM ABERTO ----
    L.append("CONVERSAS SEM RESPOSTA  (atencao)")
    if resumo.em_aberto == 0:
        L.append("  ✅ todas as conversas do dia foram respondidas")
    else:
        L.append(f"- {resumo.em_aberto} conversas iniciadas e nao respondidas")
        if resumo.em_aberto_2h:
            L.append(f"- {len(resumo.em_aberto_2h)} conversas com cliente esperando ha > 2h:")
            for cliente, dt in resumo.em_aberto_2h[:5]:
                L.append(f"   ▸ {cliente.ljust(20)} — ultima mensagem {dt.strftime('%H:%M')}")
            if len(resumo.em_aberto_2h) > 5:
                L.append(f"   (+{len(resumo.em_aberto_2h) - 5})")
    L.append("")

    # ---- VIPs ----
    L.append("CLIENTES VIP QUE MANDARAM HOJE")
    if not resumo.vips:
        L.append("  (nenhum VIP entrou em contato — ou lista de VIPs nao fornecida)")
    else:
        max_nome = max(len(v["cliente"]) for v in resumo.vips)
        for v in resumo.vips:
            hora = v["chegou"].strftime("%H:%M")
            if v["ainda_aberto"]:
                L.append(
                    f"🌟 {v['cliente'].ljust(max_nome)} — chegou {hora} — AGUARDANDO         ⚠️"
                )
            elif v["respondido_em_s"] is not None:
                L.append(
                    f"🌟 {v['cliente'].ljust(max_nome)} — chegou {hora} — respondido em {fmt_seg(v['respondido_em_s']):>6}  ✅"
                )
            else:
                L.append(
                    f"🌟 {v['cliente'].ljust(max_nome)} — chegou {hora} — sem resposta clara"
                )
    L.append("")

    # ---- VOLUME POR GRUPO ----
    if resumo.volume_grupo:
        L.append("VOLUME POR GRUPO")
        L.append("| Grupo               | Recebidas | Respondidas | %    |")
        L.append("|---------------------|-----------|-------------|------|")
        for grupo, v in sorted(resumo.volume_grupo.items(), key=lambda x: -x[1]["recebidas"]):
            # taxa de resposta capada em 100% (uma resposta pode ser pra conversa iniciada em dia anterior)
            pct = 0 if not v["recebidas"] else min(100, round(v["respondidas"] / v["recebidas"] * 100))
            L.append(
                f"| {grupo[:19].ljust(19)} | {v['recebidas']:>9} | {v['respondidas']:>11} | {pct:>3}% |"
            )
        L.append("")

    # ---- DESTAQUES ----
    L.append("DESTAQUES DO DIA")
    destaques = _destaques(resumo, anterior)
    if not destaques:
        L.append("- Dia dentro do padrao — sem destaques notaveis")
    else:
        for d in destaques:
            L.append(f"- {d}")
    L.append("")

    # ---- PROXIMOS PASSOS ----
    L.append("PROXIMOS PASSOS")
    passos = _proximos(resumo)
    for i, p in enumerate(passos, 1):
        L.append(f"{i}. {p}")
    L.append("═══════════════════════════════════════════")
    return "\n".join(L)


def _destaques(resumo: ResumoDia, anterior: ResumoDia | None) -> list[str]:
    dest: list[str] = []
    if anterior and anterior.tpr_mediana_s and resumo.tpr_mediana_s:
        delta = (resumo.tpr_mediana_s - anterior.tpr_mediana_s) / anterior.tpr_mediana_s * 100
        if delta < -10:
            dest.append(f"TPR caiu {abs(delta):.0f}% em relacao a ontem — equipe respondeu mais rapido")
        elif delta > 20:
            dest.append(f"TPR subiu {delta:.0f}% — investigar lentidao")
    if resumo.taxa_resposta >= 90:
        dest.append(f"Taxa de resposta alta ({resumo.taxa_resposta:.0f}%) — operacao saudavel")
    elif resumo.taxa_resposta < 70 and resumo.recebidas > 10:
        dest.append(f"Taxa de resposta baixa ({resumo.taxa_resposta:.0f}%) — corrigir capacidade do time")
    if resumo.volume_grupo:
        melhor = max(
            resumo.volume_grupo.items(),
            key=lambda x: min(1, x[1]["respondidas"] / x[1]["recebidas"]) if x[1]["recebidas"] else 0,
        )
        if melhor[1]["recebidas"] >= 5:
            tx = min(100, round(melhor[1]["respondidas"] / melhor[1]["recebidas"] * 100))
            dest.append(f"Melhor grupo do dia: {melhor[0]} ({tx}% de resposta)")
    vip_aberto = sum(1 for v in resumo.vips if v["ainda_aberto"])
    if resumo.vips:
        dest.append(
            f"{len(resumo.vips)} VIPs entraram em contato — {vip_aberto} ainda nao respondido(s)"
        )
    return dest


def _proximos(resumo: ResumoDia) -> list[str]:
    p: list[str] = []
    vip_aberto = [v for v in resumo.vips if v["ainda_aberto"]]
    if vip_aberto:
        nomes = ", ".join(v["cliente"] for v in vip_aberto[:3])
        p.append(f"Responder VIP(s) em espera: {nomes}")
    if resumo.em_aberto_2h:
        p.append(f"Limpar as {len(resumo.em_aberto_2h)} conversas com >2h de espera")
    if resumo.em_aberto > len(resumo.em_aberto_2h):
        restante = resumo.em_aberto - len(resumo.em_aberto_2h)
        p.append(f"Verificar {restante} nao-respondidos antes do horario de pico")
    if resumo.taxa_resposta < 70 and resumo.recebidas > 10:
        p.append("Revisar escala / capacidade do time — taxa de resposta baixa")
    if not p:
        p.append("Manter operacao — dia limpo")
    return p[:5]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Relatorio diario do WhatsApp")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--data", type=str, default=None, help="YYYY-MM-DD (default: dia da ultima mensagem)")
    parser.add_argument("--vip", type=Path, default=None)
    args = parser.parse_args()

    todas = carregar_csv(args.csv)
    vips = carregar_vips(args.vip)

    if args.data:
        try:
            dia_alvo = datetime.strptime(args.data, "%Y-%m-%d").date()
        except ValueError:
            sys.exit("erro: --data invalida (use YYYY-MM-DD)")
    else:
        dia_alvo = todas[-1].data_hora.date()

    msgs_dia = filtrar_dia(todas, dia_alvo)
    if not msgs_dia:
        sys.exit(f"erro: nenhuma mensagem no dia {dia_alvo}")

    corte = msgs_dia[-1].data_hora.replace(hour=23, minute=59, second=59)
    resumo = calcular_resumo(msgs_dia, vips, corte)

    # dia anterior (se houver)
    anterior_data = dia_alvo - timedelta(days=1)
    msgs_anterior = filtrar_dia(todas, anterior_data)
    anterior = None
    if msgs_anterior:
        corte_a = msgs_anterior[-1].data_hora.replace(hour=23, minute=59, second=59)
        anterior = calcular_resumo(msgs_anterior, vips, corte_a)

    print(montar_relatorio(resumo, anterior))


if __name__ == "__main__":
    main()
