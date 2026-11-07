# Etapa 7 — O momento certo (diário)

> Em andamento. Este diário cobre a **fatia 3**: ligar o ciclo do foco ao app e construir a janela D.

## O que foi feito
- `HabitCoach` virou o ponto único: tem o `FocusCycle` e a `Water`, grava os eventos (com categoria e resumo da
  pausa) e devolve um `HabitTick` com o que foi gravado, o que a tela deve avisar, o que a rede aprende e o resumo.
- O controlador lê o sensor de reunião só quando a observação está ligada.
- A aba Pulso ganhou o anel do foco, a pílula de modo e um painel por fase; Ajustes ganhou modo e tolerância; a
  bandeja ganhou "Modo casual" e o submenu "Foco". O `Pomodoro` antigo foi removido.

## Conceitos aprendidos
- **Máquina de estados + relógio injetado:** o ciclo não olha o relógio do sistema, recebe um `Clock`. Nos testes o
  tempo é falso e avança de 1 em 1 s, então 50 minutos de foco rodam em milissegundos.
- **Um só lugar grava:** só o `HabitCoach` escreve no banco; as máquinas apenas *decidem*. Isso evita eventos
  duplicados e deixa a pendência (calculada dos eventos gravados) sempre coerente.
- **Dado ausente não é zero:** com a observação pausada o sensor devolve `None`; o ciclo congela em vez de supor
  que o dono saiu. Por isso o foco para quando você pausa a observação.
- **Recompensar só o que ensina:** refeição conta como descanso longo, mas a rede não aprende com ela (`rewarded`).

## Tropeços (para não repetir)
- **QSS:** `border-radius` maior que metade da altura vira quadrado; a pílula precisou de `min-height`.
- **Altura da janela:** subir `setMinimumSize` já cresce a janela; calcular o alvo antes.
- **Captura de tela:** `QT_QPA_PLATFORM=offscreen` não tem fontes (quadradinhos); capturar com fontes reais.
- **Heredoc grande no shell** quebrou por causa de aspas: gravar o script num arquivo e rodar.
- **Testes de água** esbarravam no lembrete da pausa (o ciclo fala primeiro): rodam em modo Casual.

## Como testar
- `pytest` (372, ~1,5 min). Ver no app sem mexer nos seus dados:
  `$env:PULSO_DATA_DIR = "$env:TEMP\pulso-teste"; pulso --fake-sensors`.

## Fora desta fatia
- Horário de almoço opcional em Ajustes; rede (fatia 5).

## Fatia 4 — humor por regras e prorrogação que pesa mais
**Conceito: explicável × aprendido.** Uma regra (`se pendência então nervoso`) sempre dá a mesma resposta e dá para dizer
o porquê; uma rede de pulsos aprende e surpreende, mas não sabe explicar. Por isso o rosto passou a seguir regras
(`habits/mood_rules.py`, função pura: números entram, humor e causa saem) e a rede ficou com o que vale aprender: o
**momento** do lembrete (fatia 5).

- **Prioridade (a primeira que vale ganha):** pendência → nervoso · lembrete prorrogado → preocupado · parado há 5 min ou
  mais → sonolento · pausa no horário ou copo hoje → contente · senão neutro.
- **Motivo sempre à vista:** a legenda sob o rosto diz a causa; o balão fala na virada (a 1ª prorrogação é normal e não fala).
- **Prorrogar pesa mais a cada vez** na recompensa da rede: −0,25, −0,5, −0,75 e −1,0 (o teto é o peso de uma recusa).
- **Armadilha:** a chave "mudou o humor?" precisou incluir o número da prorrogação, senão a 2ª não falava.
- **Como testar:** `pytest` (400). `tests/habits/test_mood_rules.py` tem um teste por regra e um para a prioridade.

## Fatia 5 — a rede decide o momento do lembrete
**Conceito: o que uma rede pode aprender de verdade.** Antes a rede escolhia o humor do rosto, e ninguém corrigia essa
escolha. Agora ela decide algo que o dono confirma o tempo todo: *lembrar da pausa agora ou esperar?* Aceitar é
recompensa, prorrogar ou recusar é punição. Dois grupos de saída (`lembrar`, `esperar`) competem por inibição lateral,
como antes, só que com duas opções em vez de cinco.

- **Crédito atrasado:** a dopamina só reforça o que disparou há pouco (cerca de 10 s). Por isso aceitar o lembrete vira
  recompensa **na hora** (`BREAK_ACCEPTED`), não só no fim da pausa, minutos depois, quando a rede já esqueceu.
- **Teto de 15 min:** a rede pode adiar, mas nunca esconder o lembrete. Se o teto estoura, o aviso toca e a resposta
  vale **ao contrário**: aceitar mostra que esperar foi erro; recusar, que foi acerto. Sem isso, o aceite reforçaria o
  próprio grupo "esperar", que era quem estava ganhando.
- **Rede sem treino = comportamento antigo:** se a rede cala ou empata, vence "lembrar" (`MoodDecoder(fallback=…)`).
- **Cérebro antigo:** o formato mudou (5 grupos → 2); o arquivo velho é guardado como `cerebro.recusado-*`, nunca apagado.
- **Removido:** as 3 regras automáticas por processo/ócio e a opção em Ajustes (eram palpites que o dono nunca confirmava).
- **Teste de aprendizado:** 3 contextos, 3 sementes que começam errando; depois de 120 rodadas a rede espera onde o dono
  recusa e lembra onde aceita (≥ 80%), inclusive depois de salvar e reabrir.
- **Como testar:** `pytest` (408). Ver no app: `$env:PULSO_DATA_DIR = "$env:TEMP\pulso-teste"; pulso --fake-sensors`.
- **Ainda falta:** ver na tela real; tag v0.7.0; sensor de interação, horário de almoço, ícone da barra de tarefas,
  instalador, "About" do GitHub, `habitos.png`.

