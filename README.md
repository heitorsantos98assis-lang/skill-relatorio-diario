# Bonus 9 — Skill de Relatorio Diario E Semanal Automatico

Skill do Claude Code que gera **resumo diario** + **relatorio semanal** da operacao de WhatsApp — pra chegar no seu privado **toda manha + toda sexta**.

> Foco no **negocio** (volume, VIPs, grupos, keywords, cohort), nao no time (pra time use o Bonus 8).
> Aceita CSV padrao, export `.txt` do WhatsApp Business e JSON da Zappfy.

## Diferenca Bonus 8 vs Bonus 9

| | Bonus 8 — monitoramento-equipe | Bonus 9 — relatorio-diario (esta) |
|---|---|---|
| **Foco** | Time (TPR por pessoa) | Negocio (volume, VIPs, grupos) |
| **Para quem** | Gestor cobrar a equipe | Dono ler com o cafe |
| **Detecta** | Cancelar / reclamacao / urgencia | Interesse / preco / objecao / fechamento / cancelamento |
| **Quando** | Meio/fim do expediente | Manha do dia seguinte + sexta semanal |

As duas se complementam. Operacao tipica usa as duas.

## O que voce ganha

### Diario (`relatorio_diario.py`)

- Visao geral (recebidas, respondidas, TPR, em-aberto)
- Evolucao vs ontem (▲▼▬)
- Conversas sem resposta (com destaque pra >2h)
- VIPs nominais com status (✅ respondido / ⚠️ aguardando)
- Volume por grupo (linha de negocio)
- Destaques automaticos
- Proximos passos priorizados

### Semanal (`relatorio_semanal.py`)

- KPIs da semana
- **Curva diaria** em sparkline (recebidas, respondidas, TPR)
- **Comparativo vs semana anterior** (▲▼▬)
- **Top 10 clientes** por interacao
- **Cohort** novos vs recorrentes (% + nomes)
- **Keywords de negocio** por categoria (interesse / preco / objecao / fechamento / reclamacao / cancelamento) com contagem + exemplo
- **Hora pico** com alerta fora do horario comercial
- **Projecao**: % das conversas ja em <5min + potencial restante

## Estrutura

```
09-skill-relatorio-diario/
├── SKILL.md
├── PLANO-IMPLEMENTACAO.md
├── scripts/
│   ├── relatorio_diario.py
│   └── relatorio_semanal.py
├── conversores/
│   └── converter_whatsapp_export.py
├── envio/
│   └── enviar_relatorio.py
├── exemplos/
│   ├── conversas-exemplo.csv     (2 dias)
│   ├── conversas-14dias.csv      (14 dias - pra ver cohort + comparativo)
│   └── vips-exemplo.txt
├── 09-skill-relatorio-diario.zip
└── README.md
```

## Instalacao

```bash
mkdir -p ~/.claude/skills
cp -r . ~/.claude/skills/relatorio-diario
```

## Dependencias

Python 3.9+. Os scripts de analise (`relatorio_diario.py`, `relatorio_semanal.py`) usam **so biblioteca padrao** — zero `pip install`.

Conversor e envio:
```bash
pip install requests   # so se for usar API Zappfy ou enviar via WhatsApp
```

## Quickstart (3 minutos)

```bash
# 1) Diario do ultimo dia presente no CSV
python scripts/relatorio_diario.py exemplos/conversas-exemplo.csv \
    --vip exemplos/vips-exemplo.txt

# 2) Semanal (14 dias - mostra cohort + comparativo + keywords)
python scripts/relatorio_semanal.py exemplos/conversas-14dias.csv

# 3) Pipeline pra mandar no seu WhatsApp
python scripts/relatorio_diario.py conversas.csv --vip vips.txt | \
    python envio/enviar_relatorio.py --prefixo "📊 Resumo de ontem\n\n"
```

## Setup em producao

Veja **`PLANO-IMPLEMENTACAO.md`** — plano de 14 dias com:
- Decisao de destinatario (voce / sócios)
- Mapear linhas de negocio em `grupo`
- Validacao manual obrigatoria
- Cron diario 7h45 + semanal sexta 17h
- Customizacao de keywords por nicho (clinica, escola, infoproduto, saas)
- Ritual de leitura (diario, sexta, domingo, mensal)
- Sinais de sucesso + falha + acao

## Output (testado nos exemplos)

**Diario** — 92% taxa de resposta, 4 VIPs do dia, 1 aguardando:

```
═══════════════════════════════════════════
RESUMO DO DIA — 24/05/2026

VISAO GERAL
- Mensagens recebidas:     13
- Mensagens respondidas:   12  (92%)
- TPR:                3min55s

EVOLUCAO vs DIA ANTERIOR
- Recebidas:   +18%  ▲
- Respondidas: +33%  ▲
- TPR:         -41%  ▲ (melhorou)

CLIENTES VIP QUE MANDARAM HOJE
🌟 Roberto VIP     — 09:14 — respondido em 3min39s  ✅
🌟 Carla Premium   — 16:47 — AGUARDANDO            ⚠️
```

**Semanal** — keywords detectaram 20 mensagens de interesse e 4 de objecao:

```
KPIs DA SEMANA
  Recebidas: 65 | Respondidas: 51 (78%) | TPR: 9min

CURVA DIARIA
  Recebidas    ▄█▅▃█▁▁
  TPR          ▁▃▂█▃▇▇    (max 20min)
               STQQSSD

COMPARATIVO vs SEMANA ANTERIOR
  Recebidas         65  ←  60      (+8%)  ▲
  Taxa resposta    78%  ←  85%     (-8%)  ▼
  TPR mediano    9min  ←  7min   (+23%)   ▼

COHORT: NOVOS vs RECORRENTES
  Novos: 9 (47%) | Recorrentes: 10

KEYWORDS DE NEGOCIO
  INTERESSE     20  exemplo: 'Como funciona a garantia?'
  PRECO          7  exemplo: 'Quanto custa premium?'
  OBJECAO        4  exemplo: 'Vou comprar no concorrente'
  RECLAMACAO     5  exemplo: 'Esta um lixo, quero cancelar'

PICO DE DEMANDA: 14h (10 msgs na semana)

PROJECAO
  Hoje em <5min: 31.4%
  Potencial:      68.6%
```

## Boas praticas

- **Privado, nao grupo.** Mostra nome de cliente — expor em grupo viola LGPD.
- **Compare semana com semana.** Salve cada `semana_YYYY-WW.txt`. 4 semanas = serie pra ver sazonalidade.
- **Customize keywords pro seu nicho** (veja PLANO dia 11).
- **Não mande pra time todo.** Esse relatorio tem nome de cliente e e estrategico.

---

*Material criado pela HL.*
