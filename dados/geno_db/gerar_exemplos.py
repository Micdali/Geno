"""Regenera dados/geno_db/EXEMPLOS.md rodando as consultas de verdade (dono: Lucas).

As saídas do guia vêm do banco, e o limiar de recuo e o período vêm do config.yaml: nada é digitado à
mão. Rode de novo sempre que o banco, o config.yaml ou as consultas mudarem:

    python -m dados.geno_db.gerar_exemplos
"""
from __future__ import annotations

import sys

from dados.etl.formato import nome_proprio
from dados.geno_db import consultas

DESTINO = consultas.RAIZ / "dados" / "geno_db" / "EXEMPLOS.md"
CNAE = "8593700"          # ensino de idiomas
CNAE_RECUO = "8599605"    # cursos preparatórios: bom para mostrar o recuo em municípios menores


def tab(df) -> str:
    return df.to_string(index=False)


def meta(r: dict) -> str:
    return f"nivel_usado={r['nivel_usado']!r}  cnaes_usados={r['cnaes_usados']}  n_estab={r['n_estab']}"


def municipio_maior(con) -> tuple[str, str]:
    """Município com mais estabelecimentos do CNAE de exemplo."""
    return con.execute("""SELECT e.municipio_cod, m.descricao FROM estabelecimento e
                          JOIN municipio m ON m.codigo = e.municipio_cod WHERE e.cnae_principal = ?
                          GROUP BY 1, 2 ORDER BY count(*) DESC, 1 LIMIT 1""", [CNAE]).fetchone()


