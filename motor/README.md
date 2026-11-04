# motor/ — Camadas 3 e 4: LLM e análise (dono: Micael)

Transforma o texto dos sites em campos padronizados e responde à pergunta do usuário.

**Objetivo até 05/11:** `analisar(ideia)` devolve o resultado completo (concorrentes, saturação, lacunas, diferencial e confiança) com dados reais do setor piloto, no formato do [contrato 4](../contratos/04_resultado_analise.md).

## Como rodar

```bash
# 0. Pré-requisitos: .env com LLM_PROVEDOR=openai e OPENAI_API_KEY (ou gemini e GEMINI_API_KEY);
#    dados/geno.duckdb (pedir ao Lucas);
#    enriquecimento/cache/textos_sites.csv (Roger: python -m enriquecimento.exportar_textos)
python -m motor.teste_conexao          # confere a chave e os modelos

# 1. Antes da demo (não roda ao vivo)
python -m motor.classificar --workers 6   # texto dos sites -> motor/cache/classificacao.jsonl (retomável)
                                          # com o Gemini gratuito, acrescente --rpm 13
python -m motor.embeddings             # classificação -> motor/cache/embedding.parquet (local, sem cota)

# 2. Análise de uma ideia (chama o LLM ao vivo)
python -m motor.analisar "escola de inglês online para adultos 40+"

# Testes (sem rede, sem cota, sem banco)
python -m pytest motor/tests -v
```

No app:

```python
from motor.nicho import propor_recorte     # tela 2: recorte + até 3 perguntas
from motor.analisar import analisar        # telas 4 a 6: contrato 4
r = propor_recorte(ideia)                   # r["perguntas"] = [{"pergunta", "opcoes"}]
r = propor_recorte(ideia, respostas={"pergunta": "opção escolhida"})   # depois de responder
resultado = analisar(ideia, recorte=r)
```

## Peças

| Arquivo | O que faz | LLM? |
|---|---|---|
| `classificar.py` + `prompts/classificacao_v3.md` | Texto do site → contrato 3. Retomável: só reclassifica se o prompt, o texto (`hash_texto`) ou o modelo mudar. | Sim, antes da demo |
| `embeddings.py` | Vetor de 384 dimensões de cada empresa, a partir da classificação | Não (local) |
| `nicho.py` + `prompts/nicho_v1.md` | Ideia → recorte (público, serviço, canal, CNAE) e perguntas de afunilamento | Sim, ao vivo |
| `lacunas.py` | Concorrentes por semelhança e lacunas determinísticas, com `cnpjs_base` | Não |
| `confianca.py` | Alta, média ou baixa | Não |
| `diferencial.py` + `prompts/diferencial_v1.md` | Em comum / possíveis diferenciais / não verificado | Sim, ao vivo |
| `llm.py` | OpenAI ou Gemini (`LLM_PROVEDOR`) com JSON por schema, novas tentativas e modelos de reserva | — |
| `analisar.py` | Junta tudo no contrato 4. `exemplo(ideia)` devolve o arquivo fictício, só para desenvolver o app | — |

As saídas ficam em `motor/cache/` (fora do Git), e não no `geno.duckdb`, porque o `construir_db` do Lucas apaga as tabelas das camadas 2 a 4.

## Decisões

Vindas do grupo: atributos = superconjunto v0 do contrato 3; regra de lacuna e período no `dados/config.yaml` (Lucas); análise ao vivo, sem ideias pré-calculadas.

Decisões do motor (provisórias, a calibrar com dado real; valores em `config.py`):

