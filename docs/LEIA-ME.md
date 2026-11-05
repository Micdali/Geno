# Textos de sites — RJ (para o motor / Micael)

Formato de sempre: uma linha por página coletada —
`cnpj, site, metodo, url, tipo, texto, status_http, bloqueado, coletado_em`
(texto limpo, truncado em ~5.000). A classificação é você quem faz.

Entrega **em lotes**, sem repetir CNPJ entre lotes:
- `textos_sites_rj.csv` — lote 1 (03/11): 245 empresas.
- `textos_sites_rj_2.csv` — lote 2: 504 escolas, 89% das homes com palavra de ensino.
- `textos_sites_rj_3.csv` — lote 3: 242 escolas, **90%** ensino, 0 CNPJ com >1 site.
- `extra_email_sem_sinal_rj.csv` — refugo de e-mail sem sinal de ensino (garimpo opcional).
- `gabarito_100_rj.csv` — 100 escolas com os campos de classificação (contrato 3), para
  medir a precisão da LLM. **Rascunho: classificação gerada automaticamente (campo
  `anotador`), não conferida à mão** — serve de partida; o ideal é um humano revisar antes
  de usar como verdade de referência. `modelo_receita` usa a lista fechada (pacote_ou_mensalidade,
  assinatura, venda_avulsa, outro) — confirmar contra o `contrato 3`.

## Lote 2 — `textos_sites_rj_2.csv`
**504 empresas novas** (nenhuma repetida do lote 1), **782 páginas**.

Conferência (como você pediu):
- **CNPJs com mais de um site: 0** (agora é um site por CNPJ).
- **Homes 200 com palavra de ensino: 446/501 = 89%** (meta ≥ 80%). No lote 1 foi 67%.

Como o lote melhorou, item por item do seu pedido:
1. **Contador descartado antes de coletar.** Domínio em ≥3 CNPJs do parquet **ou** nome
   com contab/contador/contabil/fiscal/assessoria/advoga/adv. → **3.054 domínios
   descartados** (1.776 por frequência, 1.731 por nome). Vai no `METRICAS.md`.
2. **Um site por CNPJ.** Prioridade `manual > rodape_cnpj > nome_titulo > email`; no
   empate, o site com mais texto. Nome que casa com muitos domínios (genérico) não liga
   nenhum.
3. **Fila priorizada por escola.** Lote 2 = ativas com CNAE principal do piloto, nos 5
   nichos (idiomas, informática, preparatórios, treinamento, outros cursos).
4. **Filtro de e-mail fraco (importante).** O domínio do e-mail cadastral muitas vezes
   não é o site de ensino — por isso no lote 1 o e-mail acertou só 40/127. Agora um
   vínculo por **e-mail só entra se o site mostrar conteúdo de ensino em alguma página**;
   rodapé e nome × título entram sempre. É isso que puxa o % de ensino de ~51% para 89%.
   Se você preferir receber **também** os e-mails sem sinal de ensino (para você mesmo
   filtrar), peço e mando um CSV à parte — é um parâmetro.

## O que não mudou
`robots.txt`, no máximo 1 req/s por domínio, User-Agent = `GENO_USER_AGENT`. Bloqueios
(Cloudflare etc.) registrados com `bloqueado = true`, nunca contornados (6,2% dos
domínios). Só texto público. `cnpj` sempre real, vindo do `candidatos.parquet` (RJ).

## Como foi feito
`python -m enriquecimento.pipeline <lote.csv>` → `python -m enriquecimento.exportar_textos`
(numera o lote e exclui os CNPJs já entregues sozinho).

## Próximos lotes
Há **2.300+ escolas ativas tier-1** ainda não coletadas, mais as que entraram por CNAE
secundário. Dá para seguir até o seu marco de 500–1.000 sites de ensino. É só pedir o
próximo lote.
