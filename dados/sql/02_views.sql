-- =====================================================================
-- Visões do GENO (dono: Lucas). Aplicadas DEPOIS de contratos/01_schema.sql.
--
-- vw_eventos substitui a do contrato com as MESMAS colunas na mesma ordem, mais duas ao final
-- (tipo_baixa, conta_mortalidade). Quem lê só as colunas antigas não percebe a mudança.
-- A classificação dos motivos vem da tabela motivo_tipo (preenchida a partir de
-- dados/config.yaml, seção `baixas`) e está A CONFIRMAR PELO GRUPO.
-- =====================================================================

-- Tipo de cada motivo de situação cadastral (não faz parte do contrato 1; é tabela auxiliar).
CREATE OR REPLACE TABLE motivo_tipo (
    codigo  VARCHAR PRIMARY KEY,   -- -> motivo.codigo
    tipo    VARCHAR                -- 'voluntaria' | 'judicial' | 'obito_mei' | 'oficio' | 'reorganizacao' | 'outro'
);

-- Eventos de abertura e baixa, base das séries de saturação.
--   ano_baixa      : ano de qualquer baixa (situação 08), como no contrato
--   tipo_baixa     : classificação do motivo; NULL se não está baixada
--   conta_mortalidade : true só para baixas que indicam fechamento do negócio; baixas de ofício
--                       (omissão, inaptidão) e reorganizações não contam
CREATE OR REPLACE VIEW vw_eventos AS
SELECT
    e.cnpj,
    year(e.data_inicio)                                           AS ano_abertura,
    CASE WHEN e.situacao = '08' THEN year(e.data_situacao) END    AS ano_baixa,
    e.situacao,
    e.motivo_situacao                                             AS motivo,
    CASE WHEN e.situacao = '08' THEN coalesce(t.tipo, 'outro') END AS tipo_baixa,
    coalesce(e.situacao = '08'
             AND coalesce(t.tipo, 'outro') IN ('voluntaria', 'judicial', 'obito_mei'), false)
                                                                  AS conta_mortalidade
FROM estabelecimento e
LEFT JOIN motivo_tipo t ON t.codigo = e.motivo_situacao;

-- Dados exibíveis. Esconde o nome do titular de MEI / empresário individual (LGPD).
-- Natureza 2135 = "Empresário (Individual)" (conferido na tabela oficial).
-- Diferença do contrato: aqui o nome fantasia também é escondido quando, em MEI/EI, ele repete o
-- nome do titular, com ou sem o CPF (a razão social desses casos é "NOME 12345678901"). Medido em 30/10/2026:
-- 53.207 estabelecimentos de MEI/EI têm nome fantasia, e parte deles é o nome da pessoa.
-- Limite conhecido: um nome fantasia que é só parte do nome (ex.: o primeiro nome) não é detectado.
CREATE OR REPLACE VIEW vw_publico AS
SELECT
    e.cnpj,
    CASE
        WHEN emp.opcao_mei OR emp.natureza_juridica = '2135' THEN
            CASE WHEN e.nome_fantasia IS NOT NULL
                      AND NOT regexp_matches(e.nome_fantasia, '[0-9]{11}')   -- "NOME CPF" no fantasia
                      AND upper(trim(e.nome_fantasia))
                          <> upper(trim(regexp_replace(emp.razao_social, '\s*[0-9]{11}\s*$', '')))
                 THEN e.nome_fantasia
                 ELSE 'Empresa individual (nome oculto)' END
        ELSE COALESCE(e.nome_fantasia, emp.razao_social)
    END                     AS nome_exibicao,
    e.situacao,
    e.data_inicio,
    e.data_situacao,
    e.bairro,
    m.descricao             AS municipio,
    e.uf
FROM estabelecimento e
LEFT JOIN empresa   emp ON emp.cnpj_basico = e.cnpj_basico
LEFT JOIN municipio m   ON m.codigo        = e.municipio_cod;
