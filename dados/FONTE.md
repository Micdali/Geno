# FONTE — Dados Abertos do CNPJ (Receita Federal)

Registro da fonte usada pelo ETL de `dados/`. Atualizar a cada nova carga.

| Item | Valor |
|---|---|
| Responsável | Receita Federal do Brasil (RFB) |
| Competência usada | **2026-10** (arquivos gerados em 13/10/2026) |
| Consulta feita em | 29/10/2026 |
| Licença | Creative Commons Attribution (CC-BY): uso livre, inclusive comercial, com atribuição da fonte |
| Formato | ZIP com um CSV sem cabeçalho, separador `;`, aspas `"`, encoding Latin-1 (ISO-8859-1) |
| Recorte do GENO | UF = RJ; CNAE principal ou secundário do setor "educação livre" (ver `config.yaml`) |

## Onde está (o endereço mudou)

- **Endereço antigo, fora do ar:** `https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/` retorna HTTP 404 (verificado em 29/10/2026).
- **Endereço atual:** a Receita migrou o repositório para um compartilhamento Nextcloud ("SERPRO+"):
  `https://arquivos.receitafederal.gov.br/index.php/s/gn672Ad4CF8N6TK` (navegador).
- **Acesso programático (WebDAV)**, usado pelo ETL:
  `https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/<AAAA-MM>/`
  com autenticação básica: usuário = `gn672Ad4CF8N6TK` (token do link público), senha vazia.
  O servidor responde a `PROPFIND` (lista com tamanho, ETag e data) e aceita `Range` (HTTP 206).
- A pasta `Dados/Cadastros/CNPJ/` tem uma pasta por mês de 2023-05 a 2026-10 e um `cnpj.tar.gz` (63,95 GB, jan/2026) que **não** usamos.
- Conferir o endereço no navegador antes de cada carga: ele já mudou de lugar mais de uma vez.

## Arquivos da competência 2026-10 usados pelo GENO

Tamanhos em bytes, conforme o servidor em 29/10/2026. **Sócios não é baixado** (minimização de dados, LGPD); no servidor há `Socios0` a `Socios9` (≈ 0,7 GB), ignorados.

| Arquivo | Bytes | Modificado (GMT) |
|---|---:|---|
| Estabelecimentos0 | 2.277.696.710 | 13/10/2026 22:04 |
| Estabelecimentos1 | 341.948.627 | 13/10/2026 22:04 |
| Estabelecimentos2 | 336.288.966 | 13/10/2026 22:05 |
| Estabelecimentos3 | 368.597.760 | 13/10/2026 22:05 |
| Estabelecimentos4 | 340.413.465 | 13/10/2026 22:06 |
| Estabelecimentos5 | 335.452.647 | 13/10/2026 22:06 |
| Estabelecimentos6 | 369.782.592 | 13/10/2026 22:06 |
| Estabelecimentos7 | 338.419.961 | 13/10/2026 22:07 |
| Estabelecimentos8 | 343.568.209 | 13/10/2026 22:07 |
| Estabelecimentos9 | 364.761.032 | 13/10/2026 22:08 |
| Empresas0 | 570.972.127 | 13/10/2026 22:00 |
| Empresas1 | 77.901.368 | 13/10/2026 22:01 |
| Empresas2 | 79.125.712 | 13/10/2026 22:01 |
| Empresas3 | 85.102.880 | 13/10/2026 22:01 |
| Empresas4 | 90.222.463 | 13/10/2026 22:01 |
| Empresas5 | 97.310.075 | 13/10/2026 22:01 |
| Empresas6 | 94.194.819 | 13/10/2026 22:01 |
| Empresas7 | 98.676.055 | 13/10/2026 22:01 |
| Empresas8 | 98.736.571 | 13/10/2026 22:01 |
| Empresas9 | 94.309.858 | 13/10/2026 22:01 |
| Simples | 310.608.217 | 13/10/2026 22:08 |
| Cnaes | 22.078 | 13/10/2026 22:00 |
| Motivos | 1.180 | 13/10/2026 22:08 |
| Municipios | 43.443 | 13/10/2026 22:08 |
| Naturezas | 1.585 | 13/10/2026 22:08 |
| Paises | 2.745 | 13/10/2026 22:08 |
| Qualificacoes | 980 | 13/10/2026 22:08 |

Total: 27 arquivos, 7,11 GB compactados. Tamanhos descompactados medidos no índice do ZIP:
`Estabelecimentos0` 7,26 GB (CSV), `Estabelecimentos1` 1,08 GB, `Empresas0` 2,35 GB, `Simples` 3,20 GB.
Por isso, ao processar, é preciso espaço para o ZIP **mais** o maior CSV (≈ 9,5 GB no pior caso).

