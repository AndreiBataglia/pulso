# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versões seguem [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [0.8.0] - 2026-11-07

### Adicionado
- **Remover o Pulso:** botão em Ajustes e `pulso --remover [--backup-para PASTA]`. Apaga a pasta de dados (só os arquivos que o Pulso cria), o "Iniciar com o Windows" e o atalho do Menu Iniciar; pede para digitar REMOVER, oferece backup em `.zip` e recusa pastas suspeitas.

### Alterado
- O projeto foi marcado como inacabado e encerrado na v0.8.0; ver `docs/diario/encerramento.md`.

## [0.7.0] - 2026-11-07

### Adicionado
- **Etapa 7 (fatias 2 e 3):** ciclo do foco por presença (`FocusCycle`: aguardando, foco, ausente, "o que foi?", lembrete, descanso, além do descanso, reunião), modos Profissional e Casual, sensor de reunião (microfone em uso por outro programa, sem capturar som), migração v3 do banco (categoria e resumo da pausa em segundos).
- Janela nova: anel do foco no rosto, pílula de modo, um painel por fase, **Pausar agora · Prorrogar 5 min · Hoje não**, "o que foi?", reunião, casual e placar do dia. Bandeja com "Modo casual" e submenu "Foco". Ajustes com modo e tolerância de ausência.
- **Aba Jogo:** jokenpô e par ou ímpar com o pet (ganhou: contente; perdeu: bravo), placar do dia em `game_result` (migração v2).
- **Ajustes** (⚙ e menu da bandeja): tempos do pomodoro e da água, aplicados na hora.
- **Etapa 7 (fatia 5):** a rede decide o momento do lembrete da pausa (lembrar × esperar, teto de 15 min); aceitar o lembrete recompensa a rede na hora. Aba Cérebro com "Lembrar × esperar". As regras automáticas por processo/ócio e a opção em Ajustes foram removidas. O `cerebro.npz` antigo (formato 1) é guardado como `cerebro.recusado-*` e a rede recomeça.
- Pet com atividades: ao aceitar a pausa ele descansa (olhos fechados, respirando) com a contagem regressiva no rosto; ao clicar em "Bebi" ele bebe por 15 s com um copo esvaziando.
- `pulso --criar-atalho`: atalho "Pulso" no Menu Iniciar (sem console, com o rostinho como ícone) para reabrir o app depois de sair.
- Janela do pet: botões secundários menores, pomodoro em ícones (▶ ⏸ ⏭) e dicas dos botões faladas pelo pet ao passar o mouse; ícone de pausa visível no modo escuro do Windows.
- Fundação do projeto: `pyproject.toml`, layout `src/pulso/`, comando `pulso --version`, testes e CI (etapa 0).
- Sensores de nível B (CPU, RAM, hora, ociosidade, categoria do programa em primeiro plano e trocas por minuto),
  relógio injetável, laço mínimo com pausa de privacidade e `pulso --print-sensors` (etapa 1).
- Cérebro sem aprendizado: neurônio LIF, rede de pulso em numpy (entrada de Poisson, oculta 80E+20I, saída com
  inibição lateral), contrato `Engine`, codificador, decodificador com histerese e
  `pulso --print-brain [--fake-sensors]` (etapa 2). Custo medido: 1,6 ms por segundo real.
- Aprendizado: STDP com rastro de elegibilidade e dopamina como erro de previsão (R-STDP) na oculta→saída,
  `Engine.reward`, regras de recompensa (dono e automáticas, com filtro de cliques repetidos),
  `cerebro.npz` com versão e gravação atômica, `AutoSaver` e semente guardada (etapa 3).
  Custo medido: 2,7 ms por segundo real. Limitação conhecida: 1 de 6 sementes não aprende o cenário de teste.
- O pet aparece: janela PySide6 com o rosto desenhado em QPainter (5 humores e "dormindo", transições suaves,
  piscar e olhar de lado), balão de fala, botões Carinho, Bronca e Pausa (só ícone), janela no tamanho mínimo, selo
  de pausa (só aparece pausado), legenda do humor, reação ao carinho/bronca, boas-vindas no primeiro uso, tema claro/escuro do Windows e `PetController`
  (o laço de 1 s sem Qt). `pulso` abre a janela (`--fake-sensors` usa o roteiro falso) (etapa 4).
- Aba **Cérebro** (pyqtgraph): raster de pulsos por camada, potencial de 3 neurônios, dopamina com a cor de quem a deu,
  pulsos por humor, mapa de pesos (com modo "só o que mudou"), ❓ em cada gráfico, congelar/continuar, Ctrl+1/Ctrl+2
  e rodapé com o custo da rede. `Engine.snapshot()` e `Engine.reward` devolvendo a dopamina (etapa 5). Custo medido:
  ~13 ms por volta de 1 s com a aba visível e nenhum a mais com ela escondida ou a janela minimizada.
- Hábitos: **pomodoro** (foco 50 / descanso 10, longo 20 a cada 4 ciclos; iniciar, pausar, pular), **lembrete de água**
  (60 min) com Bebi · Depois · Hoje não, notificação do Windows e `pulso.db` (SQLite com migração v1). Recusar ou
  ignorar acumula **pendência**; com 3 pontos ou mais o pet fica **nervoso** até o dono dizer que fez. O ócio adia o
  lembrete e o pomodoro é independente da pausa de privacidade (etapa 6).
- Bandeja do Windows: ícone sempre visível com menu (mostrar, sempre à frente, lembrete de água, iniciar com o Windows,
  pausar observação, pomodoro, sair). **Fechar a janela (X) esconde o pet na bandeja** e ele segue com os avisos; "Sair do
  Pulso" encerra de verdade. A janela fica **sempre à frente** por padrão. Preferências em `config.toml`; "iniciar com o
  Windows" pela chave `Run` do usuário.

### Alterado
- Aba "Pet" virou "Pulso"; o botão Bronca saiu (o Carinho só reage). Com a observação pausada o foco congela (sem leitura não há presença). Refeição conta como descanso longo, mas a rede só aprende com pausa e foco.
- README com capa, fases da janela, fluxo do humor e blocos de atualização.

- Recompensas só por resposta do dono: as regras por processo/ócio ficam desligadas por padrão (ligáveis em Ajustes) e os hábitos (bebi, fiz a pausa, hoje não) pesam como carinho e bronca.
- A barra de abas ganhou "Jogo" e o botão ⚙ (Pet · Jogo · Cérebro; Ctrl+1/2/3).
- A barra de abas aparece (Pet · Cérebro); a janela cresce ao abrir o Cérebro e volta ao tamanho do pet.
- `Engine.reward` passa a devolver a dopamina entregue (`value − r̄`).
- Primária clara escurecida de `#0F8A7E` para `#0D7F74`: o texto branco do botão dava 4,24:1 (mínimo 4,5:1).
- `pulso` sem argumentos agora abre o app (antes imprimia a ajuda).

### Removido
- `habits/pomodoro.py` e o botão Iniciar: o foco abre sozinho.
