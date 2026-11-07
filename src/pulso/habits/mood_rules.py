"""Humor por regras claras: o rosto sempre tem um motivo que dá para dizer em palavras.

A rede decide **quando** lembrar (fatia 5); o **humor do rosto** vem destas regras, explicáveis e
sem acaso. Cada regra devolve o humor e a **causa**, que a janela escreve sob o rosto e no balão.

Da mais forte para a mais fraca (a primeira que vale ganha):

1. **Pendência** de água/pausa → nervoso (some só quando o dono diz que fez).
2. **Lembrete prorrogado** → preocupado (o rosto pesa mais a cada prorrogação).
3. **Muito tempo sem interação** → sonolento.
4. **Cumpriu** (pausa no horário, sem prorrogar, ou copo d'água hoje) → contente.
5. Nada disso → neutro ("tranquilo").

Função pura: recebe números e devolve um veredito. Não lê sensor, banco nem relógio.
"""

from dataclasses import dataclass

# As causas (o texto de cada uma mora em `ui/phrases.py`).
PENDING = "pending"
POSTPONED = "postponed"
SLEEPY = "sleepy"
ON_TIME_BREAK = "on_time_break"
WATER_DONE = "water_done"
CALM = "calm"


@dataclass(frozen=True)
class MoodInputs:
    """O que as regras precisam saber, já resumido (nenhum sinal de sensor)."""

    nervous_reason: str | None  # "água", "pausa", "água e pausa" ou None
    postponements: int  # prorrogações do lembrete de pausa atual
    idle_s: float | None  # segundos sem teclado nem mouse (None = observação pausada)
    sleepy_after_s: float  # a partir de quanto tempo parado o Pulso fica sonolento
    on_time_breaks: int  # pausas feitas hoje sem prorrogar
    cups: int  # copos de água hoje


@dataclass(frozen=True)
class MoodVerdict:
    mood: str
    cause: str
    detail: str | int | None = None  # nervous_reason, nº de prorrogações, minutos parado, contagem

    @property
    def key(self) -> tuple[str, str, str | int | None]:
        """Identifica a virada, sem o detalhe que muda a cada minuto. Cada prorrogação é uma
        virada nova (o rosto fica mais preocupado), então o número entra na chave."""
        return (self.mood, self.cause, self.detail if self.cause == POSTPONED else None)


def decide(inp: MoodInputs) -> MoodVerdict:
    """O humor que vale agora e por quê."""
    if inp.nervous_reason:
        return MoodVerdict("nervoso", PENDING, inp.nervous_reason)
    if inp.postponements > 0:
        return MoodVerdict("preocupado", POSTPONED, inp.postponements)
    if inp.idle_s is not None and inp.idle_s >= inp.sleepy_after_s:
        return MoodVerdict("sonolento", SLEEPY, int(inp.idle_s // 60))
    if inp.on_time_breaks > 0:
        return MoodVerdict("contente", ON_TIME_BREAK, inp.on_time_breaks)
    if inp.cups > 0:
        return MoodVerdict("contente", WATER_DONE, inp.cups)
    return MoodVerdict("neutro", CALM)
