# Pulso (projeto_tamagotchi)

Companheiro de desktop para Windows, com rede neural de pulso (LIF + R-STDP em numpy), pomodoro e lembrete de
água. Projeto público no GitHub (MIT), independente do hub_service. O dono quer **aprender** enquanto
construímos: explique os conceitos e registre-os no diário de cada etapa.

## Documentação do projeto
Antes de implementar algo, consulte `docs/` (índice em `docs/README.md`):
PRD (o quê), TRD (stack/decisões), App Flow (navegação), Design Brief (visual),
Back-end Schema (dados) e Implementation Plan (ordem de construção).
Se uma decisão mudar durante o trabalho, atualize o documento correspondente.

## Regras que não podem ser quebradas
- Privacidade: sensores só de nível B (metadados e nome do processo). O título da janela e as teclas **nunca**
  são lidos. A pausa para os sensores de verdade. Dados de sensor nunca vão para disco nem para o log.
- Os testes usam pasta temporária e sensor falso, nunca os dados reais do dono.
- Commit, push, PR e tag só com autorização explícita do dono, a cada vez (ritual no doc 06).
- Identificadores em inglês; comentários, docstrings e docs em português.
