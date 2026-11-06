# Pulso

[![CI](https://github.com/AndreiBataglia/pulso/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreiBataglia/pulso/actions/workflows/ci.yml)

**Status: em construção (etapa 6 implementada: sensores, rede que aprende, o pet na janela, a aba do cérebro e os hábitos (pomodoro e água); faltam a saúde, os ajustes e a bandeja).**

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
