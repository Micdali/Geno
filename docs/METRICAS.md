# MÉTRICAS — camada de enriquecimento (Roger)

Gerado por `python -m enriquecimento.metricas`. Números do `geno.duckdb` atual.

## Cobertura
- CNPJs com ao menos um domínio candidato: **2954**
  - `email`: 2954 hipótese(s)
  - `nome_titulo`: 626 hipótese(s)
  - `rodape_cnpj`: 56 hipótese(s)

## Coleta e bloqueio
- Domínios visitados: **1826**
- Domínios bloqueados (ex.: Cloudflare, não contornados): **114** (6.2%)
- Domínios sem texto aproveitável (ex.: SPA/JS): **199** (10.9%)
- Páginas coletadas: 2499 (bloqueadas: 116)

## Domínios de contador descartados (antes de coletar)
- Total descartado: **3054**
  - por frequência (em >= 3 CNPJs): 1776
  - por nome (contab/fiscal/assessoria/adv.): 1731
  - pegos pelas duas regras: 453

## Exposição de CNPJ (potencial do Método 2)
- Domínios com CNPJ válido no texto: **188** de 1712 (11.0%)
## Precisão por método
Sobre os lotes já entregues ao motor (991 CNPJs).

**Conferida à mão** (motor, lote 1 de 03/11) — vínculos que eram mesmo escola:
- `rodape_cnpj`: 16/19 (84.2%)
- `nome_titulo`: 38/58 (65.5%)
- `email`: 40/127 (31.5%)

**Cross-check automático** — homes (status 200) com palavra de ensino, por método:
- `rodape_cnpj`: 59/74 (79.7%)
- `nome_titulo`: 177/226 (78.3%)
- `email`: 577/715 (80.7%)

## Notas
- O **e-mail** é o método mais fraco (o domínio cadastral muitas vezes é do contador ou de um portal, não do site de ensino). Por isso um vínculo por e-mail só é entregue quando o site mostra conteúdo de ensino em alguma página; rodapé e nome × título entram sempre.
- A **precisão conferida à mão** é a do artigo; o cross-check automático é só um indicador barato (mede palavra de ensino na home, não classificação de verdade).
