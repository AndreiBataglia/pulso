# PRD — Pulso

> Documento de Requisitos do Produto: **o que** estamos construindo e **para quem**.
> Última revisão: 2026-11-05

## 1. Resumo da ideia
**Pulso** é um companheiro de desktop para Windows: um "bichinho" que mora numa janela de painel, observa
**de forma discreta** como o computador está sendo usado (carga da máquina, tipo de programa em uso, tempo
ocioso) e reage com estados de humor. O "cérebro" dele é uma **rede neural de pulso** (SNN — *spiking neural
network*, rede em que os neurônios se comunicam por pulsos elétricos curtos, como os do cérebro) que aprende
por **reforço**: carinho e bronca do usuário e as respostas aos hábitos (bebi, fiz a pausa, hoje não) funcionam
como "dopamina". As regras automáticas por processo/ócio (palpites sobre o humor) ficam **desligadas por padrão**
(decidido em 2026-11-06) e podem ser ligadas em Ajustes.
Ele também cuida de hábitos saudáveis: **pomodoro** (blocos de foco com descanso) e **lembrete de beber água**.
É um projeto **público no GitHub** (licença MIT), construído em etapas documentadas para servir de material de
aprendizado.

## 2. Problema e motivação
- Quem passa o dia no computador esquece de pausar e de beber água; os apps de lembrete são "frios" e acabam
  silenciados.
- Um companheiro com personalidade, que **aprende** o gosto do dono, torna os lembretes mais simpáticos.
- O usuário quer **aprender SNN e aprendizado por reforço na prática**, construindo algo próprio. Inspiração: o
  DeskBuddy (reel de Reagan, Acervo do hub, 2026-11-04), cujo código nunca foi liberado.

## 3. Público e usuários
| Perfil | Quem é | O que precisa fazer no app |
|--------|--------|----------------------------|
| Dono | O usuário, no PC Windows pessoal ou do trabalho | Ver o pet, dar carinho/bronca, pausar a observação, usar pomodoro e lembrete de água, ver o cérebro funcionando |
| Visitante do GitHub | Quem encontra o repositório | Entender o projeto pelo README e pelo diário das etapas, instalar e rodar |

Uso: um usuário por instalação, roda em segundo plano o dia todo, **100% local** (sem internet, sem servidor).

## 4. Objetivos e métricas de sucesso
- Rodar o dia todo usando **menos de 3% de CPU** e **menos de 200 MB de RAM** em média.
- Depois de ~1 semana de uso, o humor do pet **acompanha o contexto** na maior parte do tempo: sonolento no
  ócio longo, animado na volta, preocupado após muito tempo sem pausa. Medido pela fração de recompensas
  positivas no painel de cérebro.
- O usuário consegue explicar, com o diário das etapas, como um neurônio LIF e o STDP com dopamina funcionam.
- Cada etapa publicada no GitHub com diário, CHANGELOG e tag de versão.

## 5. Escopo

### 5.1 Funcionalidades — MVP (primeira versão)

#### F01 — Sensores do PC (nível B)
- **Descrição:** a cada 1 s lê **só metadados**: uso de CPU e RAM, hora do dia, segundos desde a última
  entrada de teclado/mouse (ociosidade), **categoria** do programa em primeiro plano (código, navegador, vídeo,
  chat, escritório, jogo, outro) e quantas trocas de programa houve no último minuto.
- **Usuário:** Dono
- **Critérios de aceite:**
  - [ ] A categoria vem do **nome do processo** (ex.: `code.exe` → código), por uma tabela editável; o
        **título da janela nunca é lido**.
  - [ ] Nenhum dado bruto de sensor é gravado em disco; só alimenta a rede na memória.
  - [ ] Programa desconhecido cai em "outro", sem erro.
- **Prioridade:** Alta

#### F02 — Pausa de privacidade (manual)
- **Descrição:** o dono decide que o momento é sensível e manda o Pulso parar de observar, por um botão no
  painel, pelo ícone da bandeja ou por um atalho global de teclado.
- **Critérios de aceite:**
  - [ ] Pausado, **os sensores param de verdade** (não leem nada) e o pet mostra o estado "olhos fechados".
  - [ ] Pausado, nada novo é aprendido nem registrado.
  - [ ] Retomar é manual, pelo mesmo controle. *Suposição:* opção de retomar sozinho após N minutos,
        desligada por padrão.
  - [ ] O atalho global é registrado sem monitorar o teclado (não é *keylogger*).
- **Prioridade:** Alta

