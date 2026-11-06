"""Pomodoro (F07): ciclos de foco e descanso, como máquina de estados pura.

    PARADO ──iniciar──▶ FOCO ──acabou──▶ PEDINDO_DESCANSO ──fiz──▶ DESCANSO ──acabou──▶ FOCO ...
                                              │  ▲ depois (adia 5 min)
                                              └──┴─ recusei / ignorei ──▶ FOCO (sem descansar)

- O foco e o descanso são contagens regressivas de relógio de parede: **não** dependem de o dono
  estar presente nem da pausa de privacidade (descansar não desliga a observação).
- Quando o foco acaba, quem pergunta "vamos descansar?" é um `Reminder`: ele espera o dono voltar
  se ele estiver longe e vira "ignorei" se ele não responder (só contando o tempo com ele presente).
- A cada `cycles_before_long` focos concluídos, o descanso é o longo.
- O descanso termina sozinho, avisa "hora de voltar" e já começa o próximo foco.
"""

from enum import Enum

from pulso.clock import Clock
from pulso.habits import kinds
from pulso.habits.kinds import HabitConfig, Presence
from pulso.habits.reminder import Reminder


class Phase(Enum):
    STOPPED = "parado"
    FOCUS = "foco"
    ASKING = "pedindo descanso"
    BREAK = "descanso"


class Pomodoro:
    def __init__(self, clock: Clock, cfg: HabitConfig | None = None) -> None:
        self._clock = clock
        self._cfg = cfg or HabitConfig()
        self._reminder = Reminder(clock, self._cfg.ignore_after_min * 60)
        self.phase = Phase.STOPPED
        self.paused = False  # contagem congelada pelo painel (nada a ver com a privacidade)
        self.long_break = False  # o descanso atual (ou o que vem) é o longo?
        self._remaining = 0.0
        self._last = clock.now()
        self._cycles = 0  # focos concluídos desde o último descanso longo

    # ---- consulta ----------------------------------------------------------------------------

    @property
    def remaining_s(self) -> float:
        """Segundos que faltam na fase atual (0 se parado ou pedindo descanso)."""
        return max(self._remaining, 0.0)

    @property
    def asking(self) -> bool:
        """O pet está perguntando se o dono quer descansar?"""
        return self.phase is Phase.ASKING

    def set_config(self, cfg: HabitConfig) -> None:
        """Novos tempos (Ajustes): valem a partir da próxima fase (a que está rodando termina)."""
        self._cfg = cfg

    @property
    def running(self) -> bool:
        return self.phase is not Phase.STOPPED

    # ---- comandos do dono --------------------------------------------------------------------

    def start(self) -> None:
        """Começa um foco novo (de parado, ou do zero se já estava rodando)."""
        self._begin_focus()

    def stop(self) -> None:
        self.phase = Phase.STOPPED
        self.paused = False
        self._reminder.disarm()
        self._remaining = 0.0

    def pause(self) -> None:
        if self.phase in (Phase.FOCUS, Phase.BREAK):
            self._advance_clock()  # fecha o tempo corrido até agora antes de congelar
            self.paused = True

    def resume(self) -> None:
        if self.paused:
            self._last = self._clock.now()  # o tempo parado não conta
            self.paused = False

    def skip(self) -> str | None:
        """Pula a fase: foco → pergunta do descanso; descanso → próximo foco; na pergunta, é
        o mesmo que recusar. Devolve o que deve ser gravado."""
        if self.phase is Phase.FOCUS:
            self._ask()
            return kinds.SKIPPED
        if self.phase is Phase.BREAK:
            self._begin_focus()
            return kinds.SKIPPED
        if self.phase is Phase.ASKING:
            return self.decline()
        return None

    def rest(self) -> str | None:
        """ "Fiz a pausa" (vale a qualquer hora, também sem pergunta na tela).

        Na pergunta, começa o descanso. Em pleno foco, o dono avisa que já descansou: o foco
        recomeça. Já descansando, não há o que registrar.
        """
        if self.phase is Phase.BREAK:
            return None
        if self.phase is Phase.ASKING:
            self._begin_break()
        elif self.phase is Phase.FOCUS:
            self._begin_focus()
        return kinds.BREAK_DONE

    def later(self) -> str | None:
        """Depois: adia a pergunta (só com a pergunta na tela)."""
        if not self.asking:
            return None
        self._reminder.arm(self._cfg.break_snooze_min * 60)
        return kinds.BREAK_SNOOZED

    def decline(self) -> str | None:
        """Hoje não: segue trabalhando sem descansar (só com a pergunta na tela)."""
        if not self.asking:
            return None
        self._begin_focus()
        return kinds.BREAK_DECLINED

    # ---- relógio -----------------------------------------------------------------------------

    def tick(self, presence: Presence) -> list[str]:
        """Anda o relógio. Devolve acontecimentos: gravar (`FOCUS_DONE`, `BREAK_IGNORED`) e/ou
        avisar a interface (`SHOW_BREAK`, `SHOW_BACK`)."""
        events: list[str] = []
        self._advance_clock()
        if self.phase is Phase.FOCUS and not self.paused and self._remaining <= 0:
            events.append(kinds.FOCUS_DONE)
            self._cycles += 1
            self._ask()
        elif self.phase is Phase.BREAK and not self.paused and self._remaining <= 0:
            self._begin_focus()
            events.append(kinds.SHOW_BACK)
        if self.phase is Phase.ASKING:
            outcome = self._reminder.tick(presence)
            if outcome == "shown":
                events.append(kinds.SHOW_BREAK)
            elif outcome == "ignored":
                self._begin_focus()
                events.append(kinds.BREAK_IGNORED)
        return events

    # ---- transições internas -----------------------------------------------------------------

    def _advance_clock(self) -> None:
        now = self._clock.now()
        if self.phase in (Phase.FOCUS, Phase.BREAK) and not self.paused:
            self._remaining -= now - self._last
        self._last = now

    def _begin_focus(self) -> None:
        self.phase = Phase.FOCUS
        self.paused = False
        self._remaining = self._cfg.focus_min * 60
        self._reminder.disarm()
        self._last = self._clock.now()

    def _ask(self) -> None:
        self.phase = Phase.ASKING
        self._remaining = 0.0
        self.long_break = self._cycles >= self._cfg.cycles_before_long
        self._reminder.arm(0)

    def _begin_break(self) -> None:
        self.phase = Phase.BREAK
        self.paused = False
        minutes = self._cfg.long_break_min if self.long_break else self._cfg.break_min
        if self.long_break:
            self._cycles = 0
        self._remaining = minutes * 60
        self._reminder.disarm()
        self._last = self._clock.now()
