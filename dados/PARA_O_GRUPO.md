# Bloco de dados: o que cada pessoa precisa saber

Escrito pelo Lucas em 02/11/2026. Resumo do que o bloco `dados/` entrega e do que muda para cada um. Os detalhes técnicos estão no [`dados/README.md`](README.md); os números oficiais, em [`METRICAS.md`](METRICAS.md).

## Em cinco números

Recorte: **RJ**, setor "educação livre" (5 CNAEs, ver o [`METRICAS.md`](METRICAS.md)), competência **2026-10** da Receita.

| | |
|---|---|
| Estabelecimentos no recorte | **333.571** |
| Ativos / baixados | **52,8%** / **37,2%** |
| Mortalidade em 2 anos (coortes 2021 a 2023, sem baixas de ofício) | **27,5%** |
| Ativos com e-mail de domínio próprio (ponto de partida para achar o site) | **27.296** de 176.175 (**15,5%**) |
| Período dos eventos | **2021 a 2025** (2026 fica de fora por estar incompleto) |

## Como ter o banco na sua máquina

O `geno.duckdb` (≈ 85 MB) e os Parquet **não vão para o Git**. Duas opções:

1. **Pedir o arquivo ao Lucas** (mais rápido). Coloque em `dados/geno.duckdb`.
2. **Recriar do zero**, com o venv do projeto ativo (passos no README da raiz). Precisa de ≈ 7,1 GB de download, ≈ 17 GB livres no pico e ≈ 45 minutos:

```bash
python -m dados.etl.filtrar --baixar    # baixa e filtra a base da Receita
python -m dados.etl.candidatos          # gera candidatos.parquet
python -m dados.etl.construir_db        # monta o banco e gera METRICAS.md e metricas.json
python -m pytest tests -v               # confere o banco (LGPD, consultas, métricas)
```

> **Atenção, Roger e Micael:** `construir_db` apaga e recria o `geno.duckdb`. As tabelas das camadas 2 a 4 (`candidato_dominio`, `pagina`, `classificacao`, `gabarito`, `embedding`) ficam criadas e **vazias**, e o que vocês gravarem nelas se perde se alguém reconstruir o banco. Até combinarmos outra forma, guardem a saída de vocês também em arquivos próprios (Parquet ou CSV) fora do `geno.duckdb`, ou avisem antes de eu reconstruir.

## Christian (app)

- Use **só a `vw_publico`** para mostrar dados de empresas. É a única fonte liberada pela LGPD: ela esconde a razão social de MEI e empresário individual e não tem e-mail, telefone nem endereço detalhado. Não consulte as tabelas direto.
- As consultas prontas estão em [`geno_db/consultas.py`](geno_db/consultas.py), com exemplos e saídas reais em [`geno_db/EXEMPLOS.md`](geno_db/EXEMPLOS.md):

```python
from dados.geno_db import consultas
consultas.saturacao(["8593700"])                       # ano, aberturas, baixas, baixas_oficio, saldo, ativos_fim_ano
consultas.mortalidade_setor(["8593700"], horizonte=2)  # coortes, taxa e recuo de CNAE
```

- Os parâmetros padrão estão em [`config.yaml`](config.yaml), seção `consultas`, e as funções já os usam: período **2021 a 2025** e `limiar_recuo` **50**. Os valores de lacuna (`lacuna_max_abs = 2`, `lacuna_max_pct = 0.05`) já estão gravados, mas ainda não há função de lacuna. Os valores e a justificativa estão em [`decisoes/DECISOES.md`](decisoes/DECISOES.md).
- **Mostre o recuo na tela.** `mortalidade_setor` devolve `nivel_usado` (subclasse, classe ou grupo), `cnaes_usados` e `n_estab`. Se não for "subclasse", o nicho foi ampliado e **não é o nicho exato**. Com o limiar 50, isso acontece em 71% das combinações subclasse × município do setor; em 86 de 432 nem o grupo chega a 50 estabelecimentos, e a resposta sai com baixa confiança.
- `municipio` é o **código da Receita** (texto), não o do IBGE. A unidade é o **estabelecimento** (matriz e filiais contam separadamente).
- Texto para a tela: baixa de CNPJ **não** quer dizer que a empresa fechou, e as **baixas de ofício** (inaptidão, omissão, registro cancelado) são separadas das voluntárias.

## Micael (motor e contratos)

- O banco segue o [contrato 1](../contratos/01_schema.sql), sem alterá-lo. Acrescentei tabelas em [`sql/01_schema_extra.sql`](sql/01_schema_extra.sql) (`simples`, `pais`, `qualificacao`, `situacao_cadastral`, `motivo_classe`).
- **Mudanças em relação ao contrato** (só acrescentam colunas, mas o contrato continua "v0, aguardando aprovação"; precisam da sua conferência):
  - `vw_eventos` mantém as colunas e ganha `classe_baixa` e `baixa_em_massa`; existe também a `vw_eventos_longo`, com um evento por linha.
  - `vw_publico` mantém as colunas e ganha nome fantasia, razão social, CNAE e descrição, situação e descrição, porte, `opcao_simples` e `opcao_mei`. Também esconde nome fantasia com e-mail e, em MEI e empresário individual, o que repete o nome do titular.
