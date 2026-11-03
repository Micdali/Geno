# Contratos entre os blocos

Os blocos do GENO só se comunicam pelo que está nesta pasta. Se você seguir o contrato, pode trabalhar sem esperar ninguém.

| # | Contrato | De → para | Arquivo |
|---|---|---|---|
| 1 | Schema do banco | todos | [`01_schema.sql`](01_schema.sql) |
| 2 | Empresas candidatas | Lucas → Roger | [`02_candidatos.md`](02_candidatos.md) |
| 3 | Classificação por empresa | Micael (LLM) → banco | [`03_classificacao.schema.json`](03_classificacao.schema.json) |
| 4 | Resultado da análise | Micael (motor) → Christian (app) | [`04_resultado_analise.md`](04_resultado_analise.md) |

Em `exemplos/` há um arquivo de exemplo para cada contrato, com **empresas e números fictícios** (CNPJs começando em `99`, domínios `.invalid`). Servem para desenvolver antes de existir dado real. **Nunca use esses números no artigo.**

## Status

Todos em **v0 — aguardando aprovação do grupo** (prazo: qui 15/10). O contrato 1 está na **v0.1** (03/11): as visões ganharam colunas do bloco de dados, sem remover nenhuma. Pendência principal: o conjunto final de atributos da classificação (contrato 3), que também muda as colunas de `classificacao` e `gabarito` no contrato 1.

Para mudar um contrato depois de aprovado, ver [`CONTRIBUTING.md`](../CONTRIBUTING.md).