def municipio_com_recuo(con, limiar: int, ini: int, fim: int) -> tuple[str, str]:
    """Município onde o CNAE de exemplo recua para a classe: tem entre 20% e 100% do limiar na subclasse.

    Escolha determinística: o de maior contagem na subclasse entre os que ficam abaixo do limiar
    mas cuja classe chega a ele (desempate pelo código).
    """
    return con.execute("""
        WITH t AS (SELECT cnae_principal c, municipio_cod m FROM estabelecimento WHERE year(data_inicio) BETWEEN ? AND ?),
        sub AS (SELECT m, count(*) n7 FROM t WHERE c = ? GROUP BY 1),
        cla AS (SELECT m, count(*) n5 FROM t WHERE left(c, 5) = left(?, 5) GROUP BY 1)
        SELECT sub.m, mu.descricao FROM sub JOIN cla USING (m) JOIN municipio mu ON mu.codigo = sub.m
        WHERE sub.n7 < ? AND cla.n5 >= ? AND sub.n7 >= ?
        ORDER BY sub.n7 DESC, sub.m LIMIT 1""", [ini, fim, CNAE_RECUO, CNAE_RECUO, limiar, limiar, max(1, limiar // 5)]).fetchone()


def gerar() -> str:
    cfg = consultas._config()["consultas"]
    limiar, (ini, fim) = int(cfg["limiar_recuo"]), cfg["periodo"]
    con = consultas.conectar()
    try:
        mun, nome = municipio_maior(con)
        mun_r, nome_r = municipio_com_recuo(con, limiar, ini, fim)
    finally:
        con.close()
    nome, nome_r = nome_proprio(nome), nome_proprio(nome_r)
    e1 = consultas.saturacao([CNAE])
    e2 = consultas.saturacao([CNAE], municipio=mun, ano_ini=ini - 2, ano_fim=fim, usar_secundario=True, excluir_oficio=False)
    r3 = consultas.mortalidade_setor([CNAE], horizonte=2)
    r4 = consultas.mortalidade_setor([CNAE_RECUO], municipio=mun_r, horizonte=2)
    r5 = consultas.mortalidade_setor([CNAE_RECUO], municipio=mun_r, horizonte=2, min_estab=1)
    # primeiro ano em que as duas formas de saldo divergem, para o texto do exemplo 2
    dif = e2.assign(oficio=e2["baixas_oficio"]).query("oficio > 0")
    frase_saldo = (f"Neste recorte as baixas de ofício aparecem em {', '.join(str(a) for a in dif['ano'])}, que são os únicos anos "
                   "em que os dois jeitos de calcular o saldo diferem." if len(dif) else
                   "Neste recorte não há baixas de ofício no período, então os dois jeitos de calcular o saldo dão o mesmo resultado.")

    return f'''# Exemplos de uso de `dados/geno_db/consultas.py`

Saídas reais do `geno.duckdb`, geradas por `python -m dados.geno_db.gerar_exemplos` (não edite à mão). Rode
da raiz do repositório, depois de `python -m dados.etl.construir_db`. Não precisa configurar nada: o
caminho do banco, o período padrão ({ini} a {fim}) e o limiar de recuo ({limiar}) vêm do `dados/config.yaml`.

```python
from dados.geno_db import consultas
```

Convenções que valem para todas as funções:

- `cnaes` é uma lista de códigos como **texto**, de 3 a 7 dígitos. Um código casa por prefixo: `"8593700"` é a subclasse, `"85937"` a classe e `"859"` o grupo.
- `municipio` é o **código da Receita** (texto), não o do IBGE. `{mun}` é {nome} e `{mun_r}` é {nome_r}.
- A unidade é o estabelecimento: matriz e filiais contam separadamente.
- Por padrão só vale o CNAE principal; `usar_secundario=True` inclui quem tem o CNAE como atividade secundária.
- "De ofício" é a classe `oficio` de `dados/sql/seeds/motivo_classe.csv` (inaptidão, omissão, registro cancelado...), que inclui as baixas em massa da Receita.
- O ano corrente é parcial, então o período padrão termina em {fim}.

## 1. Saturação de um nicho, com os padrões

```python
consultas.saturacao(["{CNAE}"])
```

```
{tab(e1)}
```

`baixas` é o total de baixas do ano (pela data da situação cadastral), inclusive as de ofício, e `baixas_oficio` é a parte delas que é de ofício. Com o padrão `excluir_oficio=True`, `saldo = aberturas - (baixas - baixas_oficio)`. `ativos_fim_ano` são os estabelecimentos abertos até 31/12 e ainda não baixados nessa data (inclui inaptos e suspensos).

## 2. Um município, com atividade secundária, período maior e saldo sem excluir ofício

```python
consultas.saturacao(["{CNAE}"], municipio="{mun}", ano_ini={ini - 2}, ano_fim={fim},
                    usar_secundario=True, excluir_oficio=False)
```

```
{tab(e2)}
```

Com `excluir_oficio=False`, `saldo = aberturas - baixas`. {frase_saldo}

## 3. Mortalidade por coorte, nicho grande (sem recuo)

```python
r = consultas.mortalidade_setor(["{CNAE}"], horizonte=2)
r["dados"]
```

```
{meta(r3)}
{tab(r3['dados'])}
```

Cada linha é uma coorte (estabelecimentos abertos naquele ano). `baixados` conta quem foi baixado até 2 anos depois, **sem** as baixas de ofício, e `taxa = baixados / abertos`. As baixas de ofício não saem do denominador: aparecem em `baixados_oficio` só para você ver o tamanho. Só entram coortes que completaram o horizonte dentro do período (com `ano_fim={fim}` e `horizonte=2`, a última é {fim - 2}).

## 4. Recuo de CNAE: um nicho pequeno com os padrões

O nicho "{CNAE_RECUO}" em {nome_r} tem menos de {limiar} estabelecimentos abertos no período, então o filtro sobe pela hierarquia do CNAE (subclasse, classe, grupo) até chegar ao limiar:

```python
r = consultas.mortalidade_setor(["{CNAE_RECUO}"], municipio="{mun_r}", horizonte=2)
```

```
{meta(r4)}
{tab(r4['dados'])}
```

O resultado diz em `nivel_usado`, `cnaes_usados` e `n_estab` o que foi usado de fato. **Mostre isso na tela:** um nicho que recuou **não** é o nicho exato. Para ver o mesmo nicho sem recuo, passe `min_estab=1`:

```python
r = consultas.mortalidade_setor(["{CNAE_RECUO}"], municipio="{mun_r}", horizonte=2, min_estab=1)
```

```
{meta(r5)}
{tab(r5['dados'])}
```

As coortes são pequenas e a taxa oscila muito: é por isso que existe o limiar.
'''


if __name__ == "__main__":
    DESTINO.write_text(gerar(), encoding="utf-8")
    print(f"OK: {DESTINO.relative_to(consultas.RAIZ)}")
    sys.exit(0)
