# Como trabalhar neste repositório

## Regra principal

Cada pessoa mexe **só na própria pasta**. Assim ninguém trava ninguém e quase não há conflito de Git.

| Pessoa | Pasta |
|---|---|
| Lucas | `dados/` |
| Roger | `enriquecimento/` |
| Micael | `motor/` e `contratos/` |
| Christian | `app/` |
| Mariana | `docs/` |

Precisa de algo de outro bloco? Use o que o **contrato** promete (`contratos/`) e, enquanto não estiver pronto, use os arquivos de `contratos/exemplos/`.

## Mudou um contrato? Avise antes.

Arquivos em `contratos/` são o que liga os blocos. Uma mudança ali quebra o trabalho de outra pessoa. Para mudar:

1. Abra um Pull Request só com a mudança do contrato.
2. Avise no grupo quem é afetado.
3. Só faça o merge depois de essa pessoa concordar.

## Fluxo do dia a dia

```bash
git checkout main
git pull                                  # pega o que os outros subiram
git checkout -b lucas/etl-estabelecimentos  # um branch por tarefa: <nome>/<assunto>

# ... trabalha ...

git add dados/
git commit -m "dados: filtro por UF e CNAE no ETL"
git push -u origin lucas/etl-estabelecimentos
```

Depois, no GitHub, abra um **Pull Request** para `main`. Se só mexeu na sua pasta, pode fazer o merge você mesmo. Se mexeu em `contratos/` ou em pasta de outra pessoa, peça revisão a ela.

## O que nunca sobe para o Git

- `.env` (chaves de API) — use o `.env.example` como modelo
- Arquivos da Receita (`.zip`, `.csv`), Parquet e `geno.duckdb`
- Cache de páginas coletadas

O `.gitignore` já cuida disso. Se o `git status` mostrar um arquivo grande de dados, **não** faça o commit.

## Mensagens de commit

Comece pelo nome do bloco: `dados: ...`, `enriquecimento: ...`, `motor: ...`, `app: ...`, `docs: ...`, `contratos: ...`.

## Métricas

Mediu algo que vai para o artigo (taxa de acerto, precisão, nº de empresas)? Registre em `METRICAS.md` com data e como mediu.
