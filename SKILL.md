---
name: skill-relatorio-diario
description: "Gera relatorio diario E semanal do WhatsApp pra chegar no seu privado. Use quando o usuario pedir para \"ver como foi ontem\", \"resumo do dia/semana\", \"como foi a operacao\", \"VIPs que mandaram\", \"volume por grupo\", \"top clientes da semana\", \"curva da semana\", \"comparativo semanal\", \"hora pico\", \"cohort cliente novo\". Aceita CSV, .txt do WhatsApp Business e JSON Zappfy."
allowed-tools: Read Write Bash
---

# Skill — Relatorio Diario E Semanal do WhatsApp

Duas analises voltadas pro **dono / sócio** (nao para gestor de time):

1. **Relatorio diario** (`relatorio_diario.py`) — resumo do dia para chegar no privado toda manha.
2. **Relatorio semanal** (`relatorio_semanal.py`) — curva da semana, cohort, keywords de negocio, comparativo vs semana anterior, projecao.

## Diferenca entre as 2 skills (08 vs 09)

| | Bonus 8 — monitoramento-equipe | Bonus 9 — relatorio-diario (esta) |
|---|---|---|
| **Foco** | Time (TPR por pessoa, distribuicao) | Negocio (volume, VIPs, grupos, keywords) |
| **Para quem** | Gestor cobrar a equipe | Dono ler com o cafe |
| **Mostra atendente?** | Sim, ranking + alertas | Nao — anonimo no nivel de pessoa |
| **Detecta?** | Cancelar / reclamacao / urgencia / concorrente | Interesse / preco / objecao / fechamento / reclamacao / cancelamento |
| **Quando rodar** | Meio/fim do expediente | Manha do dia seguinte + sexta semanal |

> Operacao tipica: roda **as duas em horarios diferentes**. O dono ve o `relatorio-diario` no privado as 7h45 com o cafe. O gestor ve `monitoramento-equipe` as 12h e 18h.

## O que o diario entrega (relatorio_diario.py)

- **Visao geral**: recebidas, respondidas (com %), TPR mediano, em aberto.
- **Evolucao vs ontem** (▲▼▬).
- **Conversas sem resposta** com destaque pras que tem >2h de espera.
- **VIPs que mandaram hoje** com status individual.
- **Volume por grupo** (Vendas / Suporte / Comercial / etc).
- **Destaques** automaticos.
- **Proximos passos** priorizados.

## O que o semanal entrega (relatorio_semanal.py)

- **KPIs da semana** (com taxa de resposta e em-aberto).
- **Curva diaria** em sparkline (recebidas, respondidas, TPR).
- **Comparativo vs semana anterior** com ▲▼▬.
- **Top 10 clientes** por interacao.
- **Cohort** novos vs recorrentes (% + lista de novos).
- **Keywords de negocio** detectadas por categoria — interesse / preco / objecao / fechamento / reclamacao / cancelamento — com contagem + exemplo.
- **Hora pico de demanda** — alerta se for fora do horario comercial.
- **Projecao** — quanto da sua semana ja foi respondida em <5min (correlacao com fechamento ~3x maior em B2C tipico).

## Estrutura

```
relatorio-diario/
├── SKILL.md
├── PLANO-IMPLEMENTACAO.md
├── scripts/
│   ├── relatorio_diario.py     ← resumo do dia
│   └── relatorio_semanal.py    ← curva + cohort + keywords + comparativo
├── conversores/
│   └── converter_whatsapp_export.py
├── envio/
│   └── enviar_relatorio.py     ← manda no seu privado via Zappfy
├── exemplos/
│   ├── conversas-exemplo.csv         ← 2 dias com coluna "grupo"
│   ├── conversas-14dias.csv          ← 14 dias (cohort + comparativo)
│   └── vips-exemplo.txt
└── README.md
```

## Inputs aceitos

Mesmo padrao da skill `monitoramento-equipe`:

1. **CSV padrao** (coluna `grupo` opcional, habilita "Volume por grupo"):
   ```csv
   data_hora,atendente,cliente,direcao,mensagem,grupo
   2026-05-24 09:12:03,,Pedro Fulano,recebida,"Bom dia, preço?",Vendas
   ```
2. **Export `.txt` do WhatsApp Business** — converter com `converter_whatsapp_export.py`.
3. **JSON da API Zappfy** — usar o conversor do Bonus 8 (`converter_zappfy.py`).

## Como rodar

### Diario

