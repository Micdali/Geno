# Exemplos de uso de `dados/geno_db/consultas.py`

Saídas reais do `geno.duckdb`, geradas por `python -m dados.geno_db.gerar_exemplos` (não edite à mão). Rode
da raiz do repositório, depois de `python -m dados.etl.construir_db`. Não precisa configurar nada: o
caminho do banco, o período padrão (2021 a 2025) e o limiar de recuo (50) vêm do `dados/config.yaml`.

```python
from dados.geno_db import consultas
```

Convenções que valem para todas as funções:

- `cnaes` é uma lista de códigos como **texto**, de 3 a 7 dígitos. Um código casa por prefixo: `"8593700"` é a subclasse, `"85937"` a classe e `"859"` o grupo.
- `municipio` é o **código da Receita** (texto), não o do IBGE. `6001` é Rio de Janeiro e `5813` é Cabo Frio.
- A unidade é o estabelecimento: matriz e filiais contam separadamente.
- Por padrão só vale o CNAE principal; `usar_secundario=True` inclui quem tem o CNAE como atividade secundária.
- "De ofício" é a classe `oficio` de `dados/sql/seeds/motivo_classe.csv` (inaptidão, omissão, registro cancelado...), que inclui as baixas em massa da Receita.
- O ano corrente é parcial, então o período padrão termina em 2025.

## 1. Saturação de um nicho, com os padrões

```python
consultas.saturacao(["8593700"])
```

```
 ano  aberturas  baixas  baixas_oficio  saldo  ativos_fim_ano
2021        619     302             11    328            4718
2022        576     296              0    280            4998
2023        602     376              0    226            5224
2024        633     409              0    224            5448
2025        681     519              0    162            5610
```

`baixas` é o total de baixas do ano (pela data da situação cadastral), inclusive as de ofício, e `baixas_oficio` é a parte delas que é de ofício. Com o padrão `excluir_oficio=True`, `saldo = aberturas - (baixas - baixas_oficio)`. `ativos_fim_ano` são os estabelecimentos abertos até 31/12 e ainda não baixados nessa data (inclui inaptos e suspensos).

## 2. Um município, com atividade secundária, período maior e saldo sem excluir ofício

```python
consultas.saturacao(["8593700"], municipio="6001", ano_ini=2019, ano_fim=2025,
                    usar_secundario=True, excluir_oficio=False)
```

```
 ano  aberturas  baixas  baixas_oficio  saldo  ativos_fim_ano
2019        959     333              0    626            5168
2020        908     288              0    620            5788
2021       1103     441              2    662            6450
2022        992     505              0    487            6937
2023       1000     584              0    416            7353
2024       1003     673              0    330            7683
2025       1011     772              0    239            7922
```

Com `excluir_oficio=False`, `saldo = aberturas - baixas`. Neste recorte as baixas de ofício aparecem em 2021, que são os únicos anos em que os dois jeitos de calcular o saldo diferem.

## 3. Mortalidade por coorte, nicho grande (sem recuo)

```python
r = consultas.mortalidade_setor(["8593700"], horizonte=2)
r["dados"]
```

```
nivel_usado='subclasse'  cnaes_usados=['8593700']  n_estab=3111
 ano_coorte  abertos  baixados  baixados_oficio     taxa
       2021      619       176                0 0.284330
       2022      576       154                0 0.267361
       2023      602       179                0 0.297342
```

Cada linha é uma coorte (estabelecimentos abertos naquele ano). `baixados` conta quem foi baixado até 2 anos depois, **sem** as baixas de ofício, e `taxa = baixados / abertos`. As baixas de ofício não saem do denominador: aparecem em `baixados_oficio` só para você ver o tamanho. Só entram coortes que completaram o horizonte dentro do período (com `ano_fim=2025` e `horizonte=2`, a última é 2023).

## 4. Recuo de CNAE: um nicho pequeno com os padrões

O nicho "8599605" em Cabo Frio tem menos de 50 estabelecimentos abertos no período, então o filtro sobe pela hierarquia do CNAE (subclasse, classe, grupo) até chegar ao limiar:

```python
r = consultas.mortalidade_setor(["8599605"], municipio="5813", horizonte=2)
```

```
nivel_usado='classe'  cnaes_usados=['85996']  n_estab=866
 ano_coorte  abertos  baixados  baixados_oficio     taxa
       2021      169        48                0 0.284024
       2022      153        51                0 0.333333
       2023      163        54                0 0.331288
```

O resultado diz em `nivel_usado`, `cnaes_usados` e `n_estab` o que foi usado de fato. **Mostre isso na tela:** um nicho que recuou **não** é o nicho exato. Para ver o mesmo nicho sem recuo, passe `min_estab=1`:

```python
r = consultas.mortalidade_setor(["8599605"], municipio="5813", horizonte=2, min_estab=1)
```

```
nivel_usado='subclasse'  cnaes_usados=['8599605']  n_estab=48
 ano_coorte  abertos  baixados  baixados_oficio     taxa
       2021       10         2                0 0.200000
       2022        3         2                0 0.666667
       2023       16         2                0 0.125000
```

As coortes são pequenas e a taxa oscila muito: é por isso que existe o limiar.
