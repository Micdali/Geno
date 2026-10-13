# enriquecimento/ — Camada 2: do CNPJ ao site (dono: Roger)

Liga cada empresa do setor piloto ao seu site e coleta o texto das páginas.

**Objetivo até 05/11:** cada empresa possível ligada ao seu site com a evidência registrada (`candidato_dominio`), textos coletados em cache (`pagina`), **taxa de acerto medida por método** e **gabarito de 100 empresas** anotado à mão.

## Plano híbrido

O casamento automático roda, mas uma base montada à mão garante a demo. A taxa de acerto medida diz quanto precisa completar à mão, e vira resultado do artigo mesmo se for baixa.

**Primeira entrega:** 30 empresas do piloto com site achado à mão → Micael. Isso destrava a classificação por LLM.

## Métodos (em ordem de custo)

1. Domínio do e-mail (descartar gmail/hotmail e domínios que aparecem em muitos CNPJs, em geral contadores)
2. CNPJ no rodapé do site (conferir os dígitos verificadores)
3. Nome fantasia × título da página inicial
4. Manual

## Coleta responsável

- Respeitar o `robots.txt`; no máximo 1 requisição por segundo por domínio; User-Agent identificando o projeto (`GENO_USER_AGENT` no `.env`)
- Bloqueios (ex.: Cloudflare) são **registrados, não contornados**. A taxa de bloqueio é uma métrica do artigo.
- Guardar só o texto limpo, com hash para não reprocessar.

## Entradas e saídas

- Entra: `candidatos.parquet` ([contrato 2](../contratos/02_candidatos.md)). Enquanto não existir, use `contratos/exemplos/candidatos.exemplo.csv`.
- Sai: tabelas `candidato_dominio`, `pagina` e `gabarito` ([contrato 1](../contratos/01_schema.sql)); números no `METRICAS.md`.

Referência: seção 9 do relatório técnico.