#### F03 — Cérebro SNN (neurônios LIF)
- **Descrição:** rede de ~200 neurônios LIF (*leaky integrate-and-fire*: o neurônio acumula carga, vaza um
  pouco a cada instante e dispara um pulso quando passa de um limiar). Os sensores viram **pulsos de entrada**,
  e grupos de neurônios de saída competem para escolher o humor.
- **Critérios de aceite:**
  - [ ] A cada leitura dos sensores, a rede simula 100 ms do tempo dela (passo de 1 ms).
  - [ ] A cada 10 s o grupo de saída que mais disparou define o humor exibido.
  - [ ] O motor fica atrás de uma interface comum (`Engine`), que permite trocar por outro motor que aprende
        online sem mexer no resto (ver TRD §5).
  - [ ] Os testes provam um LIF isolado disparando na frequência esperada para uma corrente conhecida.
- **Prioridade:** Alta

#### F04 — Aprendizado por reforço (STDP + dopamina)
- **Descrição:** as sinapses aprendem por **R-STDP** (STDP modulado por recompensa). O STDP marca as sinapses
  que participaram de um disparo (*rastro de elegibilidade*), e a dopamina que chega logo depois decide se elas
  fortalecem (recompensa positiva) ou enfraquecem (negativa).
- **Fontes de recompensa (as duas juntas):**
  - **Do dono:** botões 💚 Carinho (+1) e 💢 Bronca (−1).
  - **Regras automáticas** (comportamento mínimo desde o início), por exemplo: sonolento durante ócio longo
    (+), animado ao voltar do ócio (+), preocupado após mais de 90 min sem pausa (+), lembrete atendido (+),
    lembrete dispensado (−).
- **Critérios de aceite:**
  - [ ] Num cenário simulado de teste (sem PC real), depois de N recompensas a rede passa a preferir o humor
        recompensado no contexto dado.
  - [ ] A recompensa do dono pesa mais que a das regras (pesos configuráveis).
  - [ ] Os pesos aprendidos ficam salvos e sobrevivem ao fechar e reabrir o programa.
- **Prioridade:** Alta

#### F05 — Pet no painel
- **Descrição:** a janela principal mostra o pet desenhado, com 5 humores — **animado, contente, entediado,
  sonolento, preocupado** — mais "dormindo" (pausa de privacidade). Cada humor tem uma expressão e uma frase
  curta.
- **Critérios de aceite:**
  - [ ] A troca de humor é animada (transição curta), sem piscar a cada segundo.
  - [ ] Os botões Carinho e Bronca dão um retorno visual imediato.
- **Prioridade:** Alta

#### F06 — Painel do cérebro (aprender vendo)
- **Descrição:** uma aba mostra a rede funcionando: gráfico de pulsos (*raster*, um ponto por disparo), o
  potencial de alguns neurônios, o nível de dopamina e o mapa de pesos.
- **Critérios de aceite:**
  - [x] (2026-11-06) Os gráficos atualizam em tempo real sem travar a interface (~13 ms por volta de 1 s).
  - [x] (2026-11-06) Com a aba fechada ou a janela minimizada, os gráficos não consomem CPU (testado: nem a fotografia é pedida).
- **Prioridade:** Média

#### F07 — Pomodoro (sugestão de descanso)
- **Descrição:** ciclos de foco e descanso (padrão 50/10, com descanso longo de 20 min a cada 4 ciclos; decidido em 2026-11-06). O pet
  avisa a hora de descansar e a de voltar.
- **Critérios de aceite:**
  - [ ] Iniciar, pausar e pular pelo painel e pela bandeja.
  - [ ] O aviso aparece como notificação do Windows e na fala do pet.
  - [ ] O pomodoro é **independente** da pausa de privacidade: descansar não desliga a observação.
- **Prioridade:** Alta

#### F08 — Lembrete de água
- **Descrição:** a cada X minutos (padrão 60) o pet pede água. O dono responde "Bebi 💧", "Depois" ou "Hoje não" (e "Bebi" / "Fiz a pausa" ficam sempre visíveis na aba Pet).
- **Critérios de aceite:**
  - [ ] "Bebi" soma um copo no dia; "Depois" adia 10 min.
  - [ ] **Decidido pelo dono (2026-11-06) — pendência cumulativa:** o Pulso registra se o dono **fez**, **adiou**,
        **recusou** ou **ignorou** o lembrete. Recusar e ignorar **acumulam**; só "fiz" (Bebi / Fiz a pausa) zera. Quanto
        maior a pendência, mais **nervoso** o pet fica, e **ele não muda desse humor até o dono admitir** que fez a pausa
        ou bebeu água. Os intervalos de água/descanso são revistos com o uso real (ver etapa 6 do plano).
  - [ ] Durante o ócio (dono longe do PC), o lembrete espera a volta.
