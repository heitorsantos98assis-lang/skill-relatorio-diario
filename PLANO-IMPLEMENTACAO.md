# Plano de Implementacao — 14 dias

Como sair do zero ate o relatorio chegando no seu privado **toda manha automaticamente**.

## Dia 1 — Pareamento com a skill 08

Se voce ja implementou a skill `monitoramento-equipe` (Bonus 8), **pule essa secao**: o pipeline de coleta de dados ja existe. Use o mesmo CSV.

Se nao: comece pelo `PLANO-IMPLEMENTACAO.md` do Bonus 8 (dia 1-7). Esta skill PRECISA do CSV.

## Dia 2 — Decidir destinatario e formato

| | Diario | Semanal |
|---|---|---|
| **Quem recebe** | Voce, dono | Voce + sócios (se houver) |
| **Horario** | 7h45 (cafe da manha) | Sexta 17h |
| **Canal** | WhatsApp privado | WhatsApp privado + e-mail (opcional) |
| **Tamanho** | <2.000 chars | <4.000 chars |

**Decisao:** registre seu numero em `WHATSAPP_DESTINO` e o de sócios em `WHATSAPP_DESTINOS_EXTRAS` (separados por virgula).

## Dia 3 — Mapear grupos / linhas de negocio

Sua operacao tem como classificar mensagem por linha? Exemplos:

| Tipo de operacao | Grupos uteis |
|---|---|
| Ecommerce | Suporte, Pre-venda, Logistica |
| Servico B2B | Vendas, CS, Tecnico |
| Infoproduto | Pre-venda, Aluno, Reembolso |
| Saas | Free trial, Pago, Enterprise |

Como popular `grupo` no CSV:
- **Manual:** voce edita o CSV antes de rodar (suporta sed/awk).
- **Pelo numero:** se cada grupo tem um numero WhatsApp diferente, o conversor pode preencher.
- **Pelo nome do contato:** se voce tagueia clientes (Suporte | Maria Cliente).

**Acao do dia:** decida 3-6 grupos relevantes e como populá-los.

## Dia 4 — Lista de VIPs (mesma do Bonus 8)

Se ja tem `vips.txt` da skill 08, reuse. Caso contrario:

```
Roberto Construtora ACME
Mariana Costa
Empresa Cicrano LTDA
```

VIPs ganham destaque automatico no diario.

## Dia 5-6 — Primeira rodada manual + validacao

```bash
# 1) Diario do ultimo dia presente no CSV
python scripts/relatorio_diario.py conversas.csv --vip vips.txt

# 2) Semanal da janela atual
python scripts/relatorio_semanal.py conversas.csv
```

**Cheque manualmente:**
- O total de mensagens recebidas bate com a sua percepcao?
- Os VIPs listados sao os que voce esperava?
- A categoria "fechamento" detectou as vendas que voce sabe que rolaram?
- Algum cliente apareceu em "top 10" que voce nao reconhece? (pode ser spam/lead frio).

## Dia 7 — Configurar envio

Reutilize `~/.credentials/zappfy.env` do Bonus 8. Teste:

```bash
python scripts/relatorio_diario.py conversas.csv --vip vips.txt | \
    python envio/enviar_relatorio.py --prefixo "📊 Diario\n\n"
```

Deve chegar no seu WhatsApp em <10s.

## Dia 8 — Cron diario + semanal

```cron
# 7h45 - relatorio do dia ANTERIOR (precisa ter o CSV ate as 7h45)
45 7 * * 1-5  cd /Users/SEU/operacao && \
    python conversores/converter_zappfy.py --url $ZAPPFY_URL --token $ZAPPFY_TOKEN --dias 1 --saida ontem.csv && \
    python scripts/relatorio_diario.py ontem.csv --vip vips.txt --data $(date -v-1d +"%Y-%m-%d") | \
    python envio/enviar_relatorio.py --prefixo "📊 Resumo de ontem\n\n"

# Sexta 17h - semanal
0 17 * * 5    cd /Users/SEU/operacao && \
    python conversores/converter_zappfy.py --url $ZAPPFY_URL --token $ZAPPFY_TOKEN --dias 14 --saida semana.csv && \
    python scripts/relatorio_semanal.py semana.csv | \
    python envio/enviar_relatorio.py --prefixo "📊 Semana\n\n"
```

