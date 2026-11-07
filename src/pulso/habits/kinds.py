"""Os tipos de acontecimento de hábito (os mesmos valores do `CHECK` de `habit_event.kind`) e a
presença do dono, que decide quando um lembrete pode aparecer ou valer como "ignorei"."""

from dataclasses import dataclass
from enum import Enum

WATER_DRUNK = "water_drunk"  # fiz: bebi
WATER_SNOOZED = "water_snoozed"  # depois
WATER_DECLINED = "water_declined"  # recusei
WATER_IGNORED = "water_ignored"  # ignorei (sem resposta)
FOCUS_DONE = "pomodoro_focus_done"  # um ciclo de foco terminou
BREAK_DONE = "pomodoro_break_done"  # fiz: descansei
BREAK_SNOOZED = "break_snoozed"
BREAK_DECLINED = "break_declined"
BREAK_IGNORED = "break_ignored"
SKIPPED = "pomodoro_skipped"  # o dono pulou a fase pelo painel (não é recusa)
STREAK_END = "break_streak_end"  # (etapa 7) minutos seguidos de trabalho antes da pausa
# Respostas a "o que foi?" (etapa 7). Pausa e refeição são gravadas como BREAK_DONE com a categoria.
AWAY_NEED = "away_need"  # necessidade (banheiro, rápida): não penaliza nem vale como pausa
AWAY_FOCUS = "away_focus"  # foco sem mexer (leitura, vídeo): o tempo fora vira foco

# Categorias da volta (coluna `category` de `habit_event`).
CAT_PAUSE, CAT_MEAL, CAT_NEED, CAT_FOCUS = "pause", "meal", "need", "focus"
CATEGORIES = (CAT_PAUSE, CAT_MEAL, CAT_NEED, CAT_FOCUS)

# Os tipos que entraram na migração v3 do banco (o `CHECK` da v1 não os conhecia).
V3_KINDS = (AWAY_NEED, AWAY_FOCUS)

ALL_KINDS = (
    WATER_DRUNK, WATER_SNOOZED, WATER_DECLINED, WATER_IGNORED,
    FOCUS_DONE, BREAK_DONE, BREAK_SNOOZED, BREAK_DECLINED, BREAK_IGNORED,
    SKIPPED, STREAK_END,
    *V3_KINDS,
)  # fmt: skip

# Sinais que só avisam a interface (não são gravados): um lembrete acabou de aparecer.
SHOW_WATER = "water_due"
SHOW_BREAK = "break_due"
SHOW_BACK = "back_to_work"  # o descanso acabou: hora de voltar
SHOW_ASK_BACK = "ask_back"  # voltou de uma ausência: perguntar "o que foi?"


class Presence(Enum):
    """O que se sabe do dono neste segundo."""

    PRESENT = "present"  # usando o PC
    AWAY = "away"  # ocioso há tempo: o lembrete espera a volta
    UNKNOWN = "unknown"  # observação pausada ou leitura falhou: não dá para julgar


@dataclass(frozen=True)
class HabitConfig:
    """Tempos e pontos de pendência (padrões do doc 05 §5; a etapa 7 lê isto do `config.toml`)."""

    focus_min: float = 50.0
    break_min: float = 10.0
    long_break_min: float = 20.0
    cycles_before_long: int = 4
    break_snooze_min: float = 5.0
    water_interval_min: float = 60.0
    water_snooze_min: float = 10.0
    water_ml: int = 250  # quanto cada "Bebi" soma (o copo ou a garrafa do dono)
    ignore_after_min: float = 5.0
    away_idle_s: float = 300.0  # ocioso há tanto tempo = "longe do PC"
    refuse_points: int = 2
    ignore_points: int = 1
    nervous_at: int = 3
