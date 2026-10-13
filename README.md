# GENO — o mercado da sua ideia

> **Não é o mercado do seu negócio. É o mercado da sua ideia.**

O GENO recebe a descrição de uma ideia de negócio em texto livre e devolve uma análise de mercado do nicho correspondente:

1. **Concorrentes** — quem já faz algo parecido e o que cada um oferece
2. **Saturação e mortalidade** — quantas empresas abriram e quantas fecharam no recorte
3. **Lacunas** — combinações de público, serviço e canal que quase ninguém atende

A base vem dos **Dados Abertos do CNPJ** (Receita Federal), enriquecida com a **coleta dos sites** das empresas e **classificada por LLM**.

Trabalho da disciplina *Programação para Análise de Dados* (Ibmec, 2026.2).
Integrantes: Christian Werneck, Lucas Alcantara, Mariana Nogueira, Micael Dali, Roger Pires.

---

## Estrutura do repositório

Cada pasta é um bloco com **um dono**. Os blocos só se comunicam pelos contratos em `contratos/`.

| Pasta | O que tem | Dono |
|---|---|---|
| `contratos/` | Formatos que ligam os blocos (schema do banco, JSONs, exemplos) | Micael (mudanças passam pelo grupo) |
| `dados/` | ETL da base CNPJ → `geno.duckdb`, visões e consultas (camada 1) | Lucas |
| `enriquecimento/` | Casamento CNPJ ↔ site, coleta das páginas, gabarito (camada 2) | Roger |
| `motor/` | Classificação por LLM, embeddings, análise da ideia (camadas 3 e 4) | Micael |
| `app/` | As 6 telas do produto | Christian |
| `docs/` | Artigo, roteiro do vídeo, tema e textos da interface | Mariana |
| `METRICAS.md` | Números reais medidos por cada bloco (usados no artigo) | Todos |

## Como rodar

> Em construção. Cada bloco documenta seus comandos no próprio README.

```bash
# 1. Ambiente
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Chaves de API
copy .env.example .env         # Linux/Mac: cp .env.example .env  — depois preencha

# 3. Protótipo das telas (dados de exemplo)
streamlit run app/prototipo/app.py
```

## Dados e privacidade

- Os arquivos da Receita, o `geno.duckdb` e os Parquet **não vão para o Git** (ver `.gitignore`). Cada um recria o banco localmente com o script de `dados/`.
- Dados de sócios não são carregados. Razão social de MEI não é exibida (LGPD).
- Fonte: Receita Federal do Brasil — Dados Abertos do CNPJ, licença CC-BY.

Como trabalhar em grupo neste repositório: ver [`CONTRIBUTING.md`](CONTRIBUTING.md).
