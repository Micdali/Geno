# Handoff: motor do GENO com a nova chave paga da OpenAI

> Para a próxima sessão do Claude Code, aberta na raiz do repositório `Micdali/Geno` (pasta `C:\Repos Projeto IBMEC\GENO`), branch `micael/motor-llm`. Escrito em 03/11/2026.

## Contexto em 30 segundos

- GENO: trabalho do Ibmec com 5 pessoas. Recebe uma ideia de negócio e devolve concorrentes, saturação, lacunas, diferencial e confiança (contrato 4).
- **Micael é o dono de `motor/` e `contratos/`.** Mexa só nessas pastas. A exceção é a seção "Classificação por LLM — Micael" do `METRICAS.md`.
- Apresentação na **quinta, 05/11/2026**.
- Leia primeiro: [`motor/README.md`](README.md). Ele lista as peças, os comandos e as decisões.
- O pipeline: Lucas (banco da Receita) → Roger (site e texto de cada CNPJ) → Micael (LLM classifica os textos; `analisar()` responde a ideia) → Christian (telas).

## Regras que não mudam

- **A chave nunca vai para o GitHub, nunca é impressa e nunca é colada no chat.** O `.env` está no `.gitignore`. Rode `git status` antes de qualquer commit.
- Commit e push só quando o Micael pedir.
- Só texto público de site e descrição do CNAE vão para o LLM. Nome, CNPJ, sócios e contatos não (LGPD).
- Não invente números. Métrica real vai para o `METRICAS.md` com data, amostra e método. Nunca use `contratos/exemplos/` como resultado.
- Não use as palavras "validar", "abra" ou "não abra".
- A assinatura `motor.analisar(ideia, recorte=None)` não muda.
- Marque o que é sugestão sua e o que veio do grupo ou do Micael.

## Estado atual

**Mudanças sem commit na pasta de trabalho.** Se esta sessão estiver num worktree novo, elas não estão lá. Peça ao Micael para commitar antes ou trabalhe na pasta original.
- `motor/classificar.py`:
  - um site por CNPJ (prioridade manual > rodape_cnpj > nome_titulo > email, e no empate o de mais texto);
  - campo `site_de_ensino` (quando é `false`, tudo vira "indeterminado" e a confiança vai para baixa);
  - prompt v3;
  - opção `--rpm` para limitar chamadas por minuto.
- `motor/prompts/classificacao_v3.md` (arquivo novo).
- 2 testes novos em `motor/tests/test_motor.py`. São 15 testes, todos passando: `python -m pytest motor/tests -q`.
- `motor/README.md` e `METRICAS.md` atualizados.
- Ficam só locais, sem commit: `motor/PEDIDO_ROGER.md`, `motor/PEDIDO_ROGER_2.md` e este arquivo.

**Dados:**
- `docs/textos_sites_rj.csv`: entrega do Roger de 03/11. Fica fora do Git.
- `motor/cache/classificacao.jsonl`: 204 empresas classificadas com `gemini-3.5-flash-lite`, prompt v3. 94 são sites de ensino.
- `motor/cache/embedding.parquet`: 94 empresas.
- Falta o `dados/geno.duckdb` do Lucas, uns 85 MB. Sem ele, `analisar()` não roda de ponta a ponta.

**Por que trocar de chave:** a chave do Gemini está no **plano gratuito**, com limite de 15 chamadas por minuto (erro 429 `generate_content_free_tier_requests`). Na primeira rodada, 93 de 204 classificações falharam por isso. O `gemini-3.8-flash` deu 503/504 em 30/10 e 03/11.

## Tarefa 1: chave da OpenAI no `.env`

1. Acrescente ao `.env.example`, que vai para o Git, sem valor:
   ```
   OPENAI_API_KEY=
   ```
   Atualize também o comentário do `LLM_PROVEDOR` (valores: `gemini` ou `openai`) e as variáveis de modelo da Tarefa 2.
2. No `.env`, acrescente a linha `OPENAI_API_KEY=` vazia. Use edição pontual e **não imprima o conteúdo do arquivo**. Abra o `.env` no editor para o Micael (`mcp__ccd_host__open_in_editor`) e peça que ele cole a chave **ele mesmo**. Espere ele confirmar.
3. Confira só se a variável está preenchida, sem mostrar o valor. Por exemplo: `python -c "from dotenv import load_dotenv; import os; load_dotenv('.env'); print(bool(os.getenv('OPENAI_API_KEY')))"`.

## Tarefa 2: o motor usando a OpenAI

**Antes de escrever código**, consulte a documentação atual da OpenAI. Não confie na memória: modelos, preços e a API mudam. Confirme:
- quais modelos baratos servem para classificar em lote e quais são rápidos para as chamadas ao vivo;
- o preço por milhão de tokens e os limites de requisições do plano da chave;
- como pedir JSON com schema estrito (structured outputs) na versão atual do SDK `openai`.

Depois:

