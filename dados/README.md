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

Todos os parâmetros (UF, CNAEs, competência, caminhos) ficam em [`config.yaml`](config.yaml). A origem dos dados, o layout conferido e as divergências estão em [`FONTE.md`](FONTE.md).

### Etapa 1 — baixar (pronta)

```bash
python -m dados.etl.baixar --listar     # o que há no servidor, sem baixar
python -m dados.etl.baixar              # baixa tudo do config.yaml (≈ 7,1 GB, uns 20 min a ~5 MB/s)
python -m dados.etl.baixar --arquivo Simples   # só um arquivo
```

- Retoma de onde parou se a conexão cair ou se você interromper (Ctrl+C); rodar de novo pula o que já está completo.
- Os ZIPs vão para `dados/raw/` (fora do Git). Sócios nunca é baixado.
- Precisa de ≈ 7,1 GB livres para os ZIPs, mais ≈ 7,3 GB na hora de extrair o maior CSV (Estabelecimentos0).

### Etapa 2 — filtrar e gerar Parquet

> A fazer (Fase 2): `etl/filtrar.py`, `candidatos.parquet` e validação.

Referência: seções 3, 6, 7, 8 e 12 do relatório técnico.