## Layout oficial conferido

Documento: `https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf` (6 páginas, criado em 02/12/2021; não está no repositório novo).
Conferido contra as primeiras 400 linhas reais de cada arquivo em 29/10/2026:

| Tabela | Colunas no PDF | Colunas nos dados | Resultado |
|---|---:|---:|---|
| Estabelecimentos | 30 | 30 | confere, mesma ordem |
| Empresas | 7 | 7 | confere |
| Simples | 7 | 7 | confere |
| Tabelas de domínio (Cnaes, Motivos, Municipios, Naturezas, Paises, Qualificacoes) | 2 | 2 | confere |

A ordem das colunas usada pelo ETL está em `config.yaml`, seção `colunas`.

### Divergências encontradas

1. **Situação cadastral:** o PDF lista `01, 2, 3, 4, 08`, mas os dados trazem sempre dois dígitos: `01, 02, 03, 04, 08`. O ETL usa `'02'` para ativa e `'08'` para baixada.
2. **Motivos:** o PDF não descreve a tabela de domínio de motivos da situação cadastral, mas o arquivo `Motivos.zip` existe (2 colunas) e é necessário para tratar baixas em massa.
3. **Não é divergência, mas vale saber:** a tabela de domínio `Qualificacoes` (no PDF, "Qualificações de Sócios") só serve para Sócios e para a qualificação do responsável em Empresas; é baixada porque o prompt do ETL pede todas as tabelas de domínio.
4. **Capital social** vem com vírgula decimal (ex.: `120000000000,00`) e as datas como `AAAAMMDD`; datas inválidas como `00000000` precisam virar nulo (o PDF não diz isso).
5. **Município** é o código da Receita, **não** o código IBGE (o PDF fala em "código do município de jurisdição").

## Armadilhas dos CSVs (medidas em 29/10/2026)

Não estão no PDF. O `etl/filtrar.py` trata cada uma e confere o resultado contra uma contagem independente de registros.

1. **Aspas duplicadas dentro do campo** (CSV válido): `"NIGTH CLUB ""TUTU"" LTDA"`. Sem `escape='"'` o DuckDB entra em modo estrito, rejeita a linha e **descarta blocos inteiros sem avisar**: em `Empresas1` leu 1,18 M das 4,49 M linhas (perda de 74%). Com `escape='"'` lê tudo e desfaz as aspas. Foi a primeira versão do ETL que teve esse defeito, e a conferência de contagem existe por causa dele.
2. **Quebra de linha dentro de campo entre aspas**: 4 registros em `Estabelecimentos0` (nome ou complemento, de empresas fora do RJ) ocupam 2 linhas físicas. Por isso o número de registros é menor que o de quebras de linha (31.028.464 contra 31.028.468).
3. **Bytes que o DuckDB recusa como Latin-1**: `0x8F` solto no campo de e-mail de uma empresa de SP (`Estabelecimentos0`, único byte inválido em 7,26 GB). `Estabelecimentos1` e `Estabelecimentos7` deram o mesmo erro no DuckDB; a causa neles não foi inspecionada. O filtro tenta Latin-1 e, só se o DuckDB der `File is not latin-1 encoded`, converte o CSV para UTF-8 em streaming (o decodificador Latin-1 do Python aceita os 256 bytes, nada se perde). O `etl_log.csv` registra quais arquivos precisaram disso.
4. **`0x1A` (Ctrl-Z) no lugar de caracteres** em endereços de empresas no exterior (ex.: "URBANIZA␚␚O"). É válido em Latin-1 e não afeta o recorte.
5. **Conferência de totais** (competência 2026-10): 73,8 M de estabelecimentos lidos no Brasil (31.028.464 + 9 × 4.753.435) e 329.038 raízes no recorte, igual à soma das linhas filtradas de Empresas.

## CNAEs do setor piloto (conferidos na tabela oficial `Cnaes`)

| Código | Descrição oficial | Situação no `config.yaml` |
|---|---|---|
| 8593700 | Ensino de idiomas | incluído |
| 8599604 | Treinamento em desenvolvimento profissional e gerencial | incluído |
| 8599699 | Outras atividades de ensino não especificadas anteriormente | incluído |
| 8599603 | Treinamento em informática | incluído (opcional, `incluir_opcionais: true`) |
| 8599605 | Cursos preparatórios para concursos | incluído (opcional, `incluir_opcionais: true`) |

## Atribuição

Dados: Receita Federal do Brasil, Dados Abertos do CNPJ, licença CC-BY. Citar a fonte e a competência (2026-10) no artigo e no app.
