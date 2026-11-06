"""As falas do pet: primeira pessoa, curtas e carinhosas, sem culpa nem bronca (Design Brief §8)."""

import random

SLEEPING = "dormindo"  # estado de pausa; não é um humor da rede

WELCOME = (
    "Oi, eu sou o Pulso! Use 💚 e 💢 para me ensinar o que você gosta. "
    "Com o botão de pausa eu fecho os olhos e paro de observar."
)
GREETING = "Oi de novo! Já tava com saudade."
PAUSED = "Tô de olhos fechados. Me acorda quando quiser."
RESUMED = "Voltei! Que bom te ver."
PETTED = "Hmm, que bom! Vou lembrar disso."
SCOLDED = "Entendi. Vou tentar fazer diferente."

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
