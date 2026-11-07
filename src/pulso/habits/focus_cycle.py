"""O ciclo do foco por presença (etapa 7): substitui o pomodoro de "clicar em Iniciar".

O foco é medido o tempo todo pela presença (segundos sem teclado nem mouse). Ninguém precisa
apertar nada para ele começar ou parar. Desenho: quadro "D · Ciclo completo" do canvas
(`docs/design/canvas/`).

    AGUARDANDO ─1ª entrada─▶ FOCO ─parado > tolerância─▶ AUSENTE ─voltou─▶ O QUE FOI?
                              │                                              │
                   mic em uso │ ▲ mic livre              pausa/refeição: foco novo
                              ▼ │                        necessidade/foco sem mexer: segue
                           REUNIÃO

    FOCO ─acabou─▶ LEMBRETE ─┬─ pausar agora / saiu da mesa ─▶ DESCANSO
                             ├─ prorrogar ─▶ FOCO (+5 min)
                             └─ hoje não ─▶ FOCO (novo)
    DESCANSO ─acabou, você está aqui─▶ FOCO
             ─acabou, ainda fora─▶ ALÉM DO DESCANSO (conta o excesso) ─voltou─▶ FOCO

Regras:
- **Tolerância:** parado menos que `away_idle_s` (5 min) ainda é foco. Passou disso, o foco **para
  no último gesto** (os minutos parados não contam) e a volta pergunta "o que foi?".
- **Reunião** (microfone em uso por outro programa) **congela** o foco: não conta, não penaliza e
  não gera pergunta na volta. Ao acabar, a ociosidade da reunião é esquecida.
- **Descanso:** mexer no PC não o encerra; só o fim do tempo (ou "voltar ao foco antes"). Se no fim
  você ainda está longe, conta-se o excesso, e o foco volta na primeira entrada.
- **Sair durante o lembrete** (1 min sem entrada) vale como pausa aceita, contada do último gesto.
- **Observação pausada** (`idle_s=None`): tudo congela, presença incluída.
- **Casual:** o ciclo fica desligado (só a água continua, fora daqui).

É lógica pura e testável: o tempo vem de um `Clock` injetado. Devolve acontecimentos
(`CycleEvent`): uns são gravados (`FOCUS_DONE`, `BREAK_DONE`...) e outros só avisam a interface
(`SHOW_BREAK`, `SHOW_ASK_BACK`, `SHOW_BACK`).
"""

from dataclasses import dataclass
from enum import Enum

from pulso.clock import Clock
from pulso.habits import kinds
from pulso.habits.kinds import HabitConfig

ENTRY_S = 5.0  # "mexeu agora": menos que isto sem entrada
LEAVE_S = 60.0  # no lembrete, tanto tempo sem entrada = saiu da mesa (aceitou a pausa)
ASK_TIMEOUT_S = 120.0  # "o que foi?" sem resposta, com você presente, vale como pausa
EXCESS_GRACE_S = 30.0  # passar do descanso por menos que isto não conta como excesso


class Mode(Enum):
    PROFESSIONAL = "profissional"
    CASUAL = "casual"


class Phase(Enum):
    OFF = "desligado"  # modo casual
    WAITING = "aguardando"
    FOCUS = "foco"
    AWAY = "ausente"
    ASKING_BACK = "o que foi?"
    REMINDER = "lembrete"
    BREAK = "descanso"
    BREAK_OVER = "além do descanso"
    MEETING = "reunião"


class AwayAnswer(Enum):
    """As respostas de "o que foi?" (e o valor gravado em `category`)."""

    PAUSE = kinds.CAT_PAUSE
    MEAL = kinds.CAT_MEAL
    NEED = kinds.CAT_NEED
    FOCUS = kinds.CAT_FOCUS


@dataclass(frozen=True)
class CycleEvent:
    """Um acontecimento do ciclo. Os campos extras só existem no resumo das pausas e das voltas."""

    kind: str
    category: str | None = None
    value: int | None = None  # em BREAK_DONE: quantas vezes o lembrete foi prorrogado antes
    planned_s: int | None = None
    actual_s: int | None = None
    excess_s: int | None = None


# Fases em que o dono pode anunciar uma refeição (o botão ao lado do modo).
MEAL_FROM = (Phase.WAITING, Phase.FOCUS, Phase.AWAY, Phase.ASKING_BACK, Phase.REMINDER)


