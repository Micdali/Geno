# Geno: identidade visual e textos da interface

## 1. A ideia da marca

O Geno mostra o mercado da ideia de quem vai abrir um negócio. A identidade traduz isso em uma
floresta à noite: um fundo verde-escuro coberto por pontos, um por empresa, e um único ponto de
cor quente, o coral, reservado ao que importa: a ideia do usuário e o que ninguém atende. Tudo
que é secundário fica em verde e creme, para o coral ser sempre a leitura principal da tela.

## 2. Logotipo

O logotipo é um **G** verde com um foguete coral que sai do traço do G, a ideia que decola. Há
duas versões do mesmo desenho: a de cores plenas para fundo escuro e uma branca com o foguete coral,
para fundo creme ou areia.

<div class="logos"><div class="lg" style="background:#0F3D33"><img src="logo.png"><br><span>Fundo escuro</span></div><div class="lg" style="background:#FAF3E7"><img src="logo_branco.png"><br><span style="color:#17261F">Fundo claro</span></div></div>

- Usar sempre sobre o fundo noite ou sobre creme e areia. Nunca sobre fotos ou fundos com ruído.
- Manter o foguete em coral. Não recolorir o G nem o foguete.
- Deixar ao redor do logotipo uma margem livre de pelo menos a largura do foguete.
- Como ícone da aba do navegador, usar o logotipo sozinho, sem o nome.

## 3. Cores

<div class="sw"><div class="c" style="background:#1F6F5C;color:#FAF3E7"><b>Floresta</b><br>#1F6F5C</div><div class="c" style="background:#134A3D;color:#FAF3E7"><b>Floresta escura</b><br>#134A3D</div><div class="c" style="background:#0F3D33;color:#FAF3E7"><b>Noite</b><br>#0F3D33</div><div class="c" style="background:#8FD3BD;color:#17261F"><b>Menta</b><br>#8FD3BD</div><div class="c" style="background:#E8613C;color:#FFFFFF"><b>Coral</b><br>#E8613C</div><div class="c" style="background:#FAF3E7;color:#17261F"><b>Creme</b><br>#FAF3E7</div><div class="c" style="background:#F0E3C8;color:#17261F"><b>Areia</b><br>#F0E3C8</div><div class="c" style="background:#17261F;color:#FAF3E7"><b>Tinta</b><br>#17261F</div></div>

| Cor | Código | Uso |
|---|---|---|
| Floresta | `#1F6F5C` | Cor da marca: logotipo, etapas concluídas da linha do tempo |
| Floresta escura | `#134A3D` | Sombras e variações do verde |
| Noite | `#0F3D33` | Fundo de todas as telas |
| Menta | `#8FD3BD` | Verde claro legível no escuro: contornos, confiança alta, destaques secundários |
| Coral | `#E8613C` | Destaque único: botões, o nicho do usuário nos gráficos e a lacuna, o que ninguém atende |
| Creme | `#FAF3E7` | Texto sobre o fundo escuro e campo da ideia |
| Areia | `#F0E3C8` | Cabeçalho de vidro, superfícies claras |
| Tinta | `#17261F` | Texto sobre fundo claro |

Os três níveis do indicador de confiança usam uma faixa translúcida com borda na cor do nível:
**alta** em menta (`#8FD3BD`), **média** em âmbar (`#F0BE5A`) e **baixa** em coral (`#E8613C`).
O texto da faixa é sempre creme, e a cor da borda é um reforço, nunca a única informação: cada
nível também diz o motivo por escrito.

## 4. Tipografia

- **Fraunces** (500, 600 e 700), uma fonte com serifa de traço quente, para títulos e para o texto
  de destaque dos cards. Entrelinha curta e espaçamento levemente fechado nos títulos grandes.
- **Manrope** (400 a 800), sem serifa e legível em tamanho pequeno, para o texto corrido, campos,
  tabelas e botões.
- O texto corrido tem 1,12 rem e entrelinha de 1,65, maior que o padrão, porque a leitura é o
  produto. Legendas e ajudas usam creme a 70% de opacidade.

## 5. Componentes

- **Fundo.** Verde-noite com um brilho suave no alto e um campo de pontos finos. Os pontos
  lembram as empresas do mapa e aparecem também na animação da tela de progresso.
