"""Todos os textos da interface do Geno, em um só lugar.

Regras de voz (vêm da filosofia do projeto):
- Só afirmamos o que o dado sustenta: oferta, não demanda.
- Nunca "validar", "boa ideia" ou "não abra esse negócio".
- Onde há incerteza, dizemos qual é e por quê.
- Erros dizem o que aconteceu e o que fazer. Sem pedir desculpa.
- Português do Brasil, frases curtas, verbos simples.

Uso:  from geno.textos import T
      st.title(T.TITULO)
      st.write(T.CONFIANCA_ALTA.format(n=47))

Textos com {chaves} são preenchidos com .format(...).
"""


class T:
    # ------------------------------------------------------------------
    # Tela 1 · entrada
    # ------------------------------------------------------------------
    TITULO = "Não é o mercado do seu negócio. É o mercado da sua ideia."
    SUBTITULO = (
        "Descreva o que você pensa em abrir. Mostramos quem já faz, quantos "
        "deram baixa e o que ninguém está atendendo."
    )
    CAMPO_IDEIA_LABEL = "Qual é a sua ideia?"
    CAMPO_IDEIA_PLACEHOLDER = "Descreva sua ideia"
    BOTAO_ANALISAR = "Analisar ideia"
    HOME_EXPLICACAO = (
        "Descreva o negócio que você pensa em abrir: o que oferece, para quem e como. O Geno cruza dados "
        "da Receita Federal com sites de escolas do RJ e mostra quem já faz algo parecido, se o setor "
        "cresce e o que ninguém atende."
    )
    SEM_CADASTRO = "Sem cadastro. A primeira análise é grátis."

    # ------------------------------------------------------------------
    # Linha fixa de limite (aparece em todas as telas de resultado)
    # ------------------------------------------------------------------
    LIMITE_DEMANDA = (
        "Mostramos o que já existe, não quanta gente compraria."
    )

    # ------------------------------------------------------------------
    # Afunilamento: o sistema pergunta de volta (teto de 2 a 3 rodadas)
    # ------------------------------------------------------------------
    AFUNILAR_INTRO = "Para analisar com precisão, preciso entender melhor a ideia."
    AFUNILAR_RODADA = "Pergunta {atual} de {total}"
    AFUNILAR_OPCIONAL = "Responder é opcional: as respostas deixam o recorte mais preciso."
    AFUNILAR_VARIAS = "Marque quantas quiser."
    AFUNILAR_OUTRO = "Outro: escreva com suas palavras"
    AFUNILAR_OUTRO_EXEMPLO = "Descreva sua resposta"
    AFUNILAR_PUBLICO = "Para quem você pretende vender?"
    AFUNILAR_PRODUTO = "O que exatamente você ofereceria?"
    AFUNILAR_CANAL = "Como o cliente seria atendido: presencial, delivery, online ou os dois?"
    AFUNILAR_GENERICA = "Pode dar mais detalhes sobre o que você quer abrir?"
    BOTAO_RESPONDER = "Responder"
    BOTAO_ANALISAR_ASSIM_MESMO = "Analisar assim mesmo"
    AFUNILAR_AVISO_TETO = (
        "Vamos analisar com o que você descreveu. Como a ideia ainda está "
        "ampla, a confiança do resultado será baixa."
    )

    # ------------------------------------------------------------------
    # Tela 2 · confirmação do recorte (núcleo do produto)
    # ------------------------------------------------------------------
    RECORTE_TITULO = "Foi isso que entendi da sua ideia"
    RECORTE_AJUDA = "Confirme ou ajuste. Você pode escolher uma opção ou escrever do seu jeito."
    RECORTE_PUBLICO = "Público"
    RECORTE_PRODUTO = "Produto ou serviço"
    RECORTE_CANAL = "Canal"
    RECORTE_GEOGRAFIA = "Onde"
    # A base do piloto cobre só o RJ. Trocar por "Brasil inteiro" quando houver mais estados.
    RECORTE_GEOGRAFIA_PADRAO = "Estado do Rio de Janeiro (piloto)"
    AVISO_PILOTO = "Versão piloto: ensino e treinamento no estado do Rio de Janeiro."
    RECORTE_GEOGRAFIA_REFINAR = "Refinar por cidade ou estado (opcional)"
    BOTAO_CONFIRMAR_RECORTE = "Analisar recorte"
    BOTAO_VOLTAR = "Voltar"
    BOTAO_VER_SATURACAO = "Ver a saturação"
    BOTAO_VER_LACUNAS = "Ver as lacunas"
    BOTAO_NOVA_IDEIA = "Analisar outra ideia"
    CARGA_PREPARANDO = "Preparando o Geno"
    CARGA_PREPARANDO_SUB = "Só na primeira abertura: leva uns 20 segundos."
    CARGA_RECORTE_ETAPAS = ["Lendo a sua ideia", "Identificando o nicho", "Preparando as perguntas"]
    SATURACAO_LEITURA = "O que isso quer dizer"
    SAT_COMPARATIVO = "Para cada 10 que abriram, quantos fecharam"
    SAT_COMPARATIVO_AJUDA = "2021 a 2025, nos nichos de ensino que o Geno analisa no RJ. O seu está em destaque."
    SAT_ANO_A_ANO = "Aberturas e baixas, ano a ano"
    SAT_SOBREVIVENCIA = "Quantos continuam abertos"
    SAT_SOBREVIVENCIA_AJUDA = "De cada 100 que abriram em cada ano, quantos ainda estão ativos. Dos que abriram em {ano}, {pct} em 100 seguem abertos."
    SAT_ONDE_QUEM = "Onde estão e quem são"
    SAT_MUNICIPIOS = "Ativos por município"
    SAT_PORTE = "Quanto da concorrência é MEI"
    FORA_DO_PILOTO_TITULO = "O Geno ainda não analisa este ramo"
    FORA_DO_PILOTO = ("Esta versão piloto só analisa ensino e treinamento no estado do Rio de Janeiro: cursos, "
                      "aulas, escolas e capacitação. A sua ideia parece ser de outro ramo, e uma análise aqui "
                      "compararia você com escolas, o que daria resultados sem sentido.")
    BOTAO_OUTRA_IDEIA = "Escrever outra ideia"
    BOTAO_CORRIGIR_RECORTE = "Corrigir"

    # ------------------------------------------------------------------
    # Progresso (espera de até 1 minuto)
    # ------------------------------------------------------------------
    PROGRESSO_TITULO = "Analisando o seu recorte"
    PROGRESSO_ETAPAS = [
        "Contando empresas que abriram e deram baixa",
        "Identificando quem já faz algo parecido",
        "Lendo o que cada uma oferece",
        "Procurando o que ninguém atende",
    ]
    PROGRESSO_DEMORA = "Isso pode levar até 1 minuto."

    # ------------------------------------------------------------------
    # Indicador de confiança: 3 níveis, cada um diz o porquê
    # ------------------------------------------------------------------
    CONFIANCA_ROTULO = "Confiança da análise"

    CONFIANCA_ALTA = (
        "<b>Confiança alta.</b> Encontramos {n} empresas no seu recorte e "
        "conseguimos descrever o que a maioria oferece."
    )
    CONFIANCA_MEDIA = (
        "<b>Confiança média.</b> Encontramos {n} empresas, mas para {pct}% delas "
        "não conseguimos identificar com clareza o que oferecem. Confira a "
        "lista antes de tirar conclusões."
    )

    # Confiança baixa tem um texto por causa, para o usuário saber o que fazer
    CONFIANCA_BAIXA_POUCAS = (
        "<b>Confiança baixa.</b> Só encontramos {n} empresas neste recorte. "
        "Com tão poucas, qualquer padrão pode ser coincidência. Tente uma "
        "descrição mais ampla."
    )
    CONFIANCA_BAIXA_AMBIGUA = (
        "<b>Confiança baixa.</b> Não conseguimos identificar com clareza o que a "
        "maioria das empresas deste recorte oferece. Tente descrever "
        "melhor o produto ou o público."
    )
    CONFIANCA_BAIXA_IDEIA_AMPLA = (
        "<b>Confiança baixa.</b> A ideia ficou ampla e não conseguimos "
        "estreitar o recorte. Use “Ajustar minha ideia” para ser mais específico."
    )

    # ------------------------------------------------------------------
    # Baixa de CNPJ ≠ empresa fechada (aviso fixo junto da mortalidade)
    # ------------------------------------------------------------------
    BAIXA_CNPJ_AVISO = (
        "Contamos empresas com baixa no CNPJ. Baixa nem sempre significa que o "
        "negócio fechou (pode ser reestruturação), e algumas empresas "
        "paradas nunca dão baixa. O critério é o mesmo para todas."
    )
    BAIXA_CNPJ_CURTO = "Baixa no CNPJ ≠ empresa fechada"

    # ------------------------------------------------------------------
    # Tela de resultado · blocos
    # ------------------------------------------------------------------
    LACUNA_TITULO = "O que ninguém está atendendo"
    LACUNA_FRASE = (
        "Das {n} empresas analisadas, nenhuma oferece {combinacao}."
    )
    LACUNA_FRASE_POUCAS = (
        "Das {n} empresas analisadas, só {k} oferecem {combinacao}."
    )
    LACUNA_NENHUMA = (
        "Não encontramos uma combinação que quase ninguém ofereça neste "
        "recorte. Tente ajustar a ideia."
    )
    LACUNA_VER_EMPRESAS = "Ver as {n} empresas analisadas"
    LACUNA_EMPRESAS_AJUDA = (
        "Estas são as empresas que embasaram a conclusão. Você pode conferir "
        "cada uma."
    )

    SATURACAO_TITULO = "Quantos abriram e quantos deram baixa"
    SATURACAO_FRASE_FECHARAM_MAIS = (
        "Nos últimos {anos} anos, mais empresas deram baixa do que abriram neste setor."
    )
    SATURACAO_FRASE_ABRIRAM_MAIS = (
        "Nos últimos {anos} anos, mais empresas abriram do que deram baixa neste setor."
    )
    SATURACAO_FONTE = "Fonte: base de CNPJ da Receita Federal, atualizada em {data}."

    CONCORRENTES_TITULO = "Quem já faz algo parecido"
    CONCORRENTES_VAZIO = "Não encontramos empresas com site para este recorte."

    # Empresas sem site não entram na análise de concorrentes e lacunas
    SEM_SITE_AVISO = (
        "Empresas sem site não entram na análise de concorrentes e de lacunas. "
        "Isso pode deixar de fora negócios pequenos."
    )

    # Botão do laço
    BOTAO_AJUSTAR_IDEIA = "Ajustar minha ideia"

    # ------------------------------------------------------------------
    # Erros: dizem o que houve e o que fazer. Sem pedir desculpa.
    # ------------------------------------------------------------------
    ERRO_IDEIA_VAZIA = "Escreva a sua ideia antes de analisar."
    ERRO_IDEIA_CURTA = "A descrição está muito curta. Diga o que você quer vender e para quem."
    ERRO_FORA_ESCOPO = (
        "O Geno analisa ideias de negócio com empresa e CNPJ, como lojas, "
        "serviços e restaurantes. Esta descrição não parece uma. Descreva o "
        "negócio que você pensa em abrir."
    )
    ERRO_SEM_RESULTADO = (
        "Não encontramos empresas parecidas com esta ideia. Tente descrever "
        "com outras palavras ou ampliar o recorte."
    )
    ERRO_TEMPO_ESGOTADO = (
        "A análise demorou mais do que o esperado e foi interrompida. "
        "Tente de novo."
    )
    ERRO_SERVICO = (
        "Não conseguimos acessar um dos serviços da análise. Aguarde um "
        "minuto e tente de novo."
    )
    BOTAO_TENTAR_NOVAMENTE = "Tentar de novo"

    # ------------------------------------------------------------------
    # Rodapé
    # ------------------------------------------------------------------
    RODAPE = "Geno mostra oferta, não demanda. Não substitui pesquisa com clientes."