```bash
# resumo do ultimo dia presente no CSV
python scripts/relatorio_diario.py conversas.csv --vip vips.txt

# dia especifico
python scripts/relatorio_diario.py conversas.csv --data 2026-05-24

# envia no seu privado
python scripts/relatorio_diario.py conversas.csv --vip vips.txt | \
    python envio/enviar_relatorio.py --prefixo "📊 Resumo de ontem\n\n"
```

### Semanal

```bash
# ultima janela de 7 dias
python scripts/relatorio_semanal.py conversas.csv

# janela customizada
python scripts/relatorio_semanal.py conversas.csv \
    --inicio 2026-05-18 --fim 2026-05-24

# envia no seu privado (toda sexta 17h)
python scripts/relatorio_semanal.py conversas.csv | \
    python envio/enviar_relatorio.py --prefixo "📊 Semana\n\n"
```

## Output real (testado nos exemplos)

### Diario

```
═══════════════════════════════════════════
RESUMO DO DIA — 24/05/2026
═══════════════════════════════════════════

VISAO GERAL
- Mensagens recebidas:     13
- Mensagens respondidas:   12  (92%)
- Tempo medio de resposta: 3min55s
- Conversas em aberto:      1  (8%)

EVOLUCAO vs DIA ANTERIOR
- Recebidas:   +18%  ▲
- Respondidas: +33%  ▲
- TPR:         -41%  ▲

CLIENTES VIP QUE MANDARAM HOJE
🌟 Roberto VIP     — chegou 09:14 — respondido em 3min39s  ✅
🌟 Mariana Costa   — chegou 14:18 — respondido em   7min   ✅
🌟 Carla Premium   — chegou 16:47 — AGUARDANDO            ⚠️
🌟 Rafael Pinheiro — chegou 17:02 — respondido em  10min   ✅

VOLUME POR GRUPO
| Grupo               | Recebidas | Respondidas | %    |
|---------------------|-----------|-------------|------|
| Grupo Vendas        |         8 |           9 | 100% |
| Grupo Suporte       |         3 |           3 | 100% |
| Grupo Comercial     |         2 |           2 | 100% |
```

### Semanal

```
KPIs DA SEMANA
  Mensagens recebidas:     65
  Tempo medio de resposta: 9min
  Conversas em aberto:     2

CURVA DIARIA
  Recebidas    ▄█▅▃█▁▁
  Respondidas  ▂▅▄▂█▁▁
  TPR          ▁▃▂█▃▇▇
               STQQSSD

COMPARATIVO vs SEMANA ANTERIOR
  Recebidas              65  ←  60      (+8%)   ▲
  Taxa resposta %       78%  ←  85%     (-8%)   ▼
  TPR mediano          9min  ←  7min   (+23%)   ▼

TOP 10 CLIENTES POR INTERACAO
   1. Isadora Lima        9 msgs
   2. Andre Cliente       7 msgs
   ...

COHORT: NOVOS vs RECORRENTES
  Clientes primeira vez:  9  (47.4%)
  Recorrentes:           10

KEYWORDS DE NEGOCIO DETECTADAS
  INTERESSE      20  exemplo: 'Como funciona a garantia?' (Pedro Fulano)
  PRECO           7  exemplo: 'Quanto custa premium?' (Aline Souza)
  OBJECAO         4  exemplo: 'Vou comprar no concorrente' (Isadora Lima)
  RECLAMACAO      5  exemplo: 'Esta um lixo, quero cancelar' (Mariana Costa)
  CANCELAMENTO    5

PICO DE DEMANDA
  Hora mais cheia: 14h  (10 mensagens na semana)

PROJECAO — Se TODA primeira resposta fosse em <5min
  Hoje voce ja responde em <5min em 31.4% das conversas
  Potencial: melhorar os outros 68.6%
```

## Restricoes — o que a skill NUNCA faz

- **Nunca envia mensagem ao cliente.** So manda relatorio pra voce.
- **Nunca inventa volume.** Sem coluna `grupo`, secao e omitida (nao estimada).
- **Nunca infere VIP.** Sem `--vip`, secao VIPs fica vazia.
- **Nunca atribui culpa a atendente.** Essa skill e do negocio. Pra time, use 08.

## Combinacoes poderosas

```
Toda sexta 17h: rode relatorio_semanal, salve em /relatorios/semana_$(date).txt,
envie no privado. Se TAXA caiu >5% vs semana anterior, abra task urgente no ClickUp.
```

```
Toda manha 7h45: rode relatorio_diario do dia anterior, envie no privado.
Pra cada VIP em "AGUARDANDO", crie task urgente atribuida pra ti.
```

---

*Skill criada pela HL.*
