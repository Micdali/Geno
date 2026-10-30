# Métricas do GENO

Números reais medidos durante o desenvolvimento. É daqui que o artigo tira os resultados — **não invente nem arredonde para melhor**. Para cada número, registre a data, o tamanho da amostra e como foi medido.

## Recorte da base — Lucas

| Métrica | Valor | Data | Como foi medido |
|---|---|---|---|
| Competência da Receita utilizada | 2026-10 (arquivos de 13/10/2026) | 29/10/2026 | Pasta mais recente do repositório da Receita; ver `dados/FONTE.md` |
| Setor piloto (CNAEs) e recorte geográfico | "Educação livre", UF = RJ; CNAE principal ou secundário em 8593700, 8599604, 8599699, 8599603, 8599605 | 29/10/2026 | `dados/config.yaml`; filtro sem data, todas as situações cadastrais |
| Nº de estabelecimentos no recorte | 333.571 (329.038 raízes de CNPJ) | 29/10/2026 | `python -m dados.etl.validar`; 73,8 M de estabelecimentos lidos no Brasil, conferidos contra a contagem do CSV (0 divergências) |
| % ativas / % baixadas | 52,8% ativas (176.175) / 37,2% baixadas (123.927); inaptas 9,8%, suspensas 0,2%, nulas 0,1% | 29/10/2026 | `python -m dados.etl.validar`, por `situacao_cadastral` |
| Entraram só pelo CNAE secundário | 165.011 (49,5%) | 29/10/2026 | Principal fora dos 5 CNAEs do setor |
| Ativos com `dominio_email` (site provável) | 27.296 de 176.175 (15,5%); baixados 9.581 de 123.927 (7,7%) | 29/10/2026 | Domínio do e-mail, sem provedores genéricos; ainda sem descartar domínios de contadores |
| Nº de baixas tratadas como baixa em massa | | | A fazer (tratamento pelo motivo da situação, nas views) |

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

| Campo | Precisão vs. gabarito (100 empresas) | % indeterminado |
|---|---|---|
| | | |

| Recuperação | Valor | Como |
|---|---|---|
| Concorrentes relevantes entre os 10 primeiros (ideias de teste) | | |

## Custo

| Serviço | Gasto total no MVP | Limite do plano |
|---|---|---|
| API do LLM | | |