- As funções antigas do contrato, em [`dados/consultas.py`](consultas.py), continuam com a mesma assinatura e agora ignoram as baixas de ofício.
- O conjunto final de atributos da classificação (**contrato 3**) segue pendente. Até lá, `classificacao` e `gabarito` mantêm os campos das duas propostas.
- Os dados de lacuna dependem da classificação. A regra já está decidida e gravada no `config.yaml`: lacuna = combinação com no máximo `max(2, 5% dos ativos do nicho)`, e só se aponta com pelo menos `limiar_recuo` ativos no nicho; abaixo disso, "dados insuficientes".

## Roger (enriquecimento)

- O arquivo de entrada é o `dados/parquet/candidatos.parquet` ([contrato 2](../contratos/02_candidatos.md)): **333.571 linhas**, com as 8 colunas do contrato (`cnpj`, `nome_fantasia`, `razao_social`, `dominio_email`, `municipio`, `uf`, `situacao`, `cnae_principal`). Peça o arquivo ao Lucas; ele não vai para o Git.
- **Todas as situações cadastrais entram**, inclusive as baixadas (o domínio do e-mail continua na base e permite buscar o site arquivado). Para a coleta atual, filtre `situacao = '02'`.
- `dominio_email` já vem **sem provedores genéricos** (gmail, hotmail e parecidos). Há **40.241** estabelecimentos com domínio, dos quais **27.296** ativos.
- **Os domínios de contador ainda não foram descartados.** Os que mais se repetem: `contabilizei.com.br` (3.733), `lafscontabilidade.com.br` (961), `id.uff.br` (704, é a UFF), `maismei.com.br` (492) e `gmail.com.br` (345, parece erro de digitação). Descarte domínios que aparecem em muitos CNPJs, como no seu plano.
- `razao_social` está no arquivo **só para busca manual** e **nunca pode ser exibida**: em MEI ela traz o nome do titular. Não há telefone nem e-mail completo no arquivo (decisão do relatório técnico).

## Mariana (artigo e docs)

- **Fonte a citar:** Receita Federal do Brasil, Dados Abertos do CNPJ, competência **2026-10** (licença CC-BY). Detalhes e limitações em [`FONTE.md`](FONTE.md).
- Números do recorte, prontos para o artigo: [`METRICAS.md`](METRICAS.md) (leitura, em português) e [`metricas.json`](metricas.json) (tabelas e gráficos). Eles são gerados do banco; **não edite à mão**. A seção "Limitações" do `METRICAS.md` pode ser citada como está.
- Regras e números por trás de cada parâmetro (período, limiar, lacuna): [`decisoes/DECISOES.md`](decisoes/DECISOES.md).
- A mortalidade calculada **não é comparável** diretamente à do IBGE e do Sebrae: a base inclui MEIs e empresas sem empregados.

## Decisões que o grupo precisa confirmar

Tudo abaixo foi decidido por regra ou proposta minha e pode ser revisto. Para trocar um parâmetro, altere o `config.yaml` e rode `construir_db`.

1. **Quais baixas contam como mortalidade.** Só as de ofício ficam de fora. A classe `outra` entra, o que inclui 355 baixas de reorganização (incorporação, troca de matriz e filial), 0,3% do total. A classificação de cada motivo está em [`sql/seeds/motivo_classe.csv`](sql/seeds/motivo_classe.csv), com justificativa.
2. **Período 2021 a 2025 e `limiar_recuo` 50.** Saíram de regras objetivas (ver o `DECISOES.md`), mas eram provisórios.
3. **Definição da mortalidade.** As baixas de ofício não entram no numerador e **não saem do denominador**.
4. **Nomes parciais do titular.** Em MEI e empresário individual, um nome fantasia que contém só parte do nome da pessoa (por exemplo, o primeiro nome) continua visível: cerca de 94% dos nomes fantasia desse grupo. Esconder mais seria mais seguro, mas esconderia nomes comerciais legítimos.
5. **As views diferem do contrato 1** (item do Micael acima).

## Onde está cada coisa

| O que | Onde |
|---|---|
| Como rodar tudo, passo a passo | [`README.md`](README.md) |
| Parâmetros (período, limiar, lacuna, CNAEs) | [`config.yaml`](config.yaml) |
| Números do recorte | [`METRICAS.md`](METRICAS.md), [`metricas.json`](metricas.json) |
| Decisões e a justificativa de cada uma | [`decisoes/DECISOES.md`](decisoes/DECISOES.md) |
| Consultas e exemplos | [`geno_db/consultas.py`](geno_db/consultas.py), [`geno_db/EXEMPLOS.md`](geno_db/EXEMPLOS.md) |
| Classe dos motivos de baixa | [`sql/seeds/motivo_classe.csv`](sql/seeds/motivo_classe.csv) |
| Origem dos dados, layout e armadilhas | [`FONTE.md`](FONTE.md) |
| Testes | `tests/` (rodar com `python -m pytest tests -v`) |

Dúvidas sobre o banco: falar com o Lucas.
