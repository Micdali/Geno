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
python -m dados.etl.construir_db        # gera dados/geno.duckdb (≈ 85 MB, segundos)
python -m pytest tests -v               # testes de LGPD sobre o banco gerado
```

Aplica, nesta ordem: `contratos/01_schema.sql`, [`sql/01_schema_extra.sql`](sql/01_schema_extra.sql) (tabelas `simples`, `pais`, `qualificacao` e `situacao_cadastral`, que o contrato não traz), [`sql/02_views.sql`](sql/02_views.sql) e [`sql/03_views_publicas.sql`](sql/03_views_publicas.sql). Carrega a camada 1 (datas e valores já convertidos, CNPJ como texto) e preenche `motivo_tipo` a partir do `config.yaml`. Confere as contagens contra os Parquet e só então troca o banco anterior. As camadas 2 a 4 ficam criadas e vazias (Roger e Micael preenchem).

Views (mudanças em relação ao contrato, a conferir pelo grupo):

- **`vw_eventos`** (`02_views.sql`) mantém as colunas do contrato e acrescenta `classe_baixa` e `baixa_em_massa`. A classe de cada motivo de baixa vem do seed versionado [`sql/seeds/motivo_classe.csv`](sql/seeds/motivo_classe.csv) (63 motivos, com justificativa): `voluntaria` (91,7% das baixas), `oficio` (6,9%: atos da Receita, inclusive as 3 baixas em massa de 31/12/2008, 09/02/2015 e 01/02/2018) e `outra` (1,4%: óbito de MEI, falência, reorganizações). `baixa_em_massa` é `classe = 'oficio'`. O `construir_db` falha se o seed não cobrir exatamente a tabela `motivo`.
- **`vw_eventos_longo`** (`03_views_publicas.sql`): um evento por linha (abertura ou baixa), por estabelecimento. Colunas: `cnpj`, `tipo_evento`, `data_evento`, `ano`, `motivo`, `cnae_fiscal_principal`, `municipio` (código da Receita), `identificador_matriz_filial`, `opcao_mei`, `natureza_juridica`. Sem filtro de período.
- **`vw_publico`** (`03_views_publicas.sql`) é a única fonte que o app pode consultar. Mantém as colunas do contrato e acrescenta nome fantasia, razão social, CNAE e descrição, situação e descrição, porte e opções do Simples e do MEI. Regras de LGPD: `razao_social` é NULL em MEI e natureza 2135 (empresário individual); o nome fantasia some quando, em MEI/empresário individual, repete o nome do titular (com ou sem CPF) e em qualquer empresa quando contém `@`. Limite aceito: nomes parciais do titular (ex.: só o primeiro nome) continuam visíveis. Não expõe e-mail, telefone, endereço detalhado nem sócios.

Testes (`tests/test_lgpd.py`, precisam do banco já gerado): conferem que MEI e natureza 2135 não têm razão social, que a view não traz colunas de contato ou endereço detalhado nem valores com cara de e-mail, e que o banco não tem sócios, telefone nem e-mail completo.

Consultas para o app e o motor, em [`geno_db/consultas.py`](geno_db/consultas.py) (guia e exemplos com saídas reais em [`geno_db/EXEMPLOS.md`](geno_db/EXEMPLOS.md)):

```python
from dados.geno_db import consultas
consultas.saturacao(["8593700"])                        # ano, aberturas, baixas, baixas_oficio, saldo, ativos_fim_ano
consultas.mortalidade_setor(["8593700"], horizonte=2)   # coortes + recuo de CNAE (subclasse -> classe -> grupo)
```

Período padrão (2021 a 2025, só anos completos) e limiar de recuo (30 estabelecimentos) estão em `config.yaml`, seção `consultas`, e são provisórios. As consultas são parametrizadas e abrem o banco só para leitura; o caminho vem do `config.yaml` (relativo à raiz do repositório) ou da variável de ambiente `GENO_DB`. As funções antigas do contrato (`dados/consultas.py`, que o motor usa) continuam e agora ignoram as baixas de ofício.

### Etapa 4 — decisões por regra e métricas oficiais

```bash
python -m dados.etl.decidir_parametros  # aplica as regras, grava config.yaml (seção consultas) e decisoes/DECISOES.md
python -m dados.etl.construir_db        # no fim, gera dados/METRICAS.md e dados/metricas.json
```

- [`decisoes/DECISOES.md`](decisoes/DECISOES.md): uma seção por decisão, com a regra, os números que a sustentam e o valor escolhido (período 2021 a 2025, `limiar_recuo` 50, parâmetros de lacuna). Para rever uma decisão, altere o `config.yaml` e rode `construir_db`; as funções de consulta usam esses valores por padrão.
- [`METRICAS.md`](METRICAS.md) e [`metricas.json`](metricas.json): números oficiais do recorte para o artigo. Saem só de consultas ao banco, com vírgula decimal no `.md` e ponto no `.json`, e o gerador aborta se os números forem incoerentes. Não edite à mão. O `METRICAS.md` da raiz, com as tabelas dos outros blocos, é outro arquivo e não é sobrescrito.

Referência: seções 3, 6, 7, 8 e 12 do relatório técnico.
