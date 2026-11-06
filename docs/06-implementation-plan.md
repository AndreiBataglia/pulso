# Plano de Implementação — Pulso

> A sequência exata de construção, passo a passo. Cada etapa deixa o app **funcionando**
> (mesmo que incompleto) e pode ser testada antes de seguir para a próxima.
> Última revisão: 2026-11-06

## Como usar este plano
- Siga as etapas em ordem; as dependências estão indicadas.
- Ao concluir uma tarefa, marque `[x]` com a data da prova; não apague.
- Se a ordem precisar mudar, registre o motivo no histórico.
- **Ritual de cada etapa:**
  1. Abrir a branch `etapa-NN-<nome>`.
  2. Escrever os testes e depois o código.
  3. Fazer um teste real (rodar, conferir os arquivos gravados, apagar o lixo do teste).
  4. Escrever o diário `docs/diario/etapa-NN.md`: o que foi feito, **conceitos aprendidos**, como testar, o que
     ficou para depois.
  5. Atualizar o `CHANGELOG.md` e as marcas deste plano.
  6. Commits lógicos, push, PR com CI verde, *merge* e tag `v0.NN.0`, **cada passo só com autorização do
     dono**.
  7. Perguntar "posso continuar?".
- **Uma conversa nova por etapa:** o estado fica nestes docs e no diário, não no chat.

## Etapa 0 — Fundação e GitHub (F11)
**Objetivo:** repositório público vazio mas "profissional", com CI verde.
- [x] (2026-11-05) Dono: renomear a pasta para `projeto_tamagotchi`, instalar o GitHub CLI (`winget install GitHub.cli`) e
      rodar `gh auth login`.
- [x] (2026-11-05) `git init`, com `main` como branch padrão.
- [x] (2026-11-05) `pyproject.toml` (dependências, extra `dev` com pytest e ruff, comando `pulso`), layout `src/pulso/`,
      `.gitignore`, `LICENSE` (MIT, com o nome do dono) e `CHANGELOG.md`.
- [x] (2026-11-05) `README.md` inicial: resumo em inglês, explicação em português, aviso de privacidade, status "em
      construção" e link para os docs.
