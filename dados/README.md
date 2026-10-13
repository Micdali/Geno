# dados/ — Camada 1: identidade (dono: Lucas)

Transforma os Dados Abertos do CNPJ da Receita no banco `geno.duckdb` do setor piloto.

**Objetivo até 05/11:** banco reproduzível por script (qualquer pessoa recria do zero), com as visões e as consultas que o app usa. A tela de saturação depende só deste bloco: é o plano B do projeto.

## Entrega para os outros blocos

- `geno.duckdb` no schema de [`contratos/01_schema.sql`](../contratos/01_schema.sql)
- `parquet/candidatos.parquet` para o Roger ([contrato 2](../contratos/02_candidatos.md))
- As funções em `consultas.py`, usadas pelo motor

## Pastas locais (fora do Git)

- `raw/` — ZIPs baixados da Receita (apagados depois de processar)
- `parquet/` — recorte filtrado, identificado pela competência (o snapshot do MVP)

## Como recriar o banco

> A preencher pelo Lucas: comando, competência usada, tempo aproximado.

Referência: seções 3, 6, 7, 8 e 12 do relatório técnico.