- **Cabeçalho.** Uma pílula de vidro bege fixa no topo das telas 2 a 6, com o logotipo à esquerda e
  a linha do tempo à direita: Ideia, Nicho, Análise, Concorrentes, Saturação e Lacunas. A etapa
  atual fica em verde-floresta com halo, as concluídas ganham um visto e as futuras ficam tracejadas.
- **Botão principal.** Contorno menta e seta; no hover, fica coral cheio. Serve às ações
  importantes: analisar, confirmar, tentar de novo.
- **Campo da ideia.** Caixa creme com sombra suave, o único elemento claro da tela de entrada.
- **Divisor.** Linha fina de creme a 16% de opacidade entre as seções, com subtítulo em Fraunces.
- **Caixa de confiança.** Faixa translúcida com borda lateral na cor do nível (seção 3), logo abaixo do recorte.
- **Card de lacuna.** O herói da tela de resultado: cartão creme com borda coral à esquerda e título coral.
- **Gráficos.** Barras em cinza-esverdeado, com a barra do nicho do usuário em coral. Os números ficam
  ao lado, em creme.

## 6. Voz dos textos

1. **Só afirmamos o que o dado sustenta.** O Geno mostra oferta, não demanda.
2. **Nunca "validar"**, nem "boa ideia" ou "não abra esse negócio".
3. **Onde há incerteza, dizemos qual é e por quê.** Cada nível de confiança traz o motivo.
4. **Erros dizem o que aconteceu e o que fazer.** Sem pedir desculpa.
5. **Português do Brasil, frases curtas, verbos simples.**
6. **"Deram baixa", e não "fecharam".** A baixa no CNPJ nem sempre significa que o negócio fechou.

## 7. Textos da interface

Todos os textos ficam em um único arquivo (`app/geno/textos.py`), para trocar uma frase sem mexer
no código. Os trechos entre chaves, como `{n}`, são preenchidos pelo aplicativo.

### Tela 1 · entrada

| Elemento | Texto |
|---|---|
| `TITULO` | Não é o mercado do seu negócio. É o mercado da sua ideia. |
| `SUBTITULO` | Descreva o que você pensa em abrir. Mostramos quem já faz, quantos deram baixa e o que ninguém está atendendo. |
| `CAMPO_IDEIA_LABEL` | Qual é a sua ideia? |
| `CAMPO_IDEIA_PLACEHOLDER` | Descreva sua ideia |
| `BOTAO_ANALISAR` | Analisar ideia |
| `HOME_EXPLICACAO` | Descreva o negócio que você pensa em abrir: o que oferece, para quem e como. O Geno cruza dados da Receita Federal com sites de escolas do RJ e mostra quem já faz algo parecido, se o setor cresce e o que ninguém atende. |
| `SEM_CADASTRO` | Sem cadastro. A primeira análise é grátis. |

### Linha fixa de limite (aparece em todas as telas de resultado)

| Elemento | Texto |
|---|---|
| `LIMITE_DEMANDA` | Mostramos o que já existe, não quanta gente compraria. |

### Afunilamento: o sistema pergunta de volta (teto de 2 a 3 rodadas)

| Elemento | Texto |
|---|---|
| `AFUNILAR_INTRO` | Para analisar com precisão, preciso entender melhor a ideia. |
| `AFUNILAR_RODADA` | Pergunta {atual} de {total} |
| `AFUNILAR_OPCIONAL` | Responder é opcional: as respostas deixam o recorte mais preciso. |
| `AFUNILAR_VARIAS` | Marque quantas quiser. |
| `AFUNILAR_OUTRO` | Outro: escreva com suas palavras |
| `AFUNILAR_OUTRO_EXEMPLO` | Descreva sua resposta |
| `AFUNILAR_PUBLICO` | Para quem você pretende vender? |
| `AFUNILAR_PRODUTO` | O que exatamente você ofereceria? |
| `AFUNILAR_CANAL` | Como o cliente seria atendido: presencial, delivery, online ou os dois? |
| `AFUNILAR_GENERICA` | Pode dar mais detalhes sobre o que você quer abrir? |
| `BOTAO_RESPONDER` | Responder |
| `BOTAO_ANALISAR_ASSIM_MESMO` | Analisar assim mesmo |
| `AFUNILAR_AVISO_TETO` | Vamos analisar com o que você descreveu. Como a ideia ainda está ampla, a confiança do resultado será baixa. |