## Dia 9-10 — Validar 2 ciclos

Deixe rodar 2 dias + 1 sexta. Cheque:
- Diario chegou nos 2 dias?
- Semanal chegou na sexta?
- Cohort faz sentido? (novos sao realmente novos, nao bug de nome).
- Keywords de negocio refletem o tipo de cliente que voce atende?

## Dia 11 — Tunings

Edite o que precisar:

### Keywords customizadas

Edite `KEYWORDS_NEGOCIO` em `relatorio_semanal.py` pra adicionar termos do seu nicho:

```python
# clinica medica
KEYWORDS_NEGOCIO["agendamento"] = ["marcar", "agendar", "consulta", "horario"]
KEYWORDS_NEGOCIO["sintoma"] = ["dor", "febre", "tossindo", "alergia"]

# escola
KEYWORDS_NEGOCIO["matricula"] = ["matricular", "matricula", "matriculação"]

# infoproduto
KEYWORDS_NEGOCIO["bonus"] = ["bonus", "brinde", "extra", "ganhei"]
KEYWORDS_NEGOCIO["fechado"] = ["paguei", "ja pago", "transferi", "comprado"]
```

### Limiar de pico

Default: "Hora mais cheia". Se sua operacao tem 2 picos (almoco + noite), customize.

### Tamanho do top

Default `n=10`. Pra dashboards executivos, `n=5` cabe melhor em mensagem.

## Dia 12-13 — Compartilhar com sócios

Se tem outros sócios:
1. Cole o relatorio na conversa "Sócios" como teste.
2. Depois de 2-3 dias com feedback positivo, automatize o envio pra eles tambem.

Cuidado: nao mande pra time todo. Esse relatorio nominal de clientes é confidencial.

## Dia 14 — Ritual definido

| Quando | O que voce faz com o relatorio |
|---|---|
| Diario 8h | Le com o cafe. Se houver VIP aguardando, age direto antes do daily. |
| Sexta 17h | Le o semanal. No fim da tarde, anota 1-2 movimentos pra segunda. |
| Domingo 19h | Re-le o semanal frio. Decide as 3 prioridades da semana. |
| Mensal | Arquive 4 semanais. Compara M1 vs M4 — voce ta crescendo? Cohort ta saudavel? |

## Sinais de sucesso depois de 30 dias

- Voce **nao olha mais o WhatsApp pra ver "como ta".** O diario te diz.
- TPR mediano **caiu** comparando semana 1 e semana 4.
- % de cliente VIP que ficou AGUARDANDO **caiu pra zero**.
- Voce identifica **antes** quando uma keyword de cancelamento ou reclamacao explode (e pode agir).
- Voce sabe **a hora de pico** real e organiza escala em torno dela (nao do palpite).

## Sinais de falha

| Sintoma | Causa | Acao |
|---|---|---|
| "Volume por grupo" some | Coluna `grupo` vazia | Popule no CSV ou customize conversor |
| Cohort mostra 100% novos | Janela curta demais (ex: 1 dia) | Rode com 7+ dias |
| Keywords nao detectam o que voce esperava | Cliente usa girias do nicho que nao estao na lista | Edite `KEYWORDS_NEGOCIO` |
| TPR aparece "—" | Sem par recebida→enviada (operacao so de envio?) | Skill nao se aplica — use outra |
| Relatorio nao chega | `ZAPPFY_URL_ENVIO` errada ou Zappfy fora | Teste curl manual, veja painel Zappfy |

---

*Material criado pela Bravy.*
