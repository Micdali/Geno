# Pedido do motor (Micael) para o enriquecimento (Roger)

> Cole este arquivo no Claude que você estiver usando, aberto na raiz do repositório `Micdali/Geno`.

## O que eu preciso

O **texto dos sites** de empresas do setor piloto, para o motor classificar com o LLM.
A classificação (público, serviço, canal etc.) **é o motor que faz**. Não precisa preencher.

## De onde tirar as empresas

- Setor piloto: **"Educação livre" no RJ** (definido pelo Lucas em `dados/config.yaml`, no branch `lucas/etl-download-cnpj`).
- Lista de empresas: `dados/parquet/candidatos.parquet` (contrato 2). O arquivo não vai para o Git: gere com o ETL do Lucas (`dados/README.md` do branch dele) ou peça o arquivo a ele.
- Comece pelas que têm `dominio_email` preenchido: o site provável já está ali.
- Inclua empresas **ativas e baixadas** (`situacao` 02 e 08). A análise de mortalidade precisa das duas.
- **Não use** empresas de fora do RJ nem tiradas de lista própria: sem o CNPJ do parquet, a empresa não se liga ao banco.

## O que entregar

Um CSV, uma linha por página coletada:

| coluna | o que é |
|---|---|
| `cnpj` | 14 dígitos, como texto, **obrigatório** (vem do parquet) |
| `site` | domínio encontrado, ex.: `escolaexemplo.com.br` |
| `metodo` | como achou o site: `email`, `rodape_cnpj`, `nome_titulo` ou `manual` |
| `url` | página coletada |
| `tipo` | `home`, `sobre` ou `precos` |
| `texto` | texto limpo da página, sem HTML (pode truncar em ~5.000 caracteres) |
| `status_http` | ex.: 200, 403 |
| `bloqueado` | `true` se caiu em Cloudflare ou similar (registrar, nunca contornar) |
| `coletado_em` | data e hora |

Salve em `enriquecimento/cache/textos_sites.csv` (fica fora do Git) e me mande o arquivo.
Se preferir, grave direto nas tabelas `candidato_dominio` e `pagina` do contrato 1 (`contratos/01_schema.sql`). Os campos são os mesmos.

## Quantidade e prazo

1. **30 empresas até 03/11**: com elas eu testo o prompt.
2. **O máximo possível até 04/11 à noite**: quanto mais empresas, melhor a busca de concorrentes e lacunas.

## Regras de coleta (já estão no `enriquecimento/README.md`)

- Respeitar o `robots.txt`; no máximo 1 requisição por segundo por domínio; User-Agent = `GENO_USER_AGENT` do `.env`.
- Só texto público do site. Nada de sócios, telefones ou e-mails pessoais.
- Confira se o site é mesmo da empresa (CNPJ no rodapé ou nome batendo). Site errado vira classificação errada.

## Depois, se der tempo

O **gabarito de 100 empresas** (tabela `gabarito` do contrato 1): você lê o site e preenche à mão público, produto/serviço, canal, problema resolvido e modelo de receita. Serve para medir a precisão do LLM no artigo. Não trava a demo.
