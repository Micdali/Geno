# Contrato 2 — `candidatos.parquet` (Lucas → Roger)

**Status:** v0, aguardando aprovação.

Arquivo que o bloco de **dados** entrega ao bloco de **enriquecimento**: a lista de estabelecimentos do setor piloto para os quais o Roger vai tentar achar o site.

Local: `dados/parquet/candidatos.parquet` (fora do Git; o Lucas avisa no grupo quando gerar uma versão nova).

| Coluna | Tipo | Descrição |
|---|---|---|
| `cnpj` | texto (14) | Chave de tudo. Texto, nunca número. |
| `nome_fantasia` | texto ou nulo | Usado no casamento nome × título do site |
| `razao_social` | texto ou nulo | Só para busca manual. **Não exibir.** |
| `dominio_email` | texto ou nulo | Domínio do e-mail cadastrado, já sem gmail/hotmail etc. |
| `municipio` | texto | Nome do município |
| `uf` | texto (2) | |
| `situacao` | texto | `02` ativa, `08` baixada etc. Empresas baixadas também entram. |
| `cnae_principal` | texto (7) | |

Enquanto o arquivo real não existe, o Roger pode começar com `exemplos/candidatos.exemplo.csv`.
