# Métricas do recorte do GENO

Gerado automaticamente por `python -m dados.etl.gerar_metricas` (roda ao fim do `construir_db`). Todos os números vêm de consultas ao `geno.duckdb`; não edite à mão. Os mesmos números, em formato estruturado, estão em `metricas.json`.

## Fonte

- Base: Dados Abertos do CNPJ, Receita Federal do Brasil (licença CC-BY), competência **2026-10**.
- Data de geração: 2026-11-02
- Commit: `5091397`

## Recorte

- UF: **RJ**. Unidade de análise: **estabelecimento** (matriz e filiais contam separadamente).
- Período dos eventos: **2021 a 2025** (anos completos).
- CNAEs (principal ou secundário):

  - 8593700: Ensino de idiomas
  - 8599604: Treinamento em desenvolvimento profissional e gerencial
  - 8599699: Outras atividades de ensino não especificadas anteriormente
  - 8599603: Treinamento em informática
  - 8599605: Cursos preparatórios para concursos

## Parâmetros

- `limiar_recuo`: **50** estabelecimentos no nicho antes de ampliar o CNAE (subclasse, classe, grupo).
- Lacuna: no máximo `max(2, 5,0% dos estabelecimentos ativos do nicho)`; só se aponta com pelo menos 50 ativos no nicho.
- Regras e números que sustentam cada escolha: [decisoes/DECISOES.md](decisoes/DECISOES.md).

## Estoque

Total de estabelecimentos no recorte: **333.571**. Ativas: **52,8%**. Baixadas: **37,2%**.

| Situação cadastral | Estabelecimentos | % |
|---|---|---|
| Ativa | 176.175 | 52,8% |
| Suspensa | 516 | 0,2% |
| Inapta | 32.598 | 9,8% |
| Baixada | 123.927 | 37,2% |
| Nula | 355 | 0,1% |

## Por CNAE (principal)

| CNAE | Descrição | Estabelecimentos | Ativas | % ativas |
|---|---|---|---|---|
| 8593700 | Ensino de idiomas | 11.524 | 4.199 | 36,4% |
| 8599604 | Treinamento em desenvolvimento profissional e gerencial | 53.817 | 26.215 | 48,7% |
| 8599699 | Outras atividades de ensino não especificadas anteriormente | 81.836 | 39.644 | 48,4% |
| 8599603 | Treinamento em informática | 13.113 | 4.775 | 36,4% |
| 8599605 | Cursos preparatórios para concursos | 8.270 | 3.305 | 40,0% |
| outros | CNAE principal fora do setor (entraram pelo CNAE secundário) | 165.011 | 98.037 | 59,4% |

## Municípios com mais estabelecimentos ativos (10 maiores)

| Município | Ativos | Total | % ativos |
|---|---|---|---|
| Rio de Janeiro | 97.055 | 180.166 | 53,9% |
| Niteroi | 11.884 | 21.129 | 56,2% |
| Sao Goncalo | 5.765 | 11.743 | 49,1% |
| Duque de Caxias | 4.766 | 9.838 | 48,4% |
| Nova Iguacu | 4.762 | 9.912 | 48,0% |
| Petropolis | 3.743 | 7.148 | 52,4% |
| Campos dos Goytacazes | 3.545 | 6.692 | 53,0% |
| Macae | 2.798 | 5.363 | 52,2% |
| Volta Redonda | 2.696 | 4.996 | 54,0% |
| Marica | 2.316 | 4.089 | 56,6% |

## Perfil

Base: todos os 333.571 estabelecimentos do recorte.

| Característica | Estabelecimentos | % |
|---|---|---|
| Empresa optante pelo MEI | 118.802 | 35,6% |
| Empresa optante pelo Simples Nacional | 175.254 | 52,5% |
| Matriz | 327.495 | 98,2% |
| Filial | 6.076 | 1,8% |

## Eventos no período (2021 a 2025)

Aberturas pela data de início de atividade; baixas pela data da situação cadastral (situação 08). `Baixas de ofício` são parte das baixas, separadas pelo motivo (`motivo_classe.csv`). `Saldo` = aberturas - baixas que não são de ofício. `Ativos no fim do ano`: abertos até 31/12 e ainda não baixados nessa data, o que inclui estabelecimentos inaptos e suspensos (por isso é maior que a contagem de situação "ativa" do estoque).

| Ano | Aberturas | Baixas | Baixas de ofício | Saldo | Ativos no fim do ano |
|---|---|---|---|---|---|
| 2021 | 30.048 | 8.652 | 15 | 21.411 | 138.271 |
| 2022 | 27.351 | 10.847 | 2 | 16.506 | 154.775 |
| 2023 | 28.277 | 13.998 | 0 | 14.279 | 169.054 |
| 2024 | 29.001 | 16.215 | 0 | 12.786 | 181.840 |
| 2025 | 32.426 | 18.364 | 0 | 14.062 | 195.902 |

## Mortalidade em 2 anos

Por coorte de abertura: baixados até 2 anos depois (ano da baixa <= ano da abertura + 2), sem contar as baixas de ofício, sobre o total de abertos da coorte. Só entram coortes que completaram os 2 anos dentro do período.

| Coorte (ano de abertura) | Abertos | Baixados | Baixas de ofício até o horizonte | Taxa |
|---|---|---|---|---|
| 2021 | 30.048 | 7.620 | 1 | 25,4% |
| 2022 | 27.351 | 7.637 | 1 | 27,9% |
| 2023 | 28.277 | 8.334 | 0 | 29,5% |

Coortes somadas: 23.591 baixados de 85.676 abertos, taxa de **27,5%**.

## Cobertura para a coleta dos sites

Dos **176.175** estabelecimentos ativos, **27.296** (**15,5%**) têm e-mail de domínio próprio (provedores genéricos, como gmail e hotmail, excluídos). É o ponto de partida para achar o site; domínios de contadores ainda não foram descartados.

## Limitações

- A base é uma fotografia de uma única competência (2026-10); empresas e baixas posteriores não aparecem.
- O ano corrente (2026) está excluído por estar incompleto; o período vai de 2021 a 2025.
- As baixas de ofício estão separadas pelo motivo da situação cadastral, conforme `dados/sql/seeds/motivo_classe.csv`; a data da baixa é um indicador ruidoso do fechamento real da empresa.
- A unidade é o estabelecimento, não a empresa: matriz e filiais contam separadamente.
- Os percentuais de MEI e Simples refletem a situação atual da empresa na competência, não a da data de abertura.
- Os números de mortalidade não são comparáveis diretamente aos do IBGE e do Sebrae (a base inclui MEIs e empresas sem empregados).
