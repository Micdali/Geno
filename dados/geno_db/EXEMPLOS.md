# Exemplos de uso de `dados/geno_db/consultas.py`

Saídas reais do `geno.duckdb` (competência 2026-10, RJ, educação livre). Rode da raiz do repositório,
depois de `python -m dados.etl.construir_db`. Não precisa configurar nada: o caminho do banco, o
período padrão (2021 a 2025) e o limiar de recuo (30) vêm do `dados/config.yaml`.

```python
from dados.geno_db import consultas
```

Convenções que valem para todas as funções:

- `cnaes` é uma lista de códigos como **texto**, de 3 a 7 dígitos. Um código casa por prefixo: `"8593700"` é a subclasse, `"85937"` a classe e `"859"` o grupo.
- `municipio` é o **código da Receita** (texto), não o do IBGE. `6001` é Rio De Janeiro.
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

`baixas` é o total de baixas do ano (pela data da situação cadastral), inclusive as de ofício, e `baixas_oficio` é a parte delas que é de ofício. Com o padrão `excluir_oficio=True`, `saldo = aberturas - (baixas - baixas_oficio)`. `ativos_fim_ano` são os estabelecimentos abertos até 31/12 e não baixados até essa data.

## 2. Um município, com atividade secundária, período e saldo sem excluir ofício

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

Com `excluir_oficio=False`, `saldo = aberturas - baixas`. Neste recorte só 2021 tem baixas de ofício (2), então é o único ano em que os dois jeitos de calcular o saldo diferem (662 aqui, 664 com o padrão `excluir_oficio=True`).

## 3. Mortalidade por coorte, com recuo de CNAE

```python
r = consultas.mortalidade_setor(["8599699"], municipio="6001", horizonte=2)
r["dados"]
```

```
nivel_usado='subclasse'  cnaes_usados=['8599699']  n_estab=20115
 ano_coorte  abertos  baixados  baixados_oficio     taxa
       2021     3880      1048                0 0.270103
       2022     3704      1205                0 0.325324
       2023     3805      1304                0 0.342707
```

Cada linha é uma coorte (estabelecimentos abertos naquele ano). `baixados` conta quem foi baixado até 2 anos depois, **sem** as baixas de ofício, e `taxa = baixados / abertos`. As baixas de ofício não saem do denominador: aparecem em `baixados_oficio` só para você ver o tamanho. Só entram coortes que completaram o horizonte dentro do período (com `ano_fim=2025` e `horizonte=2`, a última é 2023).

Se o nicho tiver menos estabelecimentos que `min_estab` (padrão 30, contados entre os abertos no período), o filtro sobe pela hierarquia do CNAE: subclasse (7 dígitos), classe (5), grupo (3). O resultado diz em `nivel_usado` e `cnaes_usados` o que foi usado de fato, e em `n_estab` quantos estabelecimentos o nicho tem nesse nível. Mostre isso na tela: um nicho que recuou para o grupo **não** é o nicho exato.

Para ver o recuo acontecer, force um limiar alto:

```python
r = consultas.mortalidade_setor(["8593700"], min_estab=100_000)
```

```
nivel_usado='grupo'  cnaes_usados=['859']  n_estab=80090
```

E sem recuo, com um período maior (a coorte 2018 já completou 2 anos):

```python
r = consultas.mortalidade_setor(["8593700"], horizonte=2, ano_ini=2018, ano_fim=2025)
r["dados"]
```

```
nivel_usado='subclasse'  cnaes_usados=['8593700']  n_estab=4628
 ano_coorte  abertos  baixados  baixados_oficio     taxa
       2018      429        95                0 0.221445
       2019      549       122                0 0.222222
       2020      539       129                0 0.239332
       2021      619       176                0 0.284330
       2022      576       154                0 0.267361
       2023      602       179                0 0.297342
```
