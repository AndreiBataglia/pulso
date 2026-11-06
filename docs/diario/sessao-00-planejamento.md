# Sessão 00 — Planejamento (2026-11-05)

> Registro da conversa que deu origem ao projeto. Leia isto ao retomar, junto com `docs/README.md`.

## Origem
- A ideia veio do reel de Reagan sobre o **DeskBuddy** (Acervo do hub_service, 2026-11-04): um companheiro de
  desktop em Python com SNN (neurônios LIF, STDP) e "dopamina artificial".
- O repositório original nunca foi liberado. O dono não precisa dele: quer **aprender construindo** um
  projeto semelhante.
- Projeto **independente** do hub_service.

## Decisões do dono (na ordem em que foram tomadas)
1. **Foco:** companheiro que observa o PC com SNN, e não um Tamagotchi clássico.
2. **Interface:** janela de painel, com gráficos dos neurônios.
3. **Observação nível B:** metadados (CPU, RAM, hora, ociosidade), a categoria do programa e as trocas de
   programa por minuto. Sem texto, sem tela, sem teclas.
4. **Pausa de privacidade manual:** o dono decide e aperta. Não há detecção automática.
5. **SNN:** numpy desde já, com o motor trocável por uma interface comum (`Engine`).
6. **Escala:** precisa ser orçada. Faixa planejada de 100 a 500 neurônios; o MVP usa ~200.
7. **Recompensa:** as duas fontes juntas (carinho e bronca do dono, mais regras automáticas).
8. **Saúde:** a "sugestão de descanso" vira um pomodoro, e entra um lembrete de água. A pausa de privacidade
   continua separada.
9. **GitHub:** repositório público, licença MIT. O dono instala o `gh` e o Claude cria o repositório. Cada
   etapa tem documentação bem descrita e push, sempre com autorização.
10. **Nome:** o dono quer um nome próprio para o pet. O provisório é **"Pulso"** (falta confirmar).

## Correções feitas na revisão (registradas para não repetir)
- **Dois relógios:** os sensores leem a cada 1 s, e cada leitura simula 100 ms de rede, com passo de 1 ms. A
  frase anterior, "10 a 50 passos por segundo", estava errada.
- **Motor trocável:** a interface vale para motores que aprendem **online** (numpy, Brian2). O snnTorch e o
  Norse treinam **offline** por gradiente e precisam de um modo de treino separado (F15).
- A categoria da janela vem do **nome do processo**. O título nunca é lido.
- O atalho de pausa usa `RegisterHotKey`, que não é *hook* de teclado.

## Pendências (perguntas para o dono)
- Confirmar o nome "Pulso".
- Formato do pet (sugestão: uma "bolinha" com olhos).
- Retomar a observação sozinho após N minutos: deve existir, desligado por padrão, ou nunca?
- Pomodoro manual ou automático no primeiro uso do dia (sugestão: manual).

## Próximo passo
1. Dono: renomear a pasta para `projeto_tamagotchi`, rodar `winget install GitHub.cli` e depois
   `gh auth login`.
2. Abrir uma conversa nova na pasta e pedir a **etapa 0** do `docs/06-implementation-plan.md`.

## Onde mais está registrado
- Segundo cérebro do hub_service, espaço **Geral**, tema "Projetos futuros do usuário": 5 notas
  "DeskBuddy…" e "Projeto Tamagotchi…". Para achar:
  `python -m services.segundo_cerebro.registrar_nota --buscar "tamagotchi"` (dentro do hub_service).
