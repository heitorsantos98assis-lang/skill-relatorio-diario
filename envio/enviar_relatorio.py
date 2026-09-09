#!/usr/bin/env python3
"""
Envia o relatorio do dia/semana no seu privado via Zappfy.

Le de stdin (ou --arquivo) e dispara mensagem.

Variaveis de ambiente:
    ZAPPFY_URL_ENVIO  — ex: https://api.zappfy.io/v2/messages
    ZAPPFY_TOKEN      — bearer token
    WHATSAPP_DESTINO  — 55DDDNUMERO

Uso:
    python scripts/relatorio_diario.py conversas.csv | python envio/enviar_relatorio.py
    python envio/enviar_relatorio.py --arquivo relatorio.txt --prefixo "📊 Diario"

Criado pela HL.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def enviar(texto: str, url: str, token: str, destino: str) -> dict:
    try:
        import requests
    except ImportError:
        sys.exit("erro: instale 'requests' (pip install requests)")
    if not texto.strip():
        sys.exit("erro: texto vazio")
    if len(texto) > 4096:
        # whatsapp limita 4096 — quebra em pedacos se passar
        partes = []
        while texto:
            partes.append(texto[:4090])
            texto = texto[4090:]
        for i, parte in enumerate(partes, 1):
            r = requests.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"phone": destino, "message": f"({i}/{len(partes)})\n{parte}"},
                timeout=30,
            )
            if not r.ok:
                sys.exit(f"erro {r.status_code}: {r.text[:200]}")
        return {"ok": True, "partes": len(partes)}
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"phone": destino, "message": texto},
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"erro Zappfy {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {"ok": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="Enviar relatorio via Zappfy")
    parser.add_argument("--arquivo", type=Path)
    parser.add_argument("--url", default=os.environ.get("ZAPPFY_URL_ENVIO", ""))
    parser.add_argument("--token", default=os.environ.get("ZAPPFY_TOKEN", ""))
    parser.add_argument("--destino", default=os.environ.get("WHATSAPP_DESTINO", ""))
    parser.add_argument("--prefixo", default="📊 Relatorio\n\n")
    args = parser.parse_args()

    if not (args.url and args.token and args.destino):
        sys.exit("erro: defina ZAPPFY_URL_ENVIO, ZAPPFY_TOKEN, WHATSAPP_DESTINO")

    texto = args.arquivo.read_text(encoding="utf-8") if args.arquivo else sys.stdin.read()
    enviar(args.prefixo + texto, args.url, args.token, args.destino)
    print(f"OK enviado para {args.destino}", file=sys.stderr)


if __name__ == "__main__":
    main()