- [x] (2026-11-05) `src/pulso/__main__.py` que imprime a versão, e um teste trivial.
- [x] (2026-11-05) `.github/workflows/ci.yml`: ruff e pytest no `windows-latest` (Python 3.12 e 3.13).
- [x] (2026-11-05) `gh repo create pulso --public`, primeiro push e selo do CI no README (CI verde no PR #1).
- [x] (2026-11-05) Diário `etapa-00.md`: o que é venv, pyproject, CI, *Conventional Commits* e o fluxo branch → PR → tag.
- **Pronto quando:** `pulso --version` funciona localmente e o CI está verde no GitHub.

## Etapa 1 — Sensores e pausa de privacidade (F01, F02)
**Objetivo:** ver no terminal o que o Pulso "sente", e provar que a pausa desliga tudo.
**Depende de:** Etapa 0
- [x] (2026-11-06) `clock.py` (relógio real e falso).
- [x] (2026-11-06) `sensors/base.py` (`SensorFrame`, protocolo `Sensor`), `categories.py` (tabela embutida mais a extra) e
      `fake.py` (roteiro).
- [x] (2026-11-06) `sensors/windows.py`: CPU/RAM (psutil), PID em primeiro plano (`GetForegroundWindow` +
      `GetWindowThreadProcessId`), nome do processo, ociosidade (`GetLastInputInfo`) e trocas por minuto.
- [x] (2026-11-06) `loop.py` mínimo, com `pause()`/`resume()` que **param de chamar** o sensor.
- [x] (2026-11-06) Testes:
  - categorias, incluindo o desconhecido;
  - na pausa, o sensor falso recebe zero chamadas;
  - teste de grep que garante que `GetWindowText` não aparece em `src/`;
  - erro no sensor vira leitura "desconhecida".
- [x] (2026-11-06) `pulso --print-sensors`: imprime uma linha por segundo (só para desenvolvimento, sem gravar nada).
- [x] (2026-11-06) Diário: como o Windows informa a janela ativa e a ociosidade, e por que o título não é lido.
- **Arquivos:** `src/pulso/clock.py`, `src/pulso/sensors/*`, `src/pulso/loop.py`, `tests/sensors/*`
- **Pronto quando:** os critérios de F01 e F02 (exceto botão e atalho, que dependem da interface) passam, e o
  teste real mostra a categoria certa ao alternar entre VS Code e o navegador.

## Etapa 2 — O neurônio e a rede (F03)
**Objetivo:** a rede pulsa e escolhe um humor, ainda sem aprender.
**Depende de:** Etapa 1
- [x] (2026-11-06) Um neurônio LIF isolado, com teste: corrente constante → frequência dentro da faixa teórica.
- [x] (2026-11-06) `brain/engine.py` (contrato) e `tests/brain/test_engine_contract.py`.
- [x] (2026-11-06) `numpy_engine.py`: entrada de Poisson, oculta excitatória e inibitória, saída com inibição lateral,
      semente fixa.
- [x] (2026-11-06) `encoding.py` (`SensorFrame` → taxas) e `decoding.py` (contagem → humor, com histerese).
- [x] (2026-11-06) Medir o custo de um segundo real (100 passos) e registrar no diário. Se passar de 20 ms, rever o
      tamanho ou usar uma thread (TRD §5.1).
- [x] (2026-11-06) `pulso --print-brain`: humor a cada 10 s, com sensores reais ou falsos.
- [x] (2026-11-06) Diário: equação do LIF com gráfico, codificação por taxa, inibição lateral e "por que 200 neurônios
      bastam".
- **Pronto quando:** o contrato passa, o custo medido fica no orçamento e o humor muda quando o roteiro do
  sensor falso muda.

## Etapa 3 — Aprender: STDP, dopamina e memória (F04)
**Objetivo:** o pet aprende e lembra o que aprendeu.
**Depende de:** Etapa 2
- [x] (2026-11-06) STDP com rastros pré e pós. Teste: pré antes de pós fortalece; pós antes de pré enfraquece
      (no sinal da elegibilidade, que é onde o STDP escreve).
- [x] (2026-11-06) Rastro de elegibilidade e R-STDP. Testes:
  - sem dopamina, o peso não muda;
  - com dopamina positiva, as sinapses elegíveis sobem.
- [x] (2026-11-06) `rewards.py`: regras automáticas (ócio longo → sonolento +, volta → animado +, mais de 90 min sem pausa →
      preocupado +), recompensa do dono, pesos configuráveis e filtro de cliques repetidos.
- [x] (2026-11-06) `storage/paths.py` e `brain_store.py`: `.npz` com versão, gravação atômica, salvamento a cada 5 min,
      ao pausar e ao sair.
- [x] (2026-11-06) Teste de aprendizado: num cenário roteirizado, depois de N recompensas o humor recompensado
      vence em ≥ 80% das decisões (N = 360; 100% nas sementes 1, 2 e 4; a 3 não aprende, ver diário).
- [x] (2026-11-06) Teste: salvar → carregar → mesmos pesos; versão desconhecida → recusa com aviso.
- [x] (2026-11-06) Diário: STDP, o problema da recompensa atrasada, elegibilidade, os **dois relógios** (TRD §5.1) e a
      dopamina como erro de previsão.
- **Pronto quando:** os critérios de F04 passam e o teste de aprendizado está verde em 3 sementes diferentes.
  Os botões Carinho/Bronca e a chamada do `AutoSaver` no laço dependem da interface: etapa 4.

## Etapa 4 — O pet aparece (F05, botões de F02 e F04)
**Objetivo:** primeira versão "de verdade", usável no dia a dia.
**Depende de:** Etapa 3
- [x] (2026-11-06) `app.py`, `main_window.py` com abas (por enquanto só "Pet") e o laço no `QTimer` de 1 s.
- [x] (2026-11-06) `pet_widget.py`: 5 humores mais "dormindo", com transições e a cor por humor (Design Brief §3).
- [x] (2026-11-06) Botões Carinho, Bronca e Pausar/Retomar (só ícone, ao lado dos outros); selo só quando pausado.
- [x] (2026-11-06) Primeiro uso: fala de boas-vindas (J01).
- [x] (2026-11-06) Teste de interface (`offscreen`): o clique em Carinho chama `reward(+1)`; Pausar troca o selo e para o
      sensor.
- [x] (2026-11-06) Teste real e medição de CPU e RAM (meta do PRD §4). Feito em 27 min de uso real, e o dono
      considerou suficiente: CPU ~0%, RAM 152→155 MB.
- [x] (2026-11-06) Diário: Qt (sinais e *slots*, `QTimer`), desenho com QPainter e uma captura para o README.
- **Pronto quando:** os critérios de F05 passam, a J01 e a J02 (pelo botão) funcionam e o consumo está dentro da
  meta.

## Etapa 5 — Ver o cérebro (F06)
**Objetivo:** a aba Cérebro mostra a rede ao vivo.
**Depende de:** Etapa 4
- [x] (2026-11-06) `snapshot()` no motor (pulsos recentes, V de 3 neurônios, dopamina, pesos).
- [x] (2026-11-06) `brain_tab.py`: raster, potenciais, dopamina com marcas de fonte, barras por humor, mapa de pesos e
      rodapé com o custo da rede (por volta de 1 s, não por passo de 1 ms: é o que o orçamento do TRD mede).
- [x] (2026-11-06) Dicas ❓ em cada gráfico; congelar e continuar.
- [x] (2026-11-06) Não redesenhar com a aba oculta ou a janela minimizada (medido: 3,2 ms por volta com a janela escondida, igual ao pet;
      12,8 ms com o Cérebro visível).
- [x] (2026-11-06) Diário: como ler um raster e o que observar quando a rede aprende.
- **Pronto quando:** os critérios de F06 passam e a J03 é visível nos gráficos.

## Etapa 6 — Hábitos: pomodoro e água (F07, F08)
**Objetivo:** o Pulso cuida do dono.
**Depende de:** Etapa 4 (a 5 não é necessária)
- [x] (2026-11-06) **Revisão antes de codar (pedido do dono):** (a) tempos: foco 50 min, descanso 10 (longo 20 a cada 4
      ciclos), água a cada 60 min; (b) como o Pulso sabe se o dono fez ou recusou: **fiz** (Bebi / Fiz a pausa),
      **depois** (adia 10 min a água, 5 min o descanso), **recusei** ("Hoje não") e **ignorei** (5 min sem resposta, só
      contados com o dono presente e a observação ligada). Novos `kind` (`water_declined`, `water_ignored`,
      `break_snoozed`, `break_declined`, `break_ignored`) no `CHECK` e na migração v1; PRD F07/F08 e doc 05 atualizados.
- [x] (2026-11-06) **Pendência cumulativa:** recusei = 2, ignorei = 1, depois = 0; o pet fica **nervoso com 3 ou mais** e só
      o "fiz" zera (não esfria sozinha). A pendência é **calculada de `habit_event`** (sobrevive a fechar o app) e é
      **separada para água e pausa** (cada "fiz" zera só o seu hábito; nervoso se qualquer um passar do limite).
      Botão "💧 Bebi" e "☕ Fiz a pausa" sempre visíveis na aba Pet; rosto nervoso = "preocupado" com olhos mais
      arregalados e leve tremor, que **vence o humor da rede** até o dono admitir (a rede segue decidindo por baixo);
      a legenda diz o motivo ("ficaram lembretes de água sem resposta"). Suavizar/desligar o nervoso fica para a
      etapa 7 (F10); até lá o nervoso sempre age.
- [x] (2026-11-06) `habits/reminder.py` (lembrete que pergunta e espera, comum à água e ao descanso), `habits/water.py` e
      `habits/pomodoro.py`: máquinas de estado puras, testadas com relógio falso (inclusive "o ócio adia o lembrete").
      `habits/coach.py` junta as máquinas ao banco e calcula o nervoso.
- [x] (2026-11-06) `storage/db.py`: `habit_event`, `meta` e migração v1 (recusa banco de versão mais nova).
- [x] (2026-11-06) Interface: contador do pomodoro (Iniciar / Pausar / Continuar / Pular), balão do lembrete com
      Bebi · Depois · Hoje não (a linha "Depois/Hoje não" só existe durante o lembrete e a janela cresce uma linha)
      e notificação do Windows (`ui/notifier.py`, `QSystemTrayIcon`).
- [x] (2026-11-06) Eventos de hábito → recompensas: atendido +1, recusei −1, ignorei −0,5, depois 0 (× peso das regras,
      0,3). Com a observação pausada o evento é anotado, mas a rede não aprende.
- [x] (2026-11-06) Teste: o pomodoro não afeta a pausa de privacidade e vice-versa (`tests/habits/`, `tests/ui/test_habits_ui.py`).
- [x] (2026-11-06) Diário: máquinas de estado, relógio injetável e por que os hábitos são regras e não rede (e o que muda
      no F12).
- [x] (2026-11-06) **Adiantado da etapa 7, a pedido do dono:** o pet não pode depender de abrir e clicar. `ui/tray.py` (ícone sempre
      visível, menu e avisos), **X da janela → esconde na bandeja** (com aviso na 1ª vez) e **Sair do Pulso** encerra de
      verdade; **Sempre à frente** (padrão: ligado), **Lembrete de água** e **Iniciar com o Windows** ligáveis no menu
      (`storage/config.py` guarda os dois primeiros em `config.toml`; o início com o Windows é a chave `Run` do usuário,
      `storage/autostart.py`); pomodoro iniciar/pausar/pular também pelo menu da bandeja.
- [ ] **Falta (dono):** uso real do J04 (a notificação do Windows aparecer de fato, os tempos 50/10/60 no dia a dia), o
      "Iniciar com o Windows" de verdade (reiniciar e ver o pet abrir) e o fim de sessão do Windows com o pet aberto.
- **Pronto quando:** os critérios de F07 e F08 passam e a J04 funciona de ponta a ponta.

## Etapa 7 — Saúde, ajustes, bandeja e atalho (F09, F10, atalho de F02)
**Objetivo:** o programa completo do MVP.
**Depende de:** Etapa 6
- [ ] `health_tab.py`: hoje e últimos 7 dias, com o aviso de "não é orientação médica".
- [ ] `storage/config.py` (TOML, padrões, limites) e `settings_dialog.py`, incluindo "Recomeçar cérebro" com
      backup.
- [x] (2026-11-06, adiantado na etapa 6) `tray.py`: menu, fechar → bandeja, Sair → salva. **Falta:** ícones por estado (normal,
      pausado, descanso).
- [ ] `hotkey.py`: `RegisterHotKey` e `WM_HOTKEY` no Qt. **Validar** (TRD §13); se falhar, plano B com thread
      de mensagens.
- [x] (2026-11-06, adiantado na etapa 6) Iniciar com o Windows (chave `Run` do usuário, em vez do atalho na pasta Inicializar).
- [ ] Diário: privacidade por desenho (o que o Pulso nunca vê) e como o atalho global funciona sem *keylogger*.
- **Pronto quando:** os critérios de F02, F09 e F10 passam por completo.

## Etapa final — Entrega v1.0
- [ ] Revisar os critérios de aceite de F01–F11, um por um, com a data da prova.
- [ ] README final: capturas e GIF, instalação, "como funciona o cérebro" (diagrama), privacidade, roteiro
      (F12+) e link para o diário.
- [ ] Rodar 1 semana no uso real e registrar no diário se a meta de aprendizado do PRD §4 foi atingida.
- [ ] Tag `v1.0.0` e *release* no GitHub com notas.

## Riscos e pontos de atenção
| Risco | Impacto | Como reduzir |
|-------|---------|--------------|
| A rede não aprende nada útil (pesos saturam ou não mudam) | Alto: é o coração do projeto | Testes de aprendizado com cenário roteirizado na etapa 3, antes da interface; normalização de pesos; gráficos na etapa 5 |
| Dois relógios confundidos (tempo de rede × real) | Alto: a recompensa cai nas sinapses erradas | Constantes nomeadas com unidade (`tau_e_net_ms`); teste específico de recompensa atrasada |
| Simulação pesa a CPU | Médio | Medição na etapa 2 e na 4; tamanho configurável; thread se precisar |
| `WM_HOTKEY` não chega ao Qt | Baixo | Plano B com thread de mensagens; o botão e a bandeja já cobrem a pausa |
| Antivírus estranha a leitura da janela ativa | Baixo | Sem *hooks*; APIs comuns e documentadas; explicado no README |
| Dado pessoal vazar para o GitHub | Alto | `.gitignore`, testes com pasta temporária, dados fora da pasta do projeto (`%LOCALAPPDATA%`) |
| Sessão de chat longa consome a cota | Médio | Uma conversa por etapa; estado nos docs e no diário |

## Histórico de revisões
| Data | Mudança |
|------|---------|
| 2026-11-05 | Versão inicial |
| 2026-11-05 | Etapa 0 concluída: repositório `AndreiBataglia/pulso`, PR #1 com CI verde, tag `v0.0.0` |
| 2026-11-06 | Etapa 5: o rodapé mostra o custo por volta de 1 s (não por passo); o mapa de pesos ganhou o modo "só o que mudou" |
| 2026-11-06 | Adiantado da etapa 7 (pedido do dono): bandeja com menu, X → bandeja, Sair, sempre à frente, iniciar com o Windows e interruptor da água |
| 2026-11-06 | Etapa 6: hábitos (pomodoro, água, pendência cumulativa e rosto nervoso) implementados; falta o uso real e a bandeja (etapa 7) |
| 2026-11-06 | Etapa 2 concluída (custo medido: 1,6 ms por segundo real, sem thread); contrato `Engine` cresce por etapas |
