#!/usr/bin/env python3
"""
Mesmo conversor da skill monitoramento-equipe (Bonus 8).
Replicado aqui pra essa skill ser autossuficiente.

Veja documentacao completa em:
  08-skill-monitoramento-equipe/conversores/converter_whatsapp_export.py

Uso:
    python converter_whatsapp_export.py chat-export.txt \\
        --atendentes "Joao Atendente,Maria Atendente" \\
        --saida conversas.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

LINHA_REGEX = re.compile(
    r"^\s*\[?(?P<dia>\d{1,2})/(?P<mes>\d{1,2})/(?P<ano>\d{2,4})[,\s]+"
    r"(?P<hora>\d{1,2}):(?P<min>\d{2})(?::(?P<seg>\d{2}))?\]?\s*[-]?\s*"
    r"(?P<remetente>[^:]+?):\s*(?P<msg>.*)$"
)
SISTEMA_REGEX = re.compile(
    r"(messages and calls are end-to-end encrypted|mensagens e ligacoes sao protegidas"
    r"|created group|added|left|removed|changed the group)",
    re.IGNORECASE,
)


def parse_arquivo(caminho: Path, atendentes: set[str]) -> list[dict]:
    if not caminho.exists():
        sys.exit(f"erro: nao encontrado — {caminho}")
    eventos: list[dict] = []
    buffer: dict | None = None
    for raw in caminho.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LINHA_REGEX.match(raw)
        if not m:
            if buffer is not None:
                buffer["mensagem"] += "\n" + raw.strip()
            continue
        if buffer is not None:
            eventos.append(buffer); buffer = None
        if SISTEMA_REGEX.search(m.group("msg") or ""):
            continue
        ano = int(m.group("ano"))
        if ano < 100:
            ano += 2000
        try:
            dt = datetime(ano, int(m.group("mes")), int(m.group("dia")),
                          int(m.group("hora")), int(m.group("min")),
                          int(m.group("seg") or 0))
        except ValueError:
            continue
        remetente = m.group("remetente").strip()
        eh_atendente = remetente in atendentes
        buffer = {
            "data_hora": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "atendente": remetente if eh_atendente else "",
            "cliente": _cliente_implicito(remetente, eh_atendente, eventos),
            "direcao": "enviada" if eh_atendente else "recebida",
            "mensagem": m.group("msg") or "",
        }
    if buffer is not None:
        eventos.append(buffer)
    return eventos


def _cliente_implicito(remetente, eh_atendente, eventos):
    if not eh_atendente:
        return remetente
    for e in reversed(eventos):
        if e["direcao"] == "recebida":
            return e["cliente"]
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("entrada", type=Path)
    parser.add_argument("--atendentes", required=True)
    parser.add_argument("--saida", type=Path, default=Path("conversas.csv"))
    args = parser.parse_args()
    atendentes = {a.strip() for a in args.atendentes.split(",") if a.strip()}
    eventos = parse_arquivo(args.entrada, atendentes)
    if not eventos:
        sys.exit("erro: nada extraido — confira lista de atendentes")
    with args.saida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["data_hora", "atendente", "cliente", "direcao", "mensagem"])
        w.writeheader(); w.writerows(eventos)
    print(f"OK — {len(eventos)} msgs em {args.saida}")


if __name__ == "__main__":
    main()
