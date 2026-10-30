-- =====================================================================
-- Visão pública (LGPD) e eventos em formato longo. Aplicada depois de 02_views.sql, que cria
-- motivo_tipo e vw_eventos; esta redefine vw_publico com mais colunas.
-- =====================================================================

-- Dados exibíveis: ÚNICA fonte que o app pode consultar (LGPD). Mantém as colunas do contrato
-- (cnpj ... uf) e acrescenta as do relatório técnico (nome_fantasia em diante).
--   * razao_social é NULL em MEI e empresário individual (natureza 2135, "Empresário (Individual)",
--     conferido na tabela oficial): nesses casos ela é "NOME 12345678901".
--   * nome_fantasia e nome_exibicao também escondem o nome fantasia de MEI/EI que repete o nome do
--     titular (com ou sem CPF). Achado de 30/10/2026: 53.207 MEI/EI têm fantasia e parte é o nome da
--     pessoa. Limite: um fantasia que é só o primeiro nome não é detectado.
--   * Não expõe e-mail, domínio de e-mail, telefone, endereço detalhado (logradouro, número,
--     complemento, CEP) nem nada de sócios (que nem existe no banco).
CREATE OR REPLACE VIEW vw_publico AS
WITH base AS (
    SELECT
        e.*,
        emp.razao_social                                      AS rs,
        emp.porte                                             AS porte_cod,
        s.opcao_simples                                       AS opc_simples,
        s.opcao_mei                                           AS opc_mei,
        coalesce(emp.opcao_mei OR s.opcao_mei = 'S' OR emp.natureza_juridica = '2135', false)
                                                              AS pessoa_fisica,
        coalesce(e.nome_fantasia IS NOT NULL
                 AND NOT regexp_matches(e.nome_fantasia, '[0-9]{11}')
                 AND upper(trim(e.nome_fantasia))
                     <> upper(trim(regexp_replace(emp.razao_social, '\s*[0-9]{11}\s*$', ''))), false)
                                                              AS fantasia_ok
    FROM estabelecimento e
    LEFT JOIN empresa emp ON emp.cnpj_basico = e.cnpj_basico
    LEFT JOIN simples s   ON s.cnpj_basico   = e.cnpj_basico
)
SELECT
    b.cnpj,
    CASE WHEN b.pessoa_fisica
         THEN CASE WHEN b.fantasia_ok THEN b.nome_fantasia ELSE 'Empresa individual (nome oculto)' END
         ELSE COALESCE(b.nome_fantasia, b.rs) END             AS nome_exibicao,
    b.situacao,
    b.data_inicio,
    b.data_situacao,
    b.bairro,
    m.descricao                                               AS municipio,
    b.uf,
    CASE WHEN b.pessoa_fisica AND NOT b.fantasia_ok THEN NULL ELSE b.nome_fantasia END AS nome_fantasia,
    CASE WHEN b.pessoa_fisica THEN NULL ELSE b.rs END         AS razao_social,
    b.cnae_principal,
    c.descricao                                               AS cnae_descricao,
    sc.descricao                                              AS situacao_descricao,
    b.porte_cod                                               AS porte,
    b.opc_simples                                             AS opcao_simples,
    b.opc_mei                                                 AS opcao_mei
FROM base b
LEFT JOIN municipio m           ON m.codigo  = b.municipio_cod
LEFT JOIN cnae c                ON c.codigo  = b.cnae_principal
LEFT JOIN situacao_cadastral sc ON sc.codigo = b.situacao;

-- Um evento por linha (abertura ou baixa), para filtrar e agregar por tipo, ano, CNAE ou município.
-- A unidade é o ESTABELECIMENTO: matriz e filiais contam separadamente; use
-- identificador_matriz_filial ('1' matriz, '2' filial) para filtrar depois. Sem filtro de período.
-- Baixa só quando situação = '08'; o motivo vem de motivo_situacao. Município é o código da Receita.
CREATE OR REPLACE VIEW vw_eventos_longo AS
WITH base AS (
    SELECT e.*, emp.natureza_juridica AS natureza, s.opcao_mei AS mei
    FROM estabelecimento e
    LEFT JOIN empresa emp ON emp.cnpj_basico = e.cnpj_basico
    LEFT JOIN simples s   ON s.cnpj_basico   = e.cnpj_basico
)
SELECT cnpj, 'abertura' AS tipo_evento, data_inicio AS data_evento, year(data_inicio) AS ano,
       NULL::VARCHAR AS motivo, cnae_principal AS cnae_fiscal_principal, municipio_cod AS municipio,
       CASE WHEN matriz THEN '1' ELSE '2' END AS identificador_matriz_filial,
       mei AS opcao_mei, natureza AS natureza_juridica
FROM base WHERE data_inicio IS NOT NULL
UNION ALL
SELECT cnpj, 'baixa', data_situacao, year(data_situacao),
       motivo_situacao, cnae_principal, municipio_cod,
       CASE WHEN matriz THEN '1' ELSE '2' END,
       mei, natureza
FROM base WHERE situacao = '08' AND data_situacao IS NOT NULL;
