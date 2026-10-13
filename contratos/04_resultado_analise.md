# Contrato 4 — `resultado_analise` (motor → app)

**Status:** v0, aguardando aprovação.

É o que a função `motor.analisar(ideia, ...)` devolve e o que o app desenha nas telas 4, 5 e 6. O Christian constrói as telas em cima de [`exemplos/resultado_analise.exemplo.json`](exemplos/resultado_analise.exemplo.json) desde o primeiro dia. Quando o motor real ficar pronto, só a origem dos dados muda.

## Formato

```text
{
  "ideia":   texto original digitado pelo usuário
  "recorte": o nicho confirmado na tela 2
      { "descricao", "atributos": {publico, produto_servico, canal}, "uf" (ou null = nacional) }
  "confianca":
      { "nivel": "alta"|"media"|"baixa",
        "n_empresas", "n_com_site_classificado",
        "usou_setor_amplo": bool,        # mortalidade calculada no setor todo, não no nicho
        "texto": frase exibida ao usuário }
  "concorrentes": lista, ordenada por semelhança
      { "cnpj", "nome_exibicao", "o_que_oferece", "publico", "canal",
        "situacao": "ativa"|"baixada", "ano_baixa", "semelhanca": 0..1, "site" }
  "saturacao":
      { "anos": [...], "aberturas": [...], "baixas": [...],
        "total_aberturas", "total_baixas", "fonte" }
  "lacunas": lista, a mais forte primeiro
      { "titulo", "atributos": {...}, "n_empresas_que_oferecem",
        "n_empresas_analisadas", "cnpjs_base": [...] }   # empresas que embasam a conclusão
  "diferencial":
      { "em_comum", "possiveis_diferenciais", "nao_verificado" }
  "gerado_em": data-hora
}
```

## Regras

- Nunca incluir razão social de MEI nem dados de sócios: nomes vêm de `vw_publico`.
- `cnpjs_base` é obrigatório em cada lacuna: o produto mostra as empresas que sustentam a conclusão.
- O produto só afirma o que o dado sustenta. Nada de "abra" ou "não abra".
