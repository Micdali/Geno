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

```bash
python -m dados.etl.filtrar --baixar    # para cada ZIP: baixa (se faltar) -> filtra -> valida -> apaga o ZIP
python -m dados.etl.candidatos          # gera parquet/candidatos.parquet (contrato 2)
python -m dados.etl.validar             # contagens, cobertura de e-mail, rejeitados, tamanho
```

Ordem interna do `filtrar`: Estabelecimentos (UF e CNAE principal ou secundário) → Empresas e Simples (só as raízes de CNPJ do recorte) → tabelas de domínio. Opções: `--etapa estabelecimentos|empresas|simples|dominio`, `--refazer` (reprocessa mesmo com Parquet pronto), `--manter-zip`.

O que o filtro garante:

- **Nada some em silêncio.** Antes de apagar o ZIP, ele compara os registros lidos pelo DuckDB com uma contagem independente do CSV (linhas físicas menos as quebras de linha dentro de campos entre aspas) e para se divergir. Resultado por arquivo em `dados/etl_log.csv`; exemplos de linhas malformadas, se houver, em `dados/etl_rejeitados.csv`.
- **Privacidade.** Telefones e fax são descartados na leitura; do e-mail fica só `dominio_email` (NULL para provedores genéricos, lista no `config.yaml`). Sócios nunca é baixado.
- **Sem filtro de data.** O recorte temporal é feito depois, nas views.
- O Parquet só substitui o anterior depois de validado, e o ZIP só é apagado depois disso.

Armadilhas já encontradas nos CSVs da Receita (detalhes no `FONTE.md`): aspas duplicadas dentro de campos (`"NIGTH CLUB ""TUTU"" LTDA"`), quebra de linha dentro de campo e alguns bytes de controle que o DuckDB recusa como Latin-1 (nesse caso o arquivo é convertido para UTF-8 em streaming).

**Tempo e disco (competência 2026-10, máquina do Lucas):** ≈ 7,1 GB de download (uns 20 min a ~5 MB/s) e ≈ 25 min de processamento. O pico de disco é o ZIP mais o CSV do maior arquivo (≈ 10 GB; com a conversão para UTF-8, que ocorre em alguns arquivos, até ≈ 17 GB). A saída final em `dados/parquet/` ocupa ≈ 34 MB.

### Etapa 3 — montar o banco

```bash
python -m dados.etl.construir_db        # gera dados/geno.duckdb (≈ 65 MB, segundos)
```

Aplica `contratos/01_schema.sql`, carrega a camada 1 (datas e valores já convertidos, CNPJ como texto), preenche `motivo_tipo` a partir do `config.yaml` e aplica [`sql/02_views.sql`](sql/02_views.sql). Confere as contagens contra os Parquet e só então troca o banco anterior. As camadas 2 a 4 ficam criadas e vazias (Roger e Micael preenchem).

O que `02_views.sql` muda em relação ao contrato (a conferir pelo grupo):

- **`vw_eventos`** mantém as colunas do contrato e acrescenta `tipo_baixa` e `conta_mortalidade`. Só baixas por encerramento (voluntária, judicial, óbito de MEI) contam como mortalidade; baixas de ofício (omissão, inaptidão, registro cancelado) e reorganizações (incorporação, troca matriz/filial) não. A lista está em `config.yaml` (`baixas`), é proposta minha e precisa de confirmação.
- **`vw_publico`** também esconde o nome fantasia de MEI/empresário individual quando ele repete o nome do titular (com ou sem o CPF). Limite: um nome fantasia que é só o primeiro nome não é detectado.

Funções de `consultas.py` (leem o banco em modo somente leitura):

```python
from dados import consultas
consultas.saturacao(cnpjs, 2018)          # ano, aberturas, baixas (só mortalidade) de um conjunto
consultas.saturacao_setor_amplo(2018)     # o mesmo para todo o recorte
consultas.dados_publicos(cnpjs)           # lê só vw_publico
```

O ano corrente é parcial. Defina `GENO_DB` no `.env` se o banco ficar noutro lugar.

Referência: seções 3, 6, 7, 8 e 12 do relatório técnico.
