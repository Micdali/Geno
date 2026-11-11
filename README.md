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

O repositório traz o banco `dados/geno.duckdb` e o cache do motor (`motor/cache/`). O `.env` com a chave da OpenAI **não** vem no repositório: copie o `.env.example` para `.env` e cole a sua chave (o `.env` fica só na sua máquina, nunca commitado).

**Sem chave, o app também roda**, em modo reduzido: a pessoa descreve o recorte à mão na tela 2 (sem as perguntas do LLM), e a análise mostra concorrentes, saturação e lacunas da ideia, mas não as variações nem o resumo do diferencial.

```bash
# 1. Ambiente (Python 3.11 ou mais novo; testado no 3.14)
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

# 2. O app (abre em http://localhost:8501)
streamlit run app/app.py
```

- A primeira abertura leva uns 20 segundos ("Preparando o Geno"): é o modelo de embedding carregando. Depois cada análise leva de 5 a 15 segundos.
- O Geno só analisa ensino e treinamento no estado do Rio de Janeiro (piloto). Ideias de outro ramo recebem um aviso.
- Testes, sem rede: `python -m pytest app motor/tests -q`.

## Dados e privacidade

- Os arquivos brutos da Receita não vão para o Git. O banco já pronto (`dados/geno.duckdb`) e o cache do motor vão, para o app rodar logo depois do clone; o banco pode ser recriado com o script de `dados/`.
- Dados de sócios não são carregados. Razão social de MEI não é exibida (LGPD).
- Fonte: Receita Federal do Brasil — Dados Abertos do CNPJ, licença CC-BY.

Como trabalhar em grupo neste repositório: ver [`CONTRIBUTING.md`](CONTRIBUTING.md).