class FocusCycle:
    def __init__(
        self, clock: Clock, cfg: HabitConfig | None = None, mode: Mode = Mode.PROFESSIONAL
    ) -> None:
        self._clock = clock
        self._cfg = cfg or HabitConfig()
        self.mode = mode
        self.phase = Phase.OFF if mode is Mode.CASUAL else Phase.WAITING
        self.long_break = False  # o descanso atual (ou o que vem) é o longo?
        self.postponements = 0  # quantas vezes o lembrete atual foi prorrogado
        self.last_absence_s = 0.0  # quanto durou a ausência que "o que foi?" pergunta
        self._cycles = 0  # focos concluídos desde o último descanso longo
        self._worked = 0.0  # segundos de foco acumulados
        self._target = self._cfg.focus_min * 60  # quando o lembrete aparece
        self._focus_counted = False  # FOCUS_DONE já gravado neste foco (prorrogar não repete)
        self._last = clock.now()
        self._last_gesture = clock.now()  # quando foi a última entrada, na ausência
        self._ref = float("-inf")  # ociosidade só vale depois daqui (fim da reunião)
        self._unanswered_s = 0.0  # tempo presente sem responder (lembrete ou "o que foi?")
        self._break_planned = 0.0
        self._break_elapsed = 0.0
        self._excess = 0.0
        self.meal = False  # o descanso atual é uma refeição que o dono anunciou?

    # ---- consulta ----------------------------------------------------------------------------

    @property
    def remaining_s(self) -> float:
        """Segundos até o lembrete (foco, parado ou não) ou até o fim do descanso; 0 nas demais."""
        if self.phase in (Phase.FOCUS, Phase.AWAY, Phase.ASKING_BACK, Phase.MEETING):
            return max(self._target - self._worked, 0.0)
        if self.phase is Phase.BREAK:
            return max(self._break_planned - self._break_elapsed, 0.0)
        return 0.0

    @property
    def excess_s(self) -> float:
        """Quanto já passou do descanso (só em `BREAK_OVER`)."""
        return self._excess

    @property
    def worked_s(self) -> float:
        """Segundos de foco acumulados neste foco."""
        return self._worked

    @property
    def planned_break_s(self) -> float:
        """Duração prevista do descanso atual (ou do próximo, se ainda não começou)."""
        minutes = self._cfg.long_break_min if self.long_break else self._cfg.break_min
        return minutes * 60

    @property
    def focus_number(self) -> int:
        """Qual foco do conjunto é este ("2 de 4"). O que já bateu a meta mantém o seu número."""
        number = self._cycles if self._focus_counted else self._cycles + 1
        return min(max(number, 1), self._cfg.cycles_before_long)

    @property
    def focus_total(self) -> int:
        return self._cfg.cycles_before_long

    @property
    def progress(self) -> float:
        """Quanto da fase já passou (0 a 1), para o anel da janela."""
        if self.phase in (Phase.FOCUS, Phase.AWAY, Phase.ASKING_BACK, Phase.MEETING):
            return min(self._worked / self._target, 1.0) if self._target else 0.0
        if self.phase is Phase.BREAK:
            return (
                min(self._break_elapsed / self._break_planned, 1.0) if self._break_planned else 0.0
            )
        if self.phase in (Phase.REMINDER, Phase.BREAK_OVER):
            return 1.0
        return 0.0

    def set_config(self, cfg: HabitConfig) -> None:
        """Novos tempos (Ajustes): valem a partir do próximo foco ou descanso."""
        self._cfg = cfg

    def set_mode(self, mode: Mode) -> None:
        """Troca de modo (a pílula da janela). Casual desliga o ciclo; profissional recomeça."""
        if mode is self.mode:
            return
        self.mode = mode
        self._reset_cycle()
        self.phase = Phase.OFF if mode is Mode.CASUAL else Phase.WAITING

    # ---- relógio -----------------------------------------------------------------------------

    def tick(self, idle_s: float | None, meeting: bool = False) -> list[CycleEvent]:
        """Anda o relógio um passo. `idle_s` = segundos sem teclado nem mouse (`None` = observação
        pausada). `meeting` = microfone em uso por outro programa."""
        now = self._clock.now()
        dt, self._last = now - self._last, now
        if self.phase is Phase.OFF or idle_s is None:
            return []
        idle = min(idle_s, now - self._ref)  # depois de uma reunião, a ociosidade dela não vale
        if self.phase is Phase.MEETING:
            if not meeting:
                self._ref = now  # reunião acabou: conta como presença e segue o foco
                self.phase = Phase.FOCUS
            return []
        if meeting and self.phase in (Phase.WAITING, Phase.FOCUS, Phase.AWAY):
            self.phase = Phase.MEETING
            return []
        handler = {
            Phase.WAITING: self._tick_waiting,
            Phase.FOCUS: self._tick_focus,
            Phase.AWAY: self._tick_away,
            Phase.ASKING_BACK: self._tick_asking_back,
            Phase.REMINDER: self._tick_reminder,
            Phase.BREAK: self._tick_break,
            Phase.BREAK_OVER: self._tick_break_over,
        }[self.phase]
        return handler(idle, dt, now)

    def _tick_waiting(self, idle: float, dt: float, now: float) -> list[CycleEvent]:
        if idle < ENTRY_S:
            self._begin_focus()
        return []

    def _tick_focus(self, idle: float, dt: float, now: float) -> list[CycleEvent]:
        if idle >= self._cfg.away_idle_s:
            # O foco para no último gesto: tira os minutos parados que já tinham sido contados.
            self._worked = max(self._worked - idle, 0.0)
            self._last_gesture = now - idle
            self.phase = Phase.AWAY
            return []
        self._worked += dt
        if self._worked < self._target:
            return []
        events = [] if self._focus_counted else [CycleEvent(kinds.FOCUS_DONE)]
        if not self._focus_counted:
            self._cycles += 1
            self._focus_counted = True
        self.long_break = self._cycles >= self._cfg.cycles_before_long
        self.phase = Phase.REMINDER
        self._unanswered_s = 0.0
        return [*events, CycleEvent(kinds.SHOW_BREAK)]

    def _tick_away(self, idle: float, dt: float, now: float) -> list[CycleEvent]:
        if idle >= ENTRY_S:
            return []
        self.last_absence_s = now - self._last_gesture
        self.phase = Phase.ASKING_BACK
        self._unanswered_s = 0.0
        return [CycleEvent(kinds.SHOW_ASK_BACK)]

    def _tick_asking_back(self, idle: float, dt: float, now: float) -> list[CycleEvent]:
        if idle < self._cfg.away_idle_s:  # só conta o tempo com você ali, vendo a pergunta
            self._unanswered_s += dt
        if self._unanswered_s >= ASK_TIMEOUT_S:
            return self.answer_back(AwayAnswer.PAUSE)  # sem resposta = pausa
        return []

    def _tick_reminder(self, idle: float, dt: float, now: float) -> list[CycleEvent]:
        if idle >= LEAVE_S:  # saiu da mesa: aceitou a pausa, contada do último gesto
            self._begin_break(elapsed=idle)
            return []
        self._unanswered_s += dt
        if self._unanswered_s >= self._cfg.ignore_after_min * 60:
            self._begin_focus()
            return [CycleEvent(kinds.BREAK_IGNORED)]
        return []

    def _tick_break(self, idle: float, dt: float, now: float) -> list[CycleEvent]:
        self._break_elapsed += dt
        if self._break_elapsed < self._break_planned:
            return []  # mexer no PC não encerra o descanso
        if idle < ENTRY_S:
            return self._finish_break(excess=0.0, back=True)
        self.phase = Phase.BREAK_OVER  # o tempo acabou e você ainda está longe
        self._excess = self._break_elapsed - self._break_planned
        return []

    def _tick_break_over(self, idle: float, dt: float, now: float) -> list[CycleEvent]:
        self._excess += dt
        if idle < ENTRY_S:
            return self._finish_break(excess=self._excess, back=True)
        return []

    # ---- respostas do dono -------------------------------------------------------------------

    def take_break(self) -> bool:
        """ "Pausar agora": começa o descanso (do lembrete, ou adiantando-o em pleno foco)."""
        if self.phase is Phase.REMINDER:
            self._begin_break(elapsed=0.0)
            return True
        if self.phase is Phase.FOCUS:
            self.long_break = self._cycles >= self._cfg.cycles_before_long
            self._begin_break(elapsed=0.0)
            return True
        return False

    def start_meal(self) -> bool:
        """ "Refeição" (botão ao lado do modo): começa já um descanso longo, sem cobrança."""
        if self.phase not in MEAL_FROM:
            return False
        self.long_break = True
        self._begin_break(elapsed=0.0)
        self.meal = True
        return True

    def postpone(self) -> list[CycleEvent]:
        """ "Prorrogar 5 min": volta ao foco por mais `break_snooze_min`, quantas vezes quiser."""
        if self.phase is not Phase.REMINDER:
            return []
        self.postponements += 1
        self._target = self._worked + self._cfg.break_snooze_min * 60
        self.phase = Phase.FOCUS
        return [CycleEvent(kinds.BREAK_SNOOZED, value=self.postponements)]

    def decline(self) -> list[CycleEvent]:
        """ "Hoje não": segue o trabalho sem descansar (um foco novo)."""
        if self.phase is not Phase.REMINDER:
            return []
        self._begin_focus()
        return [CycleEvent(kinds.BREAK_DECLINED)]

    def end_break_early(self) -> list[CycleEvent]:
        """ "Voltar ao foco antes": a pausa feita pela metade também conta como pausa."""
        if self.phase not in (Phase.BREAK, Phase.BREAK_OVER):
            return []
        return self._finish_break(excess=0.0, back=False)

    def skip(self) -> list[CycleEvent]:
        """Pula a fase: foco → lembrete; descanso → próximo foco; lembrete → hoje não."""
        if self.phase is Phase.FOCUS:
            self._worked = self._target
            self._focus_counted = True  # pular não conta como foco concluído
            self.long_break = self._cycles >= self._cfg.cycles_before_long
            self.phase = Phase.REMINDER
            self._unanswered_s = 0.0
            return [CycleEvent(kinds.SKIPPED), CycleEvent(kinds.SHOW_BREAK)]
        if self.phase in (Phase.BREAK, Phase.BREAK_OVER):
            self._begin_focus()
            return [CycleEvent(kinds.SKIPPED)]
        if self.phase is Phase.REMINDER:
            return self.decline()
        return []

    def answer_back(self, answer: AwayAnswer) -> list[CycleEvent]:
        """Responde "o que foi?". Cada categoria vale uma coisa (doc 06, etapa 7)."""
        if self.phase is not Phase.ASKING_BACK:
            return []
        absence = round(self.last_absence_s)
        category = answer.value
        if answer is AwayAnswer.PAUSE:
            planned = self._cfg.break_min * 60
            excess = max(absence - planned, 0)
            self._begin_focus()
            return [
                CycleEvent(
                    kinds.BREAK_DONE,
                    category,
                    planned_s=round(planned),
                    actual_s=absence,
                    excess_s=round(excess) if excess > EXCESS_GRACE_S else 0,
                )
            ]
        if answer is AwayAnswer.MEAL:  # descanso longo, sem excesso nem penalidade
            self._cycles = 0
            self._begin_focus()
            return [
                CycleEvent(
                    kinds.BREAK_DONE,
                    category,
                    planned_s=round(self._cfg.long_break_min * 60),
                    actual_s=absence,
                    excess_s=0,
                )
            ]
        if answer is AwayAnswer.NEED:  # não penaliza, não é pausa: o foco continua de onde estava
            self.phase = Phase.FOCUS
            return [CycleEvent(kinds.AWAY_NEED, category, actual_s=absence)]
        self._worked += self.last_absence_s  # foco sem mexer: o tempo fora vira foco
        self.phase = Phase.FOCUS
        return [CycleEvent(kinds.AWAY_FOCUS, category, actual_s=absence)]

    # ---- transições internas -----------------------------------------------------------------

    def _reset_cycle(self) -> None:
        self._cycles = 0
        self._begin_focus()

    def _begin_focus(self) -> None:
        self.phase = Phase.FOCUS
        self._worked = 0.0
        self._target = self._cfg.focus_min * 60
        self._focus_counted = False
        self.postponements = 0
        self.long_break = False
        self.meal = False
        self._unanswered_s = 0.0

    def _begin_break(self, elapsed: float) -> None:
        self.phase = Phase.BREAK
        minutes = self._cfg.long_break_min if self.long_break else self._cfg.break_min
        self._break_planned = minutes * 60
        self._break_elapsed = elapsed
        self._excess = 0.0

    def _finish_break(self, excess: float, back: bool) -> list[CycleEvent]:
        actual = round(self._break_planned + excess if excess else self._break_elapsed)
        if self.meal:  # refeição não tem excesso: o tempo a mais é só contado em `actual_s`
            excess = 0.0
        event = CycleEvent(
            kinds.BREAK_DONE,
            kinds.CAT_MEAL if self.meal else kinds.CAT_PAUSE,
            value=self.postponements,
            planned_s=round(self._break_planned),
            # com excesso, o tempo parou de correr no fim do descanso: feito = planejado + excesso
            actual_s=actual,
            excess_s=round(excess) if excess > EXCESS_GRACE_S else 0,
        )
        if self.long_break:
            self._cycles = 0
        self._begin_focus()
        return [event, CycleEvent(kinds.SHOW_BACK)] if back else [event]
