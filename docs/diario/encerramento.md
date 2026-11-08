# Encerramento do projeto (2026-11-07)

O Pulso para na **v0.8.0**. O repositório continua público para quem quiser reaproveitar o código.

## O que deu certo
- Uma rede de pulso (LIF + R-STDP) em numpy puro, pequena e testada, que de fato aprende em simulação.
- Um ciclo de foco por presença, um lembrete de água e de pausa, e uma janela com a vida na bandeja.
- Privacidade por desenho: nível B de sensores, sem teclas nem títulos de janela, e um modo que apaga tudo.
- Um diário por etapa com os conceitos explicados (`docs/diario/`).

## O que não deu certo
O projeto começou como "um bichinho com humor que nasce da rede" e foi se estreitando: o rosto passou a seguir regras
(porque o humor da rede ninguém confirmava) e a rede ficou só com o momento do lembrete da pausa. Isso é pouco
aprendizado para o tamanho da máquina. A causa de fundo: a rede só aprende bem onde há um sinal confiável, e os
sensores grosseiros quase não enxergam um dia de trabalho feito lendo código e revisando o que um agente fez.

## Se alguém quiser continuar
1. Dar à rede um sinal que valha: eventos de um agente (só metadados), ritmo de revisão, tempo de resposta.
2. Aprendizado sem rótulo: prever o próprio dia (erro de previsão como "surpresa") e agrupar estados de uso por STDP.
3. Medir o aprendizado no uso real: gravar a decisão da rede em cada lembrete e mostrar o aceite de primeira por dia,
   idealmente com dias de controle em que a rede é ignorada.
4. Terminar a etapa 8 e o instalador (ver o plano em `docs/06-implementation-plan.md`).

## Como apagar tudo
Ajustes → Remover o Pulso…, ou `pulso --remover`. Depois `pip uninstall pulso`.
