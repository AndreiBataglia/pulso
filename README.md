# Pulso

[![CI](https://github.com/AndreiBataglia/pulso/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreiBataglia/pulso/actions/workflows/ci.yml)
![Python 3.13](https://img.shields.io/badge/python-%E2%89%A53.12-blue)
![Windows](https://img.shields.io/badge/plataforma-Windows-lightgrey)
[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-green)](LICENSE)

![Pulso: o foco, o lembrete da pausa e o descanso](docs/img/capa.png)

**Status: em construção.** Já funcionam: os sensores, a rede que aprende, o Pulso na janela, a aba do cérebro,
hábitos (foco por presença, pausas e água), bandeja do Windows, ajustes e um jogo. A etapa 7 (*O momento certo*)
está em andamento: o ciclo do foco e a janela nova já existem; faltam o humor por regras e a rede decidir *quando*
lembrar. Depois vêm a aba de saúde, o atalho global e o instalador.

## English

Pulso is a Windows desktop companion driven by a small spiking neural network
(leaky integrate-and-fire neurons with reward-modulated STDP, written in plain numpy).
It learns your rhythm from coarse signals only (CPU, RAM, time, idle time, foreground process name),
and helps you build routine: a focus cycle that starts by itself when you are at the PC, break reminders
and water reminders. It never reads keystrokes or window titles.

## Português

Pulso é um companheiro de desktop para Windows, movido por uma pequena rede neural de pulso
(neurônios LIF com R-STDP, em numpy puro). Ele aprende o seu ritmo a partir de sinais grosseiros
e ajuda você a criar rotina: foco, pausas e água. O projeto também é um diário de aprendizado: cada etapa
explica os conceitos usados em [`docs/diario/`](docs/diario/).

## Como o Pulso ajuda

O foco é **criar rotina sem ser chato**. O Pulso pergunta, você responde; ele nunca bloqueia nem controla a tela.

![As seis fases da janela do Pulso: foco, lembrete da pausa, descanso, voltou (o que foi?), reunião e modo casual](docs/img/fases.png)

- **O foco começa sozinho.** Não existe botão *Iniciar*: quando você mexe no PC, o foco abre (50 min por padrão) e o
  anel em volta do rosto mostra o andamento. A pílula **Profissional / Casual** troca o modo.
- **Lembrete da pausa.** Ao fim do foco: **Pausar agora**, **Prorrogar 5 min** ou **Hoje não**. Pausa no horário
  deixa o Pulso contente; recusar ou ignorar soma pendência e o deixa nervoso.
- **Descanso.** O rosto descansa com a contagem. Se passar do combinado, ele só conta quanto, sem bronca.
- **"O que foi?"** Quando você volta de uma ausência, o Pulso pergunta: *pausa*, *refeição*, *necessidade* ou
  *foco sem mexer*. Refeição e necessidade nunca o deixam nervoso, e sem resposta conta como pausa.
- **Reunião.** Microfone em uso por outro programa **pausa** o foco, sem penalizar, e ele continua de onde parou.
  A câmera e o microfone nunca são usados como sensor de presença.
- **Modo casual.** Sem ciclo de foco: só o lembrete de água.
- **Água.** *Bebi* faz o Pulso beber com você. O placar do dia fica no rodapé (pausas, prorrogações, copos, focos).
- **Você manda nos tempos.** Em **Ajustes** (⚙ ou menu da bandeja): foco, descansos, intervalo da água, modo e
  quanto tempo parado conta como ausente.
- **O Pulso vive na bandeja do Windows**, com avisos, pode iniciar com o Windows (abrindo só na bandeja), ficar
  sempre à frente e ser reaberto pelo Menu Iniciar. Sair de vez é pelo ícone da bandeja.
- **Um jogo para o dia a dia.** Na aba **Jogo**, jokenpô e par ou ímpar: se o Pulso ganha, fica contente; se perde,
  fica bravo. O resultado muda só o rosto e o placar, nunca a rede.

## A rede de pulso

O Pulso aprende com o que **você** faz e responde, não com palpites: cada carinho, *Bebi*, pausa feita ou *Hoje não*
vira um sinal de recompensa (dopamina) para a rede. Existem também recompensas automáticas, que tentam adivinhar se
você se cuidou olhando só o nome do programa em uso e o tempo parado. Como são palpites que você nunca confirma, elas
vêm **desligadas** e só funcionam se você ligá-las em Ajustes.

![Os seis rostos do Pulso: animado, contente, entediado, sonolento, preocupado e nervoso (e dormindo, quando a observação está pausada)](docs/img/humores.png)

A aba **Cérebro** mostra a rede por dentro: raster de pulsos, potenciais, dopamina, humor e mapa de pesos.

![A aba Cérebro: raster de pulsos, potenciais, dopamina, humor e mapa de pesos (roteiro de sensores falso)](docs/img/cerebro.png)

### Como o humor funciona

O rosto mostra **um humor por vez**, e a legenda embaixo diz o motivo. Quem escolhe é um conjunto de **regras
explicáveis** (a primeira que vale ganha); a rede de pulsos não escolhe a cara:

```mermaid
flowchart TD
    PV{"Observação<br/>pausada?"} -- sim --> Z["😴 Dormindo"]
    PV -- não --> R1

    R1{"Pendência alta?<br/>recusou ou ignorou<br/>vezes demais"} -- sim --> NV["😠 Nervoso<br/>até você dizer que fez"]
    R1 -- não --> R2{"Prorrogou o<br/>lembrete da pausa?"}
    R2 -- sim --> PR["😟 Preocupado<br/>(conta as prorrogações)"]
    R2 -- não --> R3{"Parado há 5 min<br/>ou mais?"}
    R3 -- sim --> SO["😴 Sonolento"]
    R3 -- não --> R4{"Pausa no horário<br/>ou água hoje?"}
    R4 -- sim --> CO["🙂 Contente"]
    R4 -- não --> NE["😐 Neutro<br/>nada pendente"]

    NV --> F["Rosto + legenda<br/>com o motivo"]
    PR --> F
    SO --> F
    CO --> F
    NE --> F
    Z --> F

    G["Aba Jogo"] -. "reação passageira:<br/>ganhou contente, perdeu bravo" .-> F

    S["Sensores (nível B)<br/>CPU, RAM, hora, ociosidade,<br/>nome do processo"] --> E["Codificador<br/>vira taxas de pulso"]
    E --> N["Rede de pulso<br/>LIF + R-STDP"]
    N --> D["Humor da rede<br/>só na aba Cérebro"]
    D -. "fatia 5: decide o<br/>momento do lembrete" .-> L["Lembrete de pausa"]

    A["Suas respostas<br/>Bebi e Pausa feita +1 · Hoje não −1<br/>ignorou −0,5 · prorrogar −0,25 a −1"] -- dopamina --> N
    A -. "Bebi e Pausa feita<br/>zeram a pendência" .-> R1
```

- **As regras decidem o rosto**, nesta ordem: pendência → nervoso; lembrete prorrogado → preocupado; parado há 5 min
  ou mais → sonolento; pausa no horário ou copo hoje → contente; senão neutro.
- **A rede continua aprendendo** com o que **você** responde (setas de dopamina), mas hoje o humor dela só aparece na
  aba Cérebro. Na fatia 5 ela passa a decidir *quando* lembrar.
- **Nervoso** nasce de recusar ou ignorar lembretes; só um *fiz* zera a pendência (*depois* vale 0). O balão diz o
  motivo: água, pausa ou as duas.
- **Prorrogar pesa mais a cada vez** na recompensa da rede: −0,25, −0,5, −0,75 e −1,0.
- **Pausar a observação** põe o Pulso para dormir e congela o foco.
- **Refeição e necessidade** (a pergunta "o que foi?") nunca somam pendência, e a rede só aprende com pausa e foco.

*In English:* the window has one panel per phase (focus, break reminder, rest, "what happened?" after an absence,
meeting, casual mode). The network learns from your own answers; the process-based guesses are off by default.
A microphone in use by another program pauses focus without penalty. Timers, mode and the away tolerance are
configurable in Settings, the companion lives in the tray, and a small rock-paper-scissors / odds-and-evens game
changes only its face, never the network.

## Atualizações

> Resumo por versão. O detalhe está no [`CHANGELOG.md`](CHANGELOG.md) e, com os conceitos explicados, em [`docs/diario/`](docs/diario/).

### Etapa 7 · O momento certo *(em andamento, PR #10)*
- **Foco por presença:** o ciclo abre sozinho quando você mexe no PC (sem botão *Iniciar*), com anel de andamento no rosto.
- **Pausar agora · Prorrogar 5 min · Hoje não**, e o placar do dia no rodapé (pausas, prorrogações, copos, focos).
- **"O que foi?"** na volta de uma ausência: pausa, refeição, necessidade ou foco sem mexer.
- **Reunião:** microfone em uso por outro programa pausa o foco, sem penalizar. Nada de som ou imagem é capturado.
- **Modos Profissional e Casual**, pela pílula da janela ou pelo menu da bandeja.
- **Janela nova** (direção D do design): um painel por fase, aba **Pulso** (antes "Pet") e **sem o botão Bronca**.
- **Ajustes** ganharam modo e "parado por mais de (min)". O banco migrou para o esquema v3 (categoria e resumo das pausas).
- Saiu o pomodoro antigo. *Vem a seguir:* humor por regras explicáveis e a rede decidindo *quando* lembrar.

### v0.6.0 · Hábitos, bandeja, ajustes e jogo
- Pomodoro e lembrete de água com notificação do Windows; recusar ou ignorar soma pendência e deixa o Pulso nervoso.
- Bandeja do Windows (o X esconde o Pulso), iniciar com o Windows, sempre à frente e atalho no Menu Iniciar.
- Aba **Ajustes** com os tempos; aba **Jogo** (jokenpô e par ou ímpar, só muda o rosto).
- O Pulso aprende só com as suas respostas; as regras por processo ficam desligadas por padrão.

### v0.5.0 e antes · A base
- **v0.5.0:** aba **Cérebro** com raster, potenciais, dopamina, humor e mapa de pesos.
- **v0.4.0:** o Pulso aparece na janela (rosto em QPainter, balão, carinho).
- **v0.3.0:** aprendizado R-STDP com dopamina; **v0.2.0:** rede de pulso LIF em numpy; sensores de nível B e CI desde o início.

## Privacidade

Os sensores leem apenas metadados: CPU, RAM, hora, ociosidade e o **nome do processo** em primeiro plano.
O título da janela, o conteúdo da tela e as teclas **nunca** são lidos. Existe uma pausa de
privacidade que desliga os sensores (o foco congela junto, porque sem leitura não há como saber se você está lá).
Dados de sensor não são gravados em disco nem no log.

## Instalação (desenvolvimento)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pulso --version
pytest
pulso --criar-atalho   # cria o atalho "Pulso" no Menu Iniciar (para abrir de novo depois de sair)
```

Para ver o app sem mexer nos seus dados e sem ler sensores de verdade:

```powershell
$env:PULSO_DATA_DIR = "$env:TEMP\pulso-teste"; pulso --fake-sensors
```

Para sair de vez: botão direito no ícone da bandeja → **Sair do Pulso**. O X da janela só manda para a bandeja.

## Documentação

Veja [`docs/README.md`](docs/README.md): PRD, TRD, fluxo, design, dados e plano de implementação.

## Licença

[MIT](LICENSE)
