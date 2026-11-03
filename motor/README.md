# motor/ — Camadas 3 e 4: LLM e análise (dono: Micael)

Transforma o texto dos sites em campos padronizados e responde à pergunta do usuário.

**Objetivo até 05/11:** `analisar(ideia)` devolve o resultado completo (concorrentes, saturação, lacunas, diferencial e confiança) com dados reais do setor piloto, no formato do [contrato 4](../contratos/04_resultado_analise.md).

## Como rodar

```bash
# 0. Pré-requisitos: .env com GEMINI_API_KEY; dados/geno.duckdb (pedir ao Lucas);
#    enriquecimento/cache/textos_sites.csv (Roger: python -m enriquecimento.exportar_textos)
python -m motor.teste_conexao          # confere a chave e os modelos

# 1. Antes da demo (não roda ao vivo)
python -m motor.classificar            # texto dos sites -> motor/cache/classificacao.jsonl (retomável)
python -m motor.embeddings             # classificação -> motor/cache/embedding.parquet (local, sem cota)

# 2. Análise de uma ideia (chama o Gemini ao vivo)
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
| `classificar.py` + `prompts/classificacao_v1.md` | Texto do site → contrato 3. Retomável: só reclassifica se o prompt ou o texto mudar (`hash_texto`). | Sim, antes da demo |
| `embeddings.py` | Vetor de 384 dimensões de cada empresa, a partir da classificação | Não (local) |
| `nicho.py` + `prompts/nicho_v1.md` | Ideia → recorte (público, serviço, canal, CNAE) e perguntas de afunilamento | Sim, ao vivo |
| `lacunas.py` | Concorrentes por semelhança e lacunas determinísticas, com `cnpjs_base` | Não |
| `confianca.py` | Alta, média ou baixa | Não |
| `diferencial.py` + `prompts/diferencial_v1.md` | Em comum / possíveis diferenciais / não verificado | Sim, ao vivo |
| `llm.py` | Gemini com JSON por schema, novas tentativas e modelos de reserva | — |
| `analisar.py` | Junta tudo no contrato 4. `exemplo(ideia)` devolve o arquivo fictício, só para desenvolver o app | — |

As saídas ficam em `motor/cache/` (fora do Git), e não no `geno.duckdb`, porque o `construir_db` do Lucas apaga as tabelas das camadas 2 a 4.

## Decisões

Vindas do grupo: atributos = superconjunto v0 do contrato 3; regra de lacuna e período no `dados/config.yaml` (Lucas); análise ao vivo, sem ideias pré-calculadas.

Decisões do motor (provisórias, a calibrar com dado real; valores em `config.py`):

- **Só texto do site e a descrição do CNAE vão para o LLM.** Nome, CNPJ, sócios e contatos não.
- **Modelos:** classificação `gemini-3.5-flash-lite`; ao vivo tenta `gemini-3.8-flash`, depois `gemini-3.6-flash`, depois `gemini-3.5-flash-lite`, com 2 tentativas por modelo. Os dois Flash deram 503 (sobrecarga) em 30/10 e 03/11/2026.
- **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2` (384 dim, bate com o contrato 1). O vetor vem do texto da classificação (nicho, serviço, público, canal).
- **Concorrentes:** semelhança de cosseno ≥ 0,35 entre o recorte da ideia e cada empresa classificada; os 10 primeiros vão para a tela.
- **Lacunas:** a combinação da ideia (público × serviço × canal) e seus pares. Uma empresa "atende" público ou serviço quando a semelhança do texto dela com o da ideia é ≥ 0,45; canal compara a lista fechada (híbrido atende presencial e online). Quem tem o campo "indeterminado" fica fora da conta daquela combinação. Só empresas ativas contam. Abaixo de 50 ativas analisadas: "dados insuficientes" (regra do Lucas).
- **Saturação:** sempre do setor (CNAEs do recorte, RJ, 2021–2025, sem baixas de ofício), porque as empresas com site são quase todas ativas e enviesariam a mortalidade. Por isso `usou_setor_amplo = true`.
- **Confiança:** alta com ≥ 50 parecidas e ≥ 70% delas com confiança do LLM alta ou média; média com ≥ 20; baixa no resto. Cai um nível se mais da metade tiver confiança baixa.

## Extras em relação ao contrato 4 (avisar o Christian)

- `propor_recorte` devolve também `cnaes` e `perguntas`.
- Cada lacuna traz `atendimento`: para cada CNPJ da base, se atende cada atributo (`true`, `false`, `null`). Serve para a tabela ✅/❌ da tela 6.
- `situacao` dos concorrentes pode ser, além de `ativa`/`baixada`, `inapta`, `suspensa` ou `nula`.