- **Só texto do site e a descrição do CNAE vão para o LLM.** Nome, CNPJ, sócios e contatos não.
- **Um site por CNPJ.** Quando a coleta liga vários sites ao mesmo CNPJ, fica o do método mais confiável (manual, CNPJ no rodapé, nome × título, e-mail) e, no empate, o de mais texto. Textos de sites diferentes nunca se misturam. Motivo: o domínio do e-mail da Receita muitas vezes é o do contador, e nome × título liga nomes genéricos a vários sites.
- **Site fora de ensino sai da análise.** O LLM responde também `site_de_ensino`; quando é `false` (contador, advogado, provedor, "em construção"), todos os campos viram "indeterminado" com confiança baixa, e a empresa fica sem embedding, ou seja, fora de concorrentes e lacunas. Empresas que vendem serviços e cursos juntos contam, descritas só pela parte de ensino.
- **Provedor: OpenAI desde 03/11/2026** (`LLM_PROVEDOR=openai`). Motivo: a chave do Gemini está no plano gratuito, com 15 chamadas por minuto; na primeira rodada, 93 de 204 classificações falharam por isso (429), e o `gemini-3.8-flash` deu 503/504 em 30/10 e 03/11. A chave paga da OpenAI (plano Build) aceita 5.000 chamadas por minuto: as 204 empresas levaram cerca de 2 minutos com 6 workers, por US$ 0,05. O Gemini continua funcionando como reserva: basta `LLM_PROVEDOR=gemini` no `.env`.
- **Modelos (OpenAI):** classificação `gpt-6-luna`, o modelo de alto volume da OpenAI. Ao vivo: `gpt-6-luna`, depois `gpt-5.6-luna`, depois `gpt-5.4-nano`; 2 tentativas por modelo e no máximo 15 s por chamada. Todos com `reasoning.effort = none` (`OPENAI_ESFORCO`), o mais rápido. Em 03/11/2026, `propor_recorte` levou de 1,8 a 1,9 s e `diferencial.gerar` de 2,2 a 2,4 s, em 3 ideias de teste. O schema estrito da OpenAI exige `additionalProperties: false` e todos os campos em `required`; o `llm.schema_estrito` converte, e o Gemini continua recebendo o schema original. As variáveis `LLM_MODELO_CLASSIFICACAO` e `LLM_MODELOS_AO_VIVO` no `.env` têm prioridade sobre esses padrões.
- **Modelos (Gemini, reserva):** classificação `gemini-3.5-flash-lite`. Ao vivo: `gemini-3.5-flash-lite`, depois `gemini-3.1-flash-lite`, depois `gemini-3.6-flash`. O `gemini-3.8-flash` ficou de fora: deu 503 (sobrecarga) em 30/10 e 03/11 e 504 (tempo esgotado) em 3 de 3 chamadas em 03/11/2026, enquanto os Flash-Lite responderam em menos de 2 s.
- **Moderação da OpenAI:** 1 das 204 empresas teve o texto recusado pelo filtro da OpenAI (erro 400). Não vale nova tentativa; a empresa fica com a classificação anterior (do Gemini). A comparação entre os modelos está no `METRICAS.md`.
- **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2` (384 dim, bate com o contrato 1). O vetor vem do texto da classificação (nicho, serviço, público, canal).
- **Concorrentes (calibrado em 04/11/2026):** duas condições. (1) Semelhança de cosseno ≥ 0,35 entre o texto do recorte (nicho, serviço, público, canal) e o de cada empresa; ela também dá a ordem e o número `semelhanca` da tela. (2) **Mesmo nicho:** o `produto_servico` da empresa com semelhança ≥ 0,60 ao da ideia (`SERVICO_MIN`); empresa com serviço "indeterminado" sai. Os 10 primeiros vão para a tela; todas as que passam entram nas lacunas e na confiança.
  - *Por quê:* com 602 escolas e 8 ideias de teste, o corte de 0,35 no texto inteiro deixava passar de 207 a 566 escolas (34% a 94%) para qualquer ideia. Mesmo acima de 0,65 apareciam "oficinas lúdicas" e "oratória" para inglês, porque público e canal pesam tanto quanto o serviço. Só o serviço, com corte de 0,60, deixa as listas no nicho: inglês 71 (idiomas), espanhol 30, preparatório de TI 61, liderança 66, Excel 6 (todas de Excel/BI), programação 12, informática para idosos 10, música para crianças 5. Abaixo de 0,60 entram oratória, marcenaria e vestibular. Escolha do motor (Micael), olhando as listas, não do grupo.
  - *Limite conhecido:* o modelo de embedding confunde algumas palavras ("marcenaria" ficou a 0,70 de "curso de programação"). Por isso o corte não desce de 0,60.
- **Resultado de ponta a ponta (04/11/2026, `geno.duckdb` do Lucas, 602 escolas):** as 8 ideias de teste rodaram em 3,3 a 4,7 s cada (`analisar`, com o modelo de embedding já carregado), mais ~2 s do `propor_recorte`. Confiança alta em inglês online (71 escolas) e liderança; média em concurso de TI e espanhol; baixa em música, informática para idosos, programação e Excel. **Nenhuma ideia teve lacuna:** onde há base (inglês: 59 ativas em público × serviço), a combinação não é rara (24 atendem adultos, limite 2,95); nas outras, a base fica abaixo de 50 e a tela recebe o aviso de dados insuficientes. É o comportamento esperado da regra do Lucas com esta base, não um erro.
- **Lacunas:** a combinação da ideia (público × serviço × canal) e seus pares. Uma empresa "atende" público ou serviço quando a semelhança do texto dela com o da ideia é ≥ 0,45; canal compara a lista fechada (híbrido atende presencial e online). Quem tem o campo "indeterminado" fica fora da conta daquela combinação. Só empresas ativas contam. Abaixo de 50 ativas analisadas: "dados insuficientes" (regra do Lucas).
- **Saturação:** sempre do setor (CNAEs do recorte, RJ, 2021–2025, sem baixas de ofício), porque as empresas com site são quase todas ativas e enviesariam a mortalidade. Por isso `usou_setor_amplo = true`.
- **Confiança:** alta com ≥ 50 parecidas e ≥ 70% delas com confiança do LLM alta ou média; média com ≥ 20; baixa no resto. Cai um nível se mais da metade tiver confiança baixa.

## Extras em relação ao contrato 4 (avisar o Christian)

- `propor_recorte` devolve também `cnaes` e `perguntas`.
- Cada lacuna traz `atendimento`: para cada CNPJ da base, se atende cada atributo (`true`, `false`, `null`). Serve para a tabela ✅/❌ da tela 6.
- `situacao` dos concorrentes pode ser, além de `ativa`/`baixada`, `inapta`, `suspensa` ou `nula`.