- **Prioridade:** Alta

#### F09 — Resumo de saúde
- **Descrição:** aba com copos de água, pomodoros concluídos e maior sequência sem pausa, do dia e dos últimos
  7 dias.
- **Critérios de aceite:**
  - [ ] Os dados vêm só dos eventos de hábito (F07/F08), nunca dos sensores.
  - [ ] Aviso visível: "lembretes de hábito, não é orientação médica".
- **Prioridade:** Média

#### F10 — Configurações e bandeja
- **Descrição:** ícone na bandeja do Windows (abrir, pausar observação, pomodoro, sair) e tela de ajustes:
  intervalos, tabela de categorias, atalho de pausa, pesos das recompensas, iniciar com o Windows.
- **Critérios de aceite:**
  - [ ] Fechar a janela minimiza para a bandeja; "Sair" encerra e salva o cérebro.
  - [ ] Valor inválido nos ajustes é recusado com mensagem no campo.
- **Prioridade:** Média

#### F11 — Projeto público e documentado no GitHub
- **Descrição:** repositório público, licença MIT, README bem descrito, CI (testes automáticos a cada push) e um
  **diário por etapa** que explica o que foi feito e os conceitos aprendidos.
- **Critérios de aceite:**
  - [ ] Cada etapa termina com diário em `docs/diario/`, entrada no `CHANGELOG.md`, tag `v0.N` e push,
        sempre com autorização do dono.
  - [ ] O CI roda os testes e o *lint* no Windows a cada push, e o selo aparece no README.
  - [ ] Nenhum dado pessoal (cérebro salvo, banco, logs) entra no repositório (`.gitignore`).
- **Prioridade:** Alta

### 5.2 Depois do MVP
- F15 (feito, 2026-11-06) — **Jogo do dia a dia:** jokenpô e par ou ímpar com o pet (aba Jogo). Ganhou, ele fica contente;
  perdeu, fica bravo. Só mexe no rosto e no placar do dia, nunca na rede (o resultado é sorte e viraria ruído).
- F16 (feito, 2026-11-06) — **Ajustes:** tempos do pomodoro e da água e o interruptor das regras automáticas.
- F12 — A SNN aprende **quando e como** lembrar (adiar se o dono está focado), em vez de intervalos fixos.
- F13 — Nível C de observação: ritmo de digitação e cliques (contagem, nunca as teclas).
- F14 — Outros lembretes de hábito: descanso dos olhos 20-20-20, postura, alongamento.
- F15 — Motor alternativo com treino offline (snnTorch/Norse, por gradiente), com modo de treino separado.
- F16 — Motor Brian2 pela mesma interface `Engine`, para comparar.
- F17 — Pet em pixel art com animações; janela flutuante opcional.
- F18 — Suporte a Linux/macOS (só a camada de sensores muda).
- F19 — Fala gerada por IA local (opcional, sem depender do hub).

### 5.3 Fora do escopo
- Capturas de tela, leitura do título das janelas, conteúdo digitado, histórico de navegação.
- Qualquer envio de dados pela internet (telemetria, nuvem, contas).
- Diagnóstico ou orientação médica.
- Integração com o hub_service (decisão do dono: projeto independente).

## 6. Requisitos não funcionais
- **Privacidade:** tudo local; sensores só de metadados; pausa manual real; dados brutos nunca persistidos.
- **Desempenho:** < 3% de CPU e < 200 MB de RAM em média; a interface nunca trava por causa da simulação.
- **Robustez:** fechar de forma inesperada perde no máximo 5 min de aprendizado (salvamento periódico).
- **Idioma:** interface e documentação em português (Brasil); resumo em inglês no topo do README.
- **Didática:** código de alto nível e muito comentado, explicando o "porquê" de cada parte da rede.

## 7. Suposições
- Nome público **"Pulso"**: o dono pediu um nome próprio para o pet; trocar é um grep no repositório.
- Escala de ~200 neurônios no MVP (faixa planejada: 100–500).
- Windows 10/11 primeiro; outros sistemas depois (F18).
- 5 humores, mais "dormindo".
- Intervalos padrão (decididos em 2026-11-06): pomodoro 50/10/20, água a cada 60 min.

## 8. Perguntas em aberto
- O nome "Pulso" está bom? — responsável: dono
- Retomar a observação sozinho após N minutos deve existir (desligado por padrão) ou nunca? — responsável: dono
- A frase do pet em cada humor: fixa (lista de frases) no MVP, IA local só no F19. Confirmar. — responsável: dono

## Histórico de revisões
| Data | Mudança |
|------|---------|
| 2026-11-05 | Versão inicial |
