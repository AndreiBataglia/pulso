"""As falas do Pulso: primeira pessoa, curtas e carinhosas, sem culpa (Design Brief §8)."""

from pulso.habits import mood_rules
from pulso.habits.mood_rules import MoodVerdict

SLEEPING = "dormindo"  # estado de pausa; não é um humor da rede

WELCOME = (
    "Oi, eu sou o Pulso! Use 💚 para me dar carinho quando eu acertar. "
    "Com o botão de pausa eu fecho os olhos e paro de observar."
)
GREETING = "Oi de novo! Já tava com saudade."
PAUSED = "Tô de olhos fechados. Me acorda quando quiser."
RESUMED = "Voltei! Que bom te ver."
PETTED = "Hmm, que bom! Vou lembrar disso."

MEANING_SLEEPING = "Dormindo: a observação está pausada, não estou lendo nada."
MEANING_HINT = "O humor segue regras claras: o que você fez, ou deixou de fazer, nos seus cuidados."


# Hábitos (F07/F08): tom de quem cuida, sem culpa nem bronca (Design Brief §8).
ASK_WATER = "Psiu! Um gole d'água? 💧"
WATER_IGNORED = "Sem resposta... deixei a água como pendente e lembro de novo daqui a pouco."
ASK_BREAK = "Já faz um bom tempo de foco. Que tal descansar um pouquinho? ☕"
BACK_TO_WORK = "O descanso acabou! Vamos voltar com calma?"
DRANK = "Que bom! Obrigado por se cuidar. 💧"
RESTED = "Descansar faz bem. Aproveita!"
LATER_AGAIN = "Tudo bem, eu lembro de novo daqui a pouco."
NO_PROBLEM = "Tá bem. É só porque eu gosto de você."
IN_TRAY = "Continuo aqui na bandeja. Clique no meu ícone para me abrir; para sair de vez, use Sair."
RELAXED = "Ufa, agora estou mais tranquilo. Obrigado!"


# Ciclo do foco por presença (etapa 7): o Pulso narra o que percebeu, sem cobrar.
MEETING_ON = "Microfone em uso: pausei o foco. Quando a reunião acabar, eu continuo de onde parou."
MEETING_OFF = "A reunião acabou. Voltei a contar o foco."
BREAK_STARTED = "Levanta, estica, olha longe. Se passar do tempo, eu te conto quanto."
MEAL_STARTED = "Bom apetite! É descanso longo, sem cobrança. Eu espero você voltar."
LONG_BREAK_STARTED = "Descanso longo! Vale água, alongar e sair um pouco da frente da tela."
AWAY_NOTICED = "Você ficou parado. Parei de contar o foco no seu último gesto."
CASUAL_ON = "Modo casual: não conto foco nem te chamo para pausa. Só lembro da água."
PROFESSIONAL_ON = "Modo profissional: conto o seu foco e te chamo para a pausa."
AWAY_REPLIES = {
    "pause": RESTED,
    "meal": "Bom apetite! Conto como descanso longo, sem cobrança.",
    "need": "Tudo bem. O foco continua de onde estava.",
    "focus": "Entendi: esse tempo conta como foco.",
}


def break_summary(planned_s: int | None, excess_s: int | None) -> str:
    """O resumo da pausa que acabou (o excesso só é contado, nunca cobrado)."""
    if not excess_s:
        return RESTED
    planned = round((planned_s or 0) / 60)
    return f"Descansou {planned} min + {max(round(excess_s / 60), 1)} além. Tudo certo!"


def away_question(minutes: int) -> str:
    return f"Você ficou {max(minutes, 1)} min fora. O que foi?"


def remind_break(focus_min: int, break_min: int) -> str:
    return f"{focus_min} min de foco. Bora pausar {break_min}?"


def _times(n: int) -> str:
    return "1 vez" if n == 1 else f"{n} vezes"


def mood_meaning(v: MoodVerdict) -> str:
    """O que o rosto quer dizer, sempre com o motivo (aparece sob o rosto)."""
    if v.cause == mood_rules.PENDING:
        return f"Nervoso: ficaram lembretes de {v.detail} sem resposta. Me conta quando fizer."
    if v.cause == mood_rules.POSTPONED:
        return f"Preocupado: você prorrogou a pausa {_times(int(v.detail))} seguidas."
    if v.cause == mood_rules.SLEEPY:
        return f"Sonolento: faz {max(int(v.detail), 1)} min sem mexer no computador."
    if v.cause == mood_rules.ON_TIME_BREAK:
        return f"Contente: você descansou no horário hoje ({v.detail})."
    if v.cause == mood_rules.WATER_DONE:
        return f"Contente: você já bebeu água hoje ({v.detail})."
    return "Tranquilo: nada pendente por aqui."


def mood_say(v: MoodVerdict, previous: MoodVerdict | None = None) -> str | None:
    """A fala do balão quando o humor vira (`None` = não precisa falar: a legenda já explica)."""
    if v.cause == mood_rules.PENDING:
        return f"Tô inquieto... ficou {v.detail} pendente. Quando fizer, me avisa?"
    if v.cause == mood_rules.POSTPONED and int(v.detail) >= 2:  # a 1ª prorrogação é normal
        return f"Você adiou a pausa {_times(int(v.detail))}... estou preocupado com você."
    if v.cause == mood_rules.SLEEPY:
        return "Que soninho... você está quietinho há um tempo."
    if previous is not None and previous.cause == mood_rules.PENDING:
        return RELAXED
    return None


# ---- jogos ----------------------------------------------------------------------------------
GAME_WON = "Ganhei! 😎 Quer a revanche?"
GAME_LOST = "Argh, você ganhou... 😤 Mais uma, agora vai!"
GAME_DRAW = "Empatou! 🤝 Joga de novo?"
GAME_INTRO = "Escolha um jogo e jogue! Eu jogo limpo."