1. **`requirements.txt`**: acrescente `openai`.
2. **`motor/llm.py`**: hoje só fala com o Gemini. Faça `gerar_json(prompt, schema, modelos, sistema, temperatura, tentativas, timeout_s)` escolher o provedor por `LLM_PROVEDOR`, mantendo a mesma assinatura e o mesmo retorno `(dict, modelo)`. **Mantenha o caminho do Gemini funcionando**, como reserva.
   - Desligue as novas tentativas internas do SDK (`max_retries=0`) e use o `timeout_s`. Quem tenta de novo e troca de modelo é o `gerar_json`, como já acontece com o Gemini.
   - Erros temporários, que valem nova tentativa: limite de taxa (429), erro do servidor (5xx), estouro de tempo e falha de conexão. O resto sobe como erro.
   - Schema estrito na OpenAI exige `additionalProperties: false` em todos os objetos e todos os campos em `required`. Ajuste os schemas de `classificar.py`, `nicho.py` (que tem objetos aninhados) e `diferencial.py`, ou converta-os dentro do `llm.py`. Se fizer isso com um adaptador, o Gemini continua recebendo o schema original.
3. **`motor/config.py`**: os padrões de `MODELO_CLASSIFICACAO` e `MODELOS_AO_VIVO` são do Gemini. Faça os padrões dependerem do provedor e mantenha as variáveis `LLM_MODELO_CLASSIFICACAO` e `LLM_MODELOS_AO_VIVO`.
4. **`motor/teste_conexao.py`**: hoje só testa o Gemini. Faça testar o provedor configurado, sem nunca imprimir a chave.
5. **Testes**: os 15 atuais usam LLM falso e devem continuar passando. Acrescente um teste do adaptador de schema e da classificação de erro temporário, sem rede.
6. **Reclassificar com o novo modelo.** Cuidado: o `classificar.rodar` pula quem já tem a mesma `(cnpj, prompt_versao, hash_texto)`, então trocar só o modelo **não reclassifica nada**. Inclua o modelo nessa chave de retomada; é a opção mais limpa. Depois rode:
   ```
   python -m motor.classificar docs/textos_sites_rj.csv --workers 6
   python -m motor.embeddings
   ```
   O `--rpm` só é necessário se o plano tiver limite baixo.
7. **Compare os dois modelos** nas mesmas 204 empresas: quantas `site_de_ensino`, a porcentagem de "indeterminado" por campo e a distribuição de confiança. Os números do Gemini estão no `METRICAS.md`. Registre os da OpenAI com data e modelo, e o gasto na tabela "Custo".
8. Teste ao vivo `nicho.propor_recorte` e `diferencial.gerar` com uma ideia, medindo o tempo. Para a demo, cada chamada deveria levar poucos segundos.
9. Atualize o `motor/README.md`: provedor, modelos e o motivo da troca.

## Tarefa 3: pendências do motor que não dependem do Roger

Em ordem de importância:

1. **Calibrar o limiar de "mesmo nicho"** (`SEMELHANCA_MIN = 0.35` em `config.py`). Medido em 03/11, nas 94 escolas: entre 62% e 96% delas passam do limiar para qualquer ideia de teste. Para "aulas de música para crianças", as mais parecidas eram uma escola regular, um curso de idiomas e um preparatório; não há escola de música na base. O limiar mede "é uma escola", e não "é do mesmo nicho", e as lacunas saem de comparações erradas. Candidatos (sugestão, não decisão): subir o corte para perto de 0,5, ou exigir que o `produto_servico` bata, e não só o texto geral. Decida olhando as listas de algumas ideias de teste e documente no README.
2. `confianca`: o `n_setor` vem de `ativos_fim_ano`, que inclui inaptas. Deveria contar só a situação `02`.
3. Teste para o caminho sem nenhum concorrente.
4. Quando o Lucas mandar o `geno.duckdb`: rodar `python -m motor.analisar "escola de inglês online para adultos"` de ponta a ponta.
5. PR do contrato 4 com os extras para o Christian (estão em "Extras" no README do motor).
6. [Micdali/Geno#7](https://github.com/Micdali/Geno/pull/7) (contrato 1, colunas das visões) está esperando o OK do Lucas.

## Tarefa 4: quando os lotes do Roger chegarem

O Roger recebeu o `PEDIDO_ROGER_2.md` e deve mandar em lotes (`textos_sites_rj_2.csv`, `_3`…), no mesmo formato, com:
- filtro de domínios de contador;
- um site por CNPJ;
- fila começando pelas empresas ativas com CNAE principal do piloto.

A meta é chegar a 500 sites de ensino primeiro e, se der tempo, 1.000. Para chegar a qualquer número de lacuna, o motor precisa de pelo menos 50 empresas ativas do mesmo nicho (`limiar_recuo` em `dados/config.yaml`).

Para cada lote:
1. Peça ao Micael que salve o arquivo em `docs/` e **não commite** (é pasta da Mariana e o arquivo tem dado coletado).
2. Rode `python -m motor.classificar docs/textos_sites_rj_N.csv` e depois `python -m motor.embeddings`. É retomável: só classifica o que é novo.
3. Meça e conte ao Micael:
   - empresas com texto útil;
   - quantas são `site_de_ensino`, por método;
   - CNPJs repetidos entre lotes;
   - o total acumulado de escolas.
4. Refaça a calibração do limiar com a base maior e veja quantas escolas do mesmo nicho cada ideia de teste alcança.
5. Atualize o `METRICAS.md`.

A "conferência rápida" que o Roger deve mandar junto com cada lote é: nenhum CNPJ com mais de um site, e pelo menos 80% das páginas iniciais com palavras de ensino. Se um lote vier bem abaixo disso, avise o Micael antes de gastar chamadas classificando.
