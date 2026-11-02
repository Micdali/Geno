# Decisões do bloco de banco de dados

Competência da Receita: **2026-10**. Gerado por `python -m dados.etl.decidir_parametros` em 2026-11-02. Os valores vigentes estão em `dados/config.yaml`, seção `consultas`.

## 1. Recorte temporal

**Regra:** usar os 5 anos completos de 2021 a 2025. Se as aberturas de 2021 ficarem mais de 30% acima ou abaixo da média de 2022 a 2025, usar 2022 a 2025 e registrar 2021 como ano atípico. 2026 (ano da competência) fica sempre de fora, por estar incompleto.

| Ano | Aberturas (estabelecimentos) |
|---|---|
| 2019 | 21.159 |
| 2020 | 22.687 |
| 2021 | 30.048 |
| 2022 | 27.351 |
| 2023 | 28.277 |
| 2024 | 29.001 |
| 2025 | 32.426 |

Média de 2022 a 2025: **29.264**. Aberturas de 2021: **30.048**, +2,7% em relação à média (limite: 30%).

**Valor escolhido:** período **2021 a 2025**. 2021 não é atípico.

_2026-11-02. Decidido por regra objetiva; pode ser revisto alterando o `dados/config.yaml` e rodando `python -m dados.etl.construir_db`._

## 2. Limiar de recuo (`limiar_recuo`)

**Regra:** menor n em {20, 30, 50, 100} cuja meia-largura do intervalo de confiança de 95% (Wilson) da taxa média de mortalidade em 2 anos do setor seja de no máximo 15 pontos percentuais; se nenhum atender, 100.

Taxa média de mortalidade em 2 anos do setor, coortes completas de 2021 a 2023, sem as baixas de ofício: **27,5%** (23.591 baixados de 85.676 abertos, coortes somadas).

| n (estabelecimentos no nicho) | IC 95% de Wilson | Meia-largura | Atende (<= 15 p.p.)? |
|---|---|---|---|
| 20 | 12,9% a 49,4% | 18,3 p.p. | não |
| 30 | 14,8% a 45,3% | 15,3 p.p. | não |
| 50 | 17,1% a 41,2% | 12,0 p.p. | sim |
| 100 | 19,7% a 37,0% | 8,6 p.p. | sim |

**Valor escolhido:** `limiar_recuo = 50`.

Efeito do limiar escolhido, nas 432 combinações subclasse CNAE x município do setor com pelo menos um estabelecimento aberto de 2021 a 2025:

| Nível usado | Combinações | % |
|---|---|---|
| subclasse | 125 | 28,9% |
| classe (recua) | 156 | 36,1% |
| grupo (recua) | 151 | 35,0% |

Das que recuam para grupo, **86** nem no grupo atingem 50 estabelecimentos (a resposta sai com o grupo mesmo assim; `n_estab` mostra o tamanho). Conferido contra `consultas.mortalidade_setor` em 12 combinações.

_2026-11-02. Decidido por regra objetiva; pode ser revisto alterando o `dados/config.yaml` e rodando `python -m dados.etl.construir_db`._

## 3. Limiar de lacuna

**Regra:** uma combinação de atributos é lacuna quando tem no máximo `max(2, 5,0% dos estabelecimentos ativos do nicho no recorte geográfico)`. Só se aponta lacuna quando o nicho tem pelo menos `limiar_recuo` (50) ativos; abaixo disso, a resposta é "dados insuficientes".

Parâmetros gravados: `lacuna_max_abs = 2`, `lacuna_max_pct = 0.05`.

Os dados de classificação por LLM ainda não existem; esta é só uma referência de tamanho: nos 10 municípios com mais estabelecimentos do recorte, ativos por CNAE principal e o limite de lacuna que resultaria. `*` marca nicho com menos de 50 ativos ("dados insuficientes").

| Município | Estab. (total) | 8593700 | 8599604 | 8599699 | 8599603 | 8599605 |
|---|---|---|---|---|---|---|
| Rio de Janeiro | 180.166 | 2.192 (109,6) | 15.154 (757,7) | 20.881 (1044,0) | 2.742 (137,1) | 1.706 (85,3) |
| Niteroi | 21.129 | 296 (14,8) | 1.678 (83,9) | 2.506 (125,3) | 273 (13,7) | 194 (9,7) |
| Sao Goncalo | 11.743 | 108 (5,4) | 778 (38,9) | 1.569 (78,5) | 186 (9,3) | 132 (6,6) |
| Nova Iguacu | 9.912 | 108 (5,4) | 671 (33,6) | 1.356 (67,8) | 145 (7,2) | 111 (5,6) |
| Duque de Caxias | 9.838 | 107 (5,4) | 614 (30,7) | 1.196 (59,8) | 135 (6,8) | 98 (4,9) |
| Petropolis | 7.148 | 111 (5,6) | 510 (25,5) | 955 (47,8) | 126 (6,3) | 60 (3,0) |
| Campos dos Goytacazes | 6.692 | 82 (4,1) | 458 (22,9) | 744 (37,2) | 73 (3,7) | 76 (3,8) |
| Macae | 5.363 | 91 (4,5) | 483 (24,2) | 420 (21,0) | 42 (2,1)* | 81 (4,0) |
| Volta Redonda | 4.996 | 76 (3,8) | 464 (23,2) | 512 (25,6) | 84 (4,2) | 54 (2,7) |
| Cabo Frio | 4.144 | 65 (3,2) | 283 (14,2) | 457 (22,9) | 62 (3,1) | 63 (3,2) |

Célula = ativos do CNAE principal no município (limite de lacuna). CNAEs: 8593700 Ensino de idiomas; 8599604 Treinamento em desenvolvimento profissional e gerencial; 8599699 Outras atividades de ensino não especificadas anteriormente; 8599603 Treinamento em informática; 8599605 Cursos preparatórios para concursos.

_2026-11-02. Decidido por regra objetiva; pode ser revisto alterando o `dados/config.yaml` e rodando `python -m dados.etl.construir_db`._
