# Camada 2 — Enriquecimento (Roger): como rodar

Liga cada empresa ao seu site (3 métodos), coleta as páginas de forma responsável e
mede o resultado. Tudo grava no `geno.duckdb` (contrato 1).

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r enriquecimento/requirements.txt
# coleta responsável: defina um contato real no .env
echo 'GENO_USER_AGENT="GENO-pesquisa/0.1 (+contato: seu-email)"' >> .env
```

## Peças
| módulo | o que faz | tabela |
|---|---|---|
| `io_contratos.py` | lê candidatos (parquet do Lucas; senão o exemplo do contrato) e cria as tabelas | — |
| `metodo1_email.py` | domínio do e-mail (descarta provedor e domínio de contador) | candidato_dominio |
| `coletor.py` | crawler: robots.txt, 1 req/s, cache, hash, registra bloqueio | pagina |
| `metodo2_rodape.py` | CNPJ no rodapé (com dígito verificador, inclui CNPJ alfanumérico) | candidato_dominio |
| `metodo3_nome_titulo.py` | nome fantasia × título da home (rapidfuzz) | candidato_dominio |
| `pipeline.py` | roda tudo em ordem + consolida melhor domínio por CNPJ | — |
| `metricas.py` | cobertura, taxa de bloqueio, exposição de CNPJ, acurácia M3 → `METRICAS.md` | — |
| `gabarito.py` | carrega empresas anotadas à mão (campos do contrato 3) | gabarito |
| `cnpj.py` | validação (inclui CNPJ alfanumérico) e extração de CNPJ | — |

## Rodar
```bash
# pipeline completo: usa dados/parquet/candidatos.parquet (Lucas) quando existir;
# senão, contratos/exemplos/candidatos.exemplo.csv
python -m enriquecimento.pipeline

# ou apontando um CSV/parquet específico:
python -m enriquecimento.pipeline caminho/para/candidatos.csv

# métricas da rodada atual (gera enriquecimento/METRICAS.md):
python -m enriquecimento.metricas caminho/para/candidatos.csv

# carregar o gabarito (CSV com os campos do contrato 3) na tabela gabarito:
python -m enriquecimento.gabarito caminho/para/empresas_anotadas.csv

# exportar o CSV de textos dos sites para o motor (Micael):
python -m enriquecimento.exportar_textos      # -> enriquecimento/cache/textos_sites.csv
```

## Entrega para o motor (Micael)
`exportar_textos.py` gera `enriquecimento/cache/textos_sites.csv` (fora do Git), uma linha
por página coletada: `cnpj, site, metodo, url, tipo, texto` (truncado em ~5.000),
`status_http, bloqueado, coletado_em`. O `cnpj` vem do `candidatos.parquet` do Lucas —
por isso a entrega do piloto depende desse arquivo (recorte RJ).

## Entrada e saída
- **Entra:** `candidatos.parquet` (contrato 2, do Lucas — recorte do piloto, UF = RJ).
  Enquanto não roda o ETL do Lucas, usa `contratos/exemplos/candidatos.exemplo.csv`.
- **Sai:** tabelas `candidato_dominio`, `pagina`, `gabarito` no `geno.duckdb`.
- **Métricas:** `metricas.py` escreve `enriquecimento/METRICAS.md`. Os números oficiais do
  piloto devem ser copiados para o `METRICAS.md` da raiz (tabela "Associação CNPJ ↔ site — Roger").

> Validado numa rodada de demonstração sobre 57 empresas reais do setor (fora do piloto RJ):
> coletor e os 3 métodos funcionando, Método 3 com alta precisão e taxa de bloqueio medida.
> Os números definitivos saem ao rodar sobre o `candidatos.parquet` real.
