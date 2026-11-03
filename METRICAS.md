# Métricas do GENO

Números reais medidos durante o desenvolvimento. É daqui que o artigo tira os resultados — **não invente nem arredonde para melhor**. Para cada número, registre a data, o tamanho da amostra e como foi medido.

## Recorte da base — Lucas

> Números oficiais e atualizados do recorte: [`dados/METRICAS.md`](dados/METRICAS.md) (e `dados/metricas.json`), gerados do banco a cada `construir_db`. A tabela abaixo é o registro de 29 e 30/10/2026.

| Métrica | Valor | Data | Como foi medido |
|---|---|---|---|
| Competência da Receita utilizada | 2026-10 (arquivos de 13/10/2026) | 29/10/2026 | Pasta mais recente do repositório da Receita; ver `dados/FONTE.md` |
| Setor piloto (CNAEs) e recorte geográfico | "Educação livre", UF = RJ; CNAE principal ou secundário em 8593700, 8599604, 8599699, 8599603, 8599605 | 29/10/2026 | `dados/config.yaml`; filtro sem data, todas as situações cadastrais |
| Nº de estabelecimentos no recorte | 333.571 (329.038 raízes de CNPJ) | 29/10/2026 | `python -m dados.etl.validar`; 73,8 M de estabelecimentos lidos no Brasil, conferidos contra a contagem do CSV (0 divergências) |
| % ativas / % baixadas | 52,8% ativas (176.175) / 37,2% baixadas (123.927); inaptas 9,8%, suspensas 0,2%, nulas 0,1% | 29/10/2026 | `python -m dados.etl.validar`, por `situacao_cadastral` |
| Entraram só pelo CNAE secundário | 165.011 (49,5%) | 29/10/2026 | Principal fora dos 5 CNAEs do setor |
| Ativos com `dominio_email` (site provável) | 27.296 de 176.175 (15,5%); baixados 9.581 de 123.927 (7,7%) | 29/10/2026 | Domínio do e-mail, sem provedores genéricos; ainda sem descartar domínios de contadores |
| Baixas por classe de motivo (123.927 baixadas) | voluntária 113.603 (91,7%); de ofício 8.573 (6,9%); outra 1.751 (1,4%) | 02/11/2026 | `vw_eventos.classe_baixa`; seed `dados/sql/seeds/motivo_classe.csv` |
| Baixas em massa (de ofício, num único dia) | 01/02/2018: 6.971 (motivo 67, 99,2% do motivo); 31/12/2008: 962 (motivo 71, 100%); 09/02/2015: 521 (motivo 73, 100%) | 02/11/2026 | Maiores datas de baixa em `vw_eventos_longo`; o motivo é o critério e a data confirma |

## Associação CNPJ ↔ site — Roger

| Método | Cobertura (% com candidato) | Precisão (% correta na amostra) | Amostra | Data |
|---|---|---|---|---|
| Domínio do e-mail | | | | |
| CNPJ no rodapé | | | | |
| Nome × título | | | | |
| Manual | | | | |

| Coleta | Valor | Data |
|---|---|---|
| % de sites acessados | | |
| % de sites bloqueados | | |

## Classificação por LLM — Micael

| Campo | Precisão vs. gabarito (100 empresas) | % indeterminado, `gemini-3.5-flash-lite` | % indeterminado, `gpt-6-luna` |
|---|---|---|---|
| publico_atendido | | 8,5% (8 de 94) | 6,7% (7 de 104) |
| produto_servico | | 0,0% (0 de 94) | 3,8% (4 de 104) |
| problema_resolvido | | 5,3% (5 de 94) | 10,6% (11 de 104) |
| posicionamento | | 19,1% (18 de 94) | 10,6% (11 de 104) |
| descricao_nicho | | 1,1% (1 de 94) | 5,8% (6 de 104) |
| canal_atendimento | | 19,1% (18 de 94) | 40,4% (42 de 104) |
| modelo_receita | | 72,3% (68 de 94) | 92,3% (96 de 104) |

% indeterminado: 03/11/2026, prompt `classificacao_v3`, `gemini-3.5-flash-lite`, temperatura 0, sobre as 94 empresas que o LLM julgou site de ensino. Entrada: `docs/textos_sites_rj.csv` do Roger (03/11/2026), 425 páginas → 204 CNPJs com texto útil, um site por CNPJ (`motor.classificar.textos_por_empresa`). A precisão ainda depende do gabarito humano.

`gpt-6-luna`: 03/11/2026, mesmo prompt `classificacao_v3`, temperatura 0, `reasoning.effort = none`, mesma entrada, sobre as 104 empresas que ele julgou site de ensino. Foram 203 das 204 empresas: uma foi recusada pelo filtro de moderação da OpenAI (erro 400, "prompt flagged") e continua com a classificação do Gemini. Nas 203 em comum, os dois modelos concordam em `site_de_ensino` em 190 (93,6%); o `gpt-6-luna` aceita 12 que o Gemini recusou (treinamentos corporativos, mentoria, segurança do trabalho) e recusa 1 que o Gemini aceitou. Nas 92 que os dois julgaram ensino, concordam no canal em 71 e no modelo de receita em 70. O `gpt-6-luna` diz "indeterminado" mais vezes em canal e receita, o que parece mais fiel ao que os sites dizem, mas sem gabarito isso não é precisão. Confiança nas empresas de ensino: Gemini 78 alta, 12 média, 3 baixa (de 93 em comum); `gpt-6-luna` 71 alta, 28 média, 5 baixa (de 104).

| Julgamento "site de ensino" pelo LLM (não é precisão: falta gabarito) | Ensino, `gemini-3.5-flash-lite` | Ensino, `gpt-6-luna` | Data |
|---|---|---|---|
| Domínio do e-mail | 40 de 127 (31,5%) | 45 de 126 (35,7%) | 03/11/2026 |
| Nome × título | 38 de 58 (65,5%) | 43 de 58 (74,1%) | 03/11/2026 |
| CNPJ no rodapé | 16 de 19 (84,2%) | 16 de 19 (84,2%) | 03/11/2026 |
| Total | 94 de 204 (46,1%) | 104 de 203 (51,2%) | 03/11/2026 |

| Recuperação | Valor | Como |
|---|---|---|
| Concorrentes relevantes entre os 10 primeiros (ideias de teste) | | |

## Custo

| Serviço | Gasto total no MVP | Limite do plano |
|---|---|---|
| API da OpenAI (`gpt-6-luna`) | US$ 0,05 em 03/11/2026: 203 classificações = 361.304 tokens de entrada e 21.139 de saída (US$ 0,10 e US$ 0,50 por milhão); mais 6 chamadas ao vivo de teste = 4.912 e 1.023 tokens (< US$ 0,01) | Plano Build: 5.000 chamadas/min e 2 milhões de tokens/min nos modelos Luna (doc da OpenAI, 03/11/2026) |
| API do Gemini (reserva) | | Chave no plano gratuito em 03/11/2026: 15 chamadas/min por modelo no `gemini-3.5-flash-lite` (erro 429 `generate_content_free_tier_requests`, limite 15) |
