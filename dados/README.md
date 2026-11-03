# dados/ — Banco de dados do GENO (camada 1: identidade)

> **Quem não é do bloco de dados:** comece por [`PARA_O_GRUPO.md`](PARA_O_GRUPO.md), com o que cada pessoa precisa saber, as decisões pendentes e onde está cada coisa.

## Objetivo

Transformar os Dados Abertos do CNPJ da Receita Federal em um banco reproduzível, `geno.duckdb`, do **setor piloto** (educação livre, RJ), com as views que o app lê, as consultas de saturação e mortalidade e os números oficiais do recorte para o artigo. Qualquer pessoa recria tudo do zero com um comando. A tela de saturação depende só deste bloco: é o plano B do projeto.

## Pré-requisitos

| Item | Valor |
|---|---|
| Python | 3.11 ou mais novo (o relatório técnico pede 3.11+; os números oficiais foram gerados e testados em **3.13.14**) |
| Bibliotecas | só as de [`requirements-dados.txt`](requirements-dados.txt), com versões fixas: duckdb 2.0.0, pandas 3.1.0, numpy 2.5.4, pyarrow 26.0.0, requests 2.34.2, PyYAML 6.0.3, tqdm 4.70.1 e pytest 9.2.0 |
| Disco livre | ≈ **17 GB** no pico (ZIP de 2,3 GB + CSV de 7,3 GB do maior arquivo, mais o CSV convertido para UTF-8 em alguns arquivos). No final ficam ≈ 85 MB de banco e ≈ 40 MB de Parquet; os ZIPs são apagados |
| Rede | ≈ 7,1 GB de download da Receita (o servidor é lento e cai; o download retoma sozinho) |
| Git | opcional; o `METRICAS.md` registra o commit atual |

## Recriar o banco do zero: um comando

```bash
python -m venv .venv
.venv\Scripts\activate                       # Linux/Mac: source .venv/bin/activate
pip install -r dados/requirements-dados.txt
python -m dados.etl.recriar
```

`recriar` baixa, filtra, gera o `candidatos.parquet`, monta o `geno.duckdb`, regenera as métricas e imprime o tempo de cada etapa. Para reaproveitar os Parquet que já existem em `dados/parquet/` (sem baixar nada): `python -m dados.etl.recriar --sem-download`.

| Etapa | Tempo estimado |
|---|---|
| Download dos ZIPs (≈ 7,1 GB, ≈ 5 MB/s) | ≈ 20 min |
| Filtro: Estabelecimentos, Empresas, Simples e domínios (por ZIP, um de cada vez) | ≈ 25 min |
| `candidatos.parquet` | segundos |
| `geno.duckdb`, views e métricas | ≈ 1 min |

Conferir o resultado: `python -m pytest tests -v`.

## Etapa por etapa (se quiser rodar separado)

```bash
python -m dados.etl.baixar --listar            # o que há no servidor, sem baixar
python -m dados.etl.filtrar --baixar           # para cada ZIP: baixa -> filtra -> valida -> apaga o ZIP
python -m dados.etl.candidatos                 # parquet/candidatos.parquet (contrato 2)
python -m dados.etl.construir_db               # geno.duckdb, views e, no fim, METRICAS.md e metricas.json
python -m dados.etl.validar                    # contagens do recorte, cobertura de e-mail, rejeitados
python -m dados.etl.decidir_parametros         # reaplica as regras de decisão (período, limiar, lacuna)
python -m dados.geno_db.gerar_exemplos         # regenera geno_db/EXEMPLOS.md
```

- **Download** (`baixar.py`): retoma por `Range`, tenta de novo com espera crescente, pula o que já está completo e **nunca baixa Sócios**.
- **Filtro** (`filtrar.py`): UF e CNAE principal ou secundário (sem filtro de data); lê o CSV Latin-1 com DuckDB e só apaga o ZIP depois de validar o Parquet e de **conferir os registros lidos contra uma contagem independente do CSV** (nada some em silêncio). Resultado por arquivo em `etl_log.csv`.
- A origem dos dados, o layout conferido e as armadilhas dos CSVs da Receita estão em [`FONTE.md`](FONTE.md).

## Estrutura de pastas

