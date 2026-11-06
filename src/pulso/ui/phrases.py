"""As falas do pet: primeira pessoa, curtas e carinhosas, sem culpa nem bronca (Design Brief §8)."""

import random

SLEEPING = "dormindo"  # estado de pausa; não é um humor da rede

WELCOME = (
    "Oi, eu sou o Pulso! Use 💚 para me dar carinho quando eu acertar. "
    "Com o botão de pausa eu fecho os olhos e paro de observar."
)
GREETING = "Oi de novo! Já tava com saudade."
PAUSED = "Tô de olhos fechados. Me acorda quando quiser."
RESUMED = "Voltei! Que bom te ver."
PETTED = "Hmm, que bom! Vou lembrar disso."

# O que cada rosto quer dizer, para o dono nunca ter que adivinhar (aparece sob o rosto).
MOOD_MEANINGS = {
    "animado": "Animado: estou com energia, parece um bom momento.",
    "contente": "Contente: está tudo tranquilo, gostei do seu ritmo.",
    "entediado": "Entediado: está quieto por aqui, sem novidade.",
    "sonolento": "Sonolento: o computador está parado, me deu sono.",
    "preocupado": "Preocupado: acho que você precisa de uma pausa.",
}
MEANING_NEW = "Acordando: ainda estou te conhecendo."
MEANING_SLEEPING = "Dormindo: a observação está pausada, não estou lendo nada."
MEANING_HINT = "O humor vem da rede de pulsos, que aprende com os seus carinhos e broncas."

MOOD_PHRASES: dict[str, tuple[str, ...]] = {
    "animado": ("Bora! Tô cheio de energia!", "Que dia bom pra fazer coisas!"),
    "contente": ("Tô bem, e você?", "Tudo tranquilo por aqui."),
    "entediado": ("Hmm... tá quietinho por aqui.", "Será que acontece algo logo?"),
    "sonolento": ("Que soninho...", "Ai, ai... bocejando aqui."),
    "preocupado": ("Faz tempo que você não descansa, né?", "Um alongadinho ia bem..."),
}


# Hábitos (F07/F08): tom de quem cuida, sem culpa nem bronca (Design Brief §8).
ASK_WATER = "Psiu! Um gole d'água? 💧"
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


def nervous_meaning(reason: str | None) -> str:
    """O que o rosto nervoso quer dizer, dizendo o motivo (aparece sob o rosto)."""
    what = reason or "hábito"
    return f"Nervoso: ficaram lembretes de {what} sem resposta. Me conta quando fizer."


def nervous_phrase(reason: str | None) -> str:
    return f"Tô inquieto... ficou {reason or 'um cuidado'} pendente. Quando fizer, me avisa?"


def mood_phrase(mood: str, rng: random.Random | None = None) -> str:
    """Uma frase do humor (sorteada, para o pet não repetir sempre a mesma)."""
    options = MOOD_PHRASES[mood]
    return (rng or random).choice(options)


# ---- jogos ----------------------------------------------------------------------------------
GAME_WON = "Ganhei! 😎 Quer a revanche?"
GAME_LOST = "Argh, você ganhou... 😤 Mais uma, agora vai!"
GAME_DRAW = "Empatou! 🤝 Joga de novo?"
GAME_INTRO = "Escolha um jogo e jogue! Eu jogo limpo."