### Tela 2 · confirmação do recorte (núcleo do produto)

| Elemento | Texto |
|---|---|
| `RECORTE_TITULO` | Foi isso que entendi da sua ideia |
| `RECORTE_AJUDA` | Confirme ou ajuste. Você pode escolher uma opção ou escrever do seu jeito. |
| `RECORTE_PUBLICO` | Público |
| `RECORTE_PRODUTO` | Produto ou serviço |
| `RECORTE_CANAL` | Canal |
| `RECORTE_GEOGRAFIA` | Onde |
| `RECORTE_GEOGRAFIA_PADRAO` | Estado do Rio de Janeiro (piloto) |
| `AVISO_PILOTO` | Versão piloto: ensino e treinamento no estado do Rio de Janeiro. |
| `RECORTE_GEOGRAFIA_REFINAR` | Refinar por cidade ou estado (opcional) |
| `BOTAO_CONFIRMAR_RECORTE` | Analisar recorte |
| `BOTAO_VOLTAR` | Voltar |
| `BOTAO_VER_SATURACAO` | Ver a saturação |
| `BOTAO_VER_LACUNAS` | Ver as lacunas |
| `BOTAO_NOVA_IDEIA` | Analisar outra ideia |
| `CARGA_PREPARANDO` | Preparando o Geno |
| `CARGA_PREPARANDO_SUB` | Só na primeira abertura: leva uns 20 segundos. |
| `CARGA_RECORTE_ETAPAS` | Lendo a sua ideia / Identificando o nicho / Preparando as perguntas |
| `SATURACAO_LEITURA` | O que isso quer dizer |
| `SAT_COMPARATIVO` | Para cada 10 que abriram, quantos fecharam |
| `SAT_COMPARATIVO_AJUDA` | 2021 a 2025, nos nichos de ensino que o Geno analisa no RJ. O seu está em destaque. |
| `SAT_ANO_A_ANO` | Aberturas e baixas, ano a ano |
| `SAT_SOBREVIVENCIA` | Quantos continuam abertos |
| `SAT_SOBREVIVENCIA_AJUDA` | De cada 100 que abriram em cada ano, quantos ainda estão ativos. Dos que abriram em {ano}, {pct} em 100 seguem abertos. |
| `SAT_ONDE_QUEM` | Onde estão e quem são |
| `SAT_MUNICIPIOS` | Ativos por município |
| `SAT_PORTE` | Quanto da concorrência é MEI |
| `FORA_DO_PILOTO_TITULO` | O Geno ainda não analisa este ramo |
| `FORA_DO_PILOTO` | Esta versão piloto só analisa ensino e treinamento no estado do Rio de Janeiro: cursos, aulas, escolas e capacitação. A sua ideia parece ser de outro ramo, e uma análise aqui compararia você com escolas, o que daria resultados sem sentido. |
| `BOTAO_OUTRA_IDEIA` | Escrever outra ideia |
| `BOTAO_CORRIGIR_RECORTE` | Corrigir |

### Progresso (espera de até 1 minuto)

| Elemento | Texto |
|---|---|
| `PROGRESSO_TITULO` | Analisando o seu recorte |
| `PROGRESSO_ETAPAS` | Contando empresas que abriram e deram baixa / Identificando quem já faz algo parecido / Lendo o que cada uma oferece / Procurando o que ninguém atende |
| `PROGRESSO_DEMORA` | Isso pode levar até 1 minuto. |

### Indicador de confiança: 3 níveis, cada um diz o porquê

| Elemento | Texto |
|---|---|
| `CONFIANCA_ROTULO` | Confiança da análise |
| `CONFIANCA_ALTA` | Confiança alta. Encontramos {n} empresas no seu recorte e conseguimos descrever o que a maioria oferece. |
| `CONFIANCA_MEDIA` | Confiança média. Encontramos {n} empresas, mas para {pct}% delas não conseguimos identificar com clareza o que oferecem. Confira a lista antes de tirar conclusões. |
| `CONFIANCA_BAIXA_POUCAS` | Confiança baixa. Só encontramos {n} empresas neste recorte. Com tão poucas, qualquer padrão pode ser coincidência. Tente uma descrição mais ampla. |
| `CONFIANCA_BAIXA_AMBIGUA` | Confiança baixa. Não conseguimos identificar com clareza o que a maioria das empresas deste recorte oferece. Tente descrever melhor o produto ou o público. |
| `CONFIANCA_BAIXA_IDEIA_AMPLA` | Confiança baixa. A ideia ficou ampla e não conseguimos estreitar o recorte. Use “Ajustar minha ideia” para ser mais específico. |