```
dados/
├── config.yaml              parâmetros: fonte, competência, UF, CNAEs, período, limiares, caminhos, colunas
├── requirements-dados.txt   dependências com versões fixas
├── PARA_O_GRUPO.md          o que cada colega precisa saber
├── FONTE.md                 fonte, layout, divergências e armadilhas
├── METRICAS.md, metricas.json   números oficiais do recorte (gerados do banco; não editar à mão)
├── decisoes/DECISOES.md     decisões por regra, com os números que as sustentam
├── etl/                     baixar, filtrar, candidatos, construir_db, validar, decidir_parametros, gerar_metricas, recriar
├── sql/                     01_schema_extra.sql, 02_views.sql, 03_views_publicas.sql e seeds/motivo_classe.csv
├── geno_db/                 consultas.py, EXEMPLOS.md e gerar_exemplos.py (consultas para o app e o motor)
├── consultas.py             funções do contrato com o motor (assinaturas antigas)
├── raw/  parquet/           ZIPs temporários e saída do ETL (fora do Git)
└── geno.duckdb              banco final (fora do Git)
tests/                       test_lgpd.py, test_consultas.py, test_metricas.py, test_limiar.py
```

## Parâmetros e decisões

Todos os parâmetros ficam em [`config.yaml`](config.yaml); nada é fixo no código. O que foi decidido por regra (período 2021 a 2025, `limiar_recuo` 50, regra de lacuna), com a regra e os números de cada decisão, está em [`decisoes/DECISOES.md`](decisoes/DECISOES.md). Para rever uma decisão, altere o `config.yaml` e rode `python -m dados.etl.construir_db`: as consultas e as métricas usam os novos valores.

## O que o banco tem

Segue o [contrato 1](../contratos/01_schema.sql), mais as tabelas de [`sql/01_schema_extra.sql`](sql/01_schema_extra.sql).

- **Grão:** o **estabelecimento** (matriz ou filial, chave `cnpj` de 14 posições, texto); a `empresa` (raiz de 8 posições) guarda razão social, natureza jurídica, porte e capital social. O município é o código da **Receita**, não o do IBGE.
- **Tabelas:** `estabelecimento`, `empresa`, `simples` (Simples e MEI), domínios (`cnae`, `municipio`, `motivo`, `natureza`, `pais`, `qualificacao`, `situacao_cadastral`), `motivo_classe` e as das camadas 2 a 4 (`candidato_dominio`, `pagina`, `classificacao`, `gabarito`, `embedding`), que ficam **vazias** e são preenchidas por Roger e Micael.
- **Views:** `vw_eventos` (aberturas e baixas por estabelecimento, com `classe_baixa` e `baixa_em_massa`), `vw_eventos_longo` (um evento por linha) e `vw_publico`, a **única** fonte que o app pode consultar.
- **Baixas de ofício:** a classe de cada um dos 63 motivos está em [`sql/seeds/motivo_classe.csv`](sql/seeds/motivo_classe.csv): `voluntaria`, `oficio` (atos da Receita, inclusive as baixas em massa de 31/12/2008, 09/02/2015 e 01/02/2018) e `outra`. `baixa_em_massa` é `classe = 'oficio'`.
- O `construir_db` **apaga e recria** o banco: o que alguém tiver gravado nas tabelas das camadas 2 a 4 se perde.

## Consultas

```python
from dados.geno_db import consultas
consultas.saturacao(["8593700"])                        # ano, aberturas, baixas, baixas_oficio, saldo, ativos_fim_ano
consultas.mortalidade_setor(["8593700"], horizonte=2)   # coortes + recuo de CNAE (subclasse -> classe -> grupo)
```

Guia e saídas reais em [`geno_db/EXEMPLOS.md`](geno_db/EXEMPLOS.md). As consultas são parametrizadas, abrem o banco só para leitura e usam por padrão o período e o `limiar_recuo` do `config.yaml`. O caminho do banco vem do `config.yaml` (relativo à raiz do repositório) ou da variável de ambiente `GENO_DB`. As funções antigas do contrato (`dados/consultas.py`, usadas pelo motor) continuam e ignoram as baixas de ofício.

## Testes

```bash
python -m pytest tests -v        # precisa do geno.duckdb já gerado
```

`test_lgpd.py` (nada de contato, endereço, sócios ou razão social de MEI na `vw_publico`), `test_consultas.py` (contagens diretas, recuo, coortes completas), `test_metricas.py` (porcentagens, totais, repetibilidade, parâmetros) e `test_limiar.py` (nenhum texto nem código com limiar diferente do `config.yaml`).

## Privacidade (LGPD)

- Sócios nunca são baixados nem carregados. Telefones são descartados na leitura; do e-mail fica só o domínio.
- O app lê **apenas** a `vw_publico`: `razao_social` é NULL em MEI e empresário individual (natureza 2135), e o nome fantasia some quando repete o nome do titular ou contém e-mail.
- **`parquet/candidatos.parquet` é de uso interno do pipeline e nunca pode ser versionado nem publicado.** A coluna `razao_social` traz, em MEI e empresário individual, o nome do titular seguido do CPF completo (113 mil linhas). O arquivo é para o casamento CNPJ ↔ site; repasse só por canal privado.

Referência: seções 3, 6, 7, 8 e 12 do relatório técnico.
