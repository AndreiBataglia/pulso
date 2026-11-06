# Pulso

[![CI](https://github.com/AndreiBataglia/pulso/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreiBataglia/pulso/actions/workflows/ci.yml)

**Status: em construção (v0.6.0: sensores, rede que aprende, o pet na janela, a aba do cérebro, hábitos (pomodoro e água), bandeja do Windows, ajustes e um jogo; faltam a aba de saúde, o atalho global e o instalador).**

![Os seis rostos do Pulso: animado, contente, entediado, sonolento, preocupado e dormindo](docs/img/humores.png)

![A aba Cérebro: raster de pulsos, potenciais, dopamina, humor e mapa de pesos (roteiro de sensores falso)](docs/img/cerebro.png)

## English

Pulso is a Windows desktop companion driven by a small spiking neural network
(leaky integrate-and-fire neurons with reward-modulated STDP, written in plain numpy).
It learns your rhythm from coarse signals only, and helps with a Pomodoro timer and water reminders.

## Português

Pulso é um companheiro de desktop para Windows, movido por uma pequena rede neural de pulso
(neurônios LIF com R-STDP, em numpy puro). Ele aprende o seu ritmo a partir de sinais grosseiros
e ajuda com pomodoro e lembrete de água. O projeto também é um diário de aprendizado: cada etapa
explica os conceitos usados em `docs/diario/`.

## Foco neste momento

O foco do Pulso agora é **ajudar você a criar rotina** (pausar e beber água) sem ser chato. O que mudou na v0.6.0:

- **O pet aprende com o que você responde, não com o que adivinha.** Carinho, bronca e as respostas aos hábitos
  (*bebi*, *fiz a pausa*, *hoje não*) são a recompensa da rede. As regras que tiravam conclusões do programa em uso
  ficaram **desligadas por padrão** (dá para ligá-las em Ajustes), porque eram palpites que você nunca confirmava.
- **Cumprir deixa o pet contente; não cumprir deixa o pet nervoso.** Recusar ou ignorar lembretes soma pendência, e
  só um *fiz* a zera. Ao aceitar a pausa ele descansa com a contagem no rosto; ao clicar em *Bebi* ele bebe com você.
- **Você manda nos tempos.** Em **Ajustes** (⚙ ou menu da bandeja) escolha foco, descansos e o intervalo da água.
  O descanso só começa a contar quando você o aceita.
- **O pet não depende de você abrir a janela.** Fica na bandeja do Windows com avisos, pode iniciar com o Windows,
  ficar sempre à frente e ser reaberto pelo Menu Iniciar. Sair de vez é pelo ícone da bandeja.
- **Um jogo para o dia a dia.** Na aba **Jogo**, jokenpô e par ou ímpar: se o pet ganha, fica contente; se perde,
  fica bravo. O resultado muda só o rosto e o placar, nunca a rede (é sorte, e viraria ruído no aprendizado).

O que o Pulso **não** faz de propósito: não vê o copo nem a pausa em si (só se você parou de mexer no PC) e não
bloqueia nem controla a tela. Ele pergunta, você responde.

**Próximos passos:** a aba de saúde, o atalho global de pausa, um instalador (`.exe`) e a rede decidir *quando*
lembrar (F12), aprendendo com as suas respostas.

*In English:* the current focus is helping you build routine. The network learns from your own answers
(petting, scolding, and *drank / took a break / not today*); the process-based guesses are off by default.
Timers are configurable in Settings, the pet lives in the tray, and a small rock-paper-scissors / odds-and-evens game
changes only its face, never the network.

## Privacidade

Os sensores leem apenas metadados: CPU, RAM, hora, ociosidade e o **nome do processo** em primeiro plano.
O título da janela, o conteúdo da tela e as teclas **nunca** são lidos. Existe uma pausa de
privacidade que desliga os sensores. Dados de sensor não são gravados em disco nem no log.

## Instalação (desenvolvimento)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pulso --version
pytest
pulso --criar-atalho   # cria o atalho "Pulso" no Menu Iniciar (para abrir de novo depois de sair)
```

Para sair de vez: botão direito no ícone da bandeja → **Sair do Pulso**. O X da janela só manda para a bandeja.

## Documentação

Veja [`docs/README.md`](docs/README.md): PRD, TRD, fluxo, design, dados e plano de implementação.

## Licença

[MIT](LICENSE)
