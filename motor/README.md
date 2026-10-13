# motor/ — Camadas 3 e 4: LLM e análise (dono: Micael)

Transforma o texto dos sites em campos padronizados e responde à pergunta do usuário.

**Objetivo até 05/11:** `analisar(ideia)` devolve o resultado completo (concorrentes, saturação, lacunas, diferencial e confiança) com dados reais do setor piloto, no formato do [contrato 4](../contratos/04_resultado_analise.md).

## Partes

- **Classificação:** prompt versionado; saída no [contrato 3](../contratos/03_classificacao.schema.json); `indeterminado` quando o site é vago; execução retomável; só reclassifica se o prompt ou o texto mudar.
- **Embeddings:** sentence-transformers (384 dimensões), gravados na tabela `embedding`.
- **Ideia → nicho:** propõe o recorte, faz até 2 ou 3 perguntas de afunilamento e aceita "analisar assim mesmo".
- **Lacunas:** combinações de atributos que quase ninguém oferece, com a lista das empresas que embasam a conclusão.
- **Confiança:** alta, média ou baixa (seção 10.3 do relatório).

## Estado atual

`analisar.py` devolve o arquivo de exemplo. Com isso o app já funciona de ponta a ponta desde o primeiro dia. As partes reais vão substituindo o exemplo sem mudar a assinatura.