### Baixa de CNPJ ≠ empresa fechada (aviso fixo junto da mortalidade)

| Elemento | Texto |
|---|---|
| `BAIXA_CNPJ_AVISO` | Contamos empresas com baixa no CNPJ. Baixa nem sempre significa que o negócio fechou (pode ser reestruturação), e algumas empresas paradas nunca dão baixa. O critério é o mesmo para todas. |
| `BAIXA_CNPJ_CURTO` | Baixa no CNPJ ≠ empresa fechada |

### Tela de resultado · blocos

| Elemento | Texto |
|---|---|
| `LACUNA_TITULO` | O que ninguém está atendendo |
| `LACUNA_FRASE` | Das {n} escolas ativas com site neste ramo, nenhuma oferece {combinacao}. |
| `LACUNA_FRASE_POUCAS` | Das {n} escolas ativas com site neste ramo, só {k} oferecem {combinacao}. |
| `LACUNA_BASE_PEQUENA` | Base pequena: confira as empresas antes de tirar conclusões. |
| `LACUNA_IDEIA_COMUM` | A combinação da sua ideia já é oferecida por mais de 10% das escolas deste ramo. Veja abaixo variações próximas com pouca oferta. |
| `LACUNA_VARIACOES` | Variações da sua ideia com pouca oferta |
| `LACUNA_VARIACOES_AJUDA` | Mudamos um ou dois aspectos da sua ideia (público, formato ou canal) e contamos quantas escolas já oferecem cada variação. Pouca oferta não quer dizer que há procura. |
| `LACUNA_NENHUMA` | Não encontramos uma combinação que quase ninguém ofereça neste recorte. Tente ajustar a ideia. |
| `LACUNA_VER_EMPRESAS` | Ver as {n} empresas analisadas |
| `LACUNA_EMPRESAS_AJUDA` | Estas são as empresas que embasaram a conclusão. Você pode conferir cada uma. |
| `SATURACAO_TITULO` | Quantos abriram e quantos deram baixa |
| `SATURACAO_FRASE_FECHARAM_MAIS` | Nos últimos {anos} anos, mais empresas deram baixa do que abriram neste setor. |
| `SATURACAO_FRASE_ABRIRAM_MAIS` | Nos últimos {anos} anos, mais empresas abriram do que deram baixa neste setor. |
| `SATURACAO_FONTE` | Fonte: base de CNPJ da Receita Federal, atualizada em {data}. |
| `CONCORRENTES_TITULO` | Quem já faz algo parecido |
| `CONCORRENTES_VAZIO` | Não encontramos empresas com site para este recorte. |
| `SEM_SITE_AVISO` | Empresas sem site não entram na análise de concorrentes e de lacunas. Isso pode deixar de fora negócios pequenos. |
| `BOTAO_AJUSTAR_IDEIA` | Ajustar minha ideia |

### Erros: dizem o que houve e o que fazer. Sem pedir desculpa.

| Elemento | Texto |
|---|---|
| `ERRO_IDEIA_VAZIA` | Escreva a sua ideia antes de analisar. |
| `ERRO_IDEIA_CURTA` | A descrição está muito curta. Diga o que você quer vender e para quem. |
| `ERRO_FORA_ESCOPO` | O Geno analisa ideias de negócio com empresa e CNPJ, como lojas, serviços e restaurantes. Esta descrição não parece uma. Descreva o negócio que você pensa em abrir. |
| `ERRO_SEM_RESULTADO` | Não encontramos empresas parecidas com esta ideia. Tente descrever com outras palavras ou ampliar o recorte. |
| `ERRO_TEMPO_ESGOTADO` | A análise demorou mais do que o esperado e foi interrompida. Tente de novo. |
| `ERRO_SERVICO` | Não conseguimos acessar um dos serviços da análise. Aguarde um minuto e tente de novo. |
| `BOTAO_TENTAR_NOVAMENTE` | Tentar de novo |

### Rodapé

| Elemento | Texto |
|---|---|
| `RODAPE` | Geno mostra oferta, não demanda. Não substitui pesquisa com clientes. |

