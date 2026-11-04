# Contrato 4 — `resultado_analise` (motor → app)

**Status:** v1 (04/11/2026), com os extras que o motor real devolve. Aguardando aprovação do Christian.

É o que a função `motor.analisar(ideia, ...)` devolve e o que o app desenha nas telas 4, 5 e 6. O Christian constrói as telas em cima de [`exemplos/resultado_analise.exemplo.json`](exemplos/resultado_analise.exemplo.json) desde o primeiro dia. Quando o motor real ficar pronto, só a origem dos dados muda.

## Formato

```text
{
  "ideia":   texto original digitado pelo usuário
  "recorte": o nicho confirmado na tela 2
      { "descricao", "atributos": {publico, produto_servico, canal}, "uf" (ou null = nacional) }
  "confianca":
      { "nivel": "alta"|"media"|"baixa",
        "n_empresas",                    # estabelecimentos ATIVOS (situação 02) do setor no recorte
        "n_com_site_classificado",       # empresas do mesmo nicho analisadas (base das lacunas)
        "usou_setor_amplo": bool,        # mortalidade calculada no setor todo, não no nicho
        "texto": frase exibida ao usuário }
  "concorrentes": lista, ordenada por semelhança
      { "cnpj", "nome_exibicao", "o_que_oferece", "publico", "canal",
        "situacao": "ativa"|"baixada"|"inapta"|"suspensa"|"nula", "ano_baixa", "semelhanca": 0..1, "site" }
  "saturacao":
      { "anos": [...], "aberturas": [...], "baixas": [...],
        "total_aberturas", "total_baixas", "fonte" }
  "lacunas": lista, a mais forte primeiro
      { "titulo", "atributos": {...}, "n_empresas_que_oferecem",
        "n_empresas_analisadas", "cnpjs_base": [...],    # empresas que embasam a conclusão
        "atendimento": { cnpj: {atributo: true|false|null} } }   # extra v1: tabela ✅/❌ da tela 6
  "diferencial":
      { "em_comum", "possiveis_diferenciais", "nao_verificado" }
  "gerado_em": data-hora
}
```

## Extras da v1 (04/11/2026)

Tudo o que a v0 tinha continua igual; o app pode ignorar os extras.

- `concorrentes[].situacao` também pode ser `inapta`, `suspensa` ou `nula` (vêm da Receita).
- `lacunas[].atendimento`: para cada CNPJ de `cnpjs_base`, se a empresa atende cada atributo da combinação. `null` = o site não diz.
- `confianca.n_empresas` conta só estabelecimentos ativos (situação 02) com o CNAE principal do recorte.
- `concorrentes` pode vir vazio e `lacunas` também: nesse caso `confianca.texto` explica que os dados são insuficientes, e `diferencial` traz um texto fixo, sem LLM.
- Tela 2 (fora deste contrato): `motor.nicho.propor_recorte(ideia, respostas=None)` devolve `{descricao, atributos, uf, cnaes, perguntas: [{pergunta, opcoes}]}`. Passe o resultado como `recorte` para `analisar`.

## Regras

- Nunca incluir razão social de MEI nem dados de sócios: nomes vêm de `vw_publico`.
- `cnpjs_base` é obrigatório em cada lacuna: o produto mostra as empresas que sustentam a conclusão.
- O produto só afirma o que o dado sustenta. Nada de "abra" ou "não abra".
