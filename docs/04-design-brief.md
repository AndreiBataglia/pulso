# Design Brief (UI/UX) — Pulso

> Direção visual e de experiência: como o app deve **parecer** e **se comportar**,
> para que cada tela nova siga o mesmo padrão em vez de ser criada ao acaso.
> Última revisão: 2026-11-05

## 1. Personalidade e princípios
**Fofo, curioso, discreto, transparente.**
- **O Pulso é o protagonista** na aba T01; os controles ficam embaixo dele, pequenos.
- **Discreto:** nada de som por padrão, nada de pular na frente do trabalho. Os avisos vão para a notificação do
  Windows e para o balão do Pulso.
- **Transparente:** o dono sempre sabe se o Pulso está dormindo (olhos fechados + selo "😴 Observação pausada" em T01 e no ícone da
  bandeja).
- **Didático:** cada gráfico do cérebro tem um ❓ que explica o que ele mostra em uma ou duas frases.

## 2. Referências
- **Tamagotchi:** um ser simples, com poucas expressões bem legíveis.
- **Neko / Desktop Goose:** o "bichinho que mora no PC", mas aqui comportado (não atrapalha).
- **LOOI (TangibleFuture):** robô de mesa que usa o celular como rosto. Não copiamos o robô, só a lição:
  **olhos animados sobre fundo escuro carregam o humor com poucos elementos**. Ver §7.1.
- **Painéis de neurociência (Brian2, NEST):** raster de pulsos clássico, com pontos pretos sobre fundo claro.
- **Forest / Pomofocus:** o foco com um contador grande e um único botão.

## 3. Paleta de cores
O tema acompanha o Windows (claro ou escuro).

| Papel | Claro | Escuro | Uso |
|-------|-------|--------|-----|
| Fundo | `#F7F7F5` | `#16181D` | Janela |
| Superfície | `#FFFFFF` | `#20232A` | Cartões, balão de fala |
| Texto principal | `#1F2328` | `#E6EDF3` | |
| Texto secundário | `#59636E` | `#9198A1` | Legendas, rodapés |
| Primária | `#0D7F74` | `#3CC6B5` | Botões principais, dopamina positiva |
| Sucesso / Aviso / Erro | `#1A7F37` / `#9A6700` / `#CF222E` | `#3FB950` / `#D29922` / `#F85149` | Mensagens; erro também = dopamina negativa |

**Cor do Pulso por humor** (cor dos olhos e da boca, desenhados sobre o fundo escuro do rosto):

| Humor | Cor | Expressão |
|-------|-----|-----------|
| Animado | `#FFB347` laranja | Olhos grandes, boca aberta, pulinho |
| Contente | `#7BD389` verde | Olhos em arco, sorriso |
| Entediado | `#A3B1C6` cinza-azulado | Olhos semicerrados, boca reta |
| Sonolento | `#B59CE6` lilás | Olhos fechando, "z" flutuando |
| Preocupado | `#F28C8C` rosado | Sobrancelhas inclinadas, gota de suor |
| Dormindo (pausa) | `#8A8F98` cinza | Olhos fechados, "zzz", sem animação |

- **Contraste:** o texto deve ter pelo menos 4.5:1 (WCAG AA), conferido na etapa 4 por `tests/ui/test_theme.py`
  (a primária clara foi escurecida de `#0F8A7E` para `#0D7F74`: o texto branco do botão dava só 4,24:1).
- **Cor nunca sozinha:** humor e estado têm sempre forma ou texto junto.

## 4. Tipografia
| Uso | Fonte | Tamanho | Peso |
|-----|-------|---------|------|
| Título da aba / cronômetro do foco | Segoe UI | 28 px | Semibold |
| Fala do Pulso | Segoe UI | 15 px | Regular |
| Corpo e botões | Segoe UI | 13 px | Regular |
| Números do cérebro (ms, contagens) | Cascadia Mono (cai para Consolas) | 12 px | Regular |

## 5. Espaçamento e layout
- Grade de 8 px; margens de 16 px; espaço de 8 px entre botões.
- Janela padrão de ~520×640, redimensionável. Em T01, o Pulso ocupa ~55% da altura. A janela do Pulso abre no **menor**
  tamanho; ao abrir o Cérebro ela cresce para ~520×760 (mínimo 420×700) e volta ao tamanho do Pulso ao voltar.
- Abas no topo: **Pulso · Jogo · Cérebro · Saúde**, com o botão ⚙ à direita.

## 6. Componentes
- **Botões:**
  - primário (preenchido): uma ação principal por área, como "Pausar agora" ou "Salvar";
  - secundário (contorno): os demais;
  - perigo (vermelho): só "Recomeçar cérebro", sempre com confirmação.
- **Balão de fala:** superfície com uma ponta virada para o Pulso; pode trazer até 2 botões (Bebi / Depois).
- **Barra de abas:** escondida enquanto houver uma única aba (o título da janela já diz "Pulso"); aparece com a aba Cérebro.
- **Selo de estado:** pílula "😴 Observação pausada" (cinza), **só aparece enquanto pausado**. Observando é o normal e não
  ganha aviso fixo (decisão do dono, 2026-11-06); o rosto sempre explica o humor numa legenda sob ele.
- **Botão de pausa:** só ícone (⏸ pausar / ▶ retomar, desenhados, sem emoji), no topo, ao lado da pílula de modo,
  com dica ao passar o mouse.
- **Tamanho da janela:** abre sempre no menor tamanho possível (e não encolhe além dele). A legenda do humor fica
  **acima** do rosto, e a legenda e o balão reservam 2 e 3 linhas para o rosto nunca ser coberto.
- **Nervoso (etapa 6, a desenhar):** quando as recusas/omissões de hábito acumulam, o rosto fica nervoso e **não sai
  desse humor** até o dono admitir que fez a pausa ou bebeu água; a legenda diz o motivo, sem culpa nem bronca (§8).
- **Reação do rosto:** Carinho deixa o rosto contente por ~2,5 s; depois volta ao humor (a Bronca saiu na etapa 7).
  Toda expressão tem legenda dizendo o que significa (ex.: "Preocupado: a rede está inquieta, mas ainda não sei dizer por quê").
- **Gráficos (pyqtgraph):** só mostram (sem zoom nem menu); ❓ ao lado do título de cada um (dica ao passar o mouse e ao
  clicar); botão **Congelar/Continuar** no topo; Ctrl+1 e Ctrl+2 trocam de aba.
  - fundo igual à superfície e eixos no texto secundário;
  - camadas no raster: entrada = cinza, oculta excitatória = azul, inibitória = vermelho,
    saída = a cor do humor de cada grupo.
- **Diálogo de configurações:** formulário em grupos (Foco, Água, Privacidade, Cérebro, Sistema), com a
  validação ao lado do campo.

## 7. Ícones e imagens
- **Rosto do Pulso desenhado com QPainter**: fundo escuro, olhos e boca, mais pequenos emojis só quando necessário
  (ex.: "z", gota, 💧). Sem corpo. Não usa arquivos de imagem no MVP.
- **Ícone da bandeja:** o rosto do Pulso em 16/32 px, com três variações (normal, pausado com olhos fechados,
  descanso).
- Emojis nos botões (💚 💧; **nunca 👁**, decisão do dono), sempre acompanhados de texto.

### 7.1 Direção visual (inspirada no LOOI)
**Decisão do dono (2026-11-06):** só o **fundo escuro com olhos, boca e alguns pequenos emojis quando
necessário**. Outros elementos podem entrar depois, se forem necessários.
- **Os olhos fazem o trabalho.** O humor se lê pelo formato e pela abertura dos olhos; a boca é secundária.
  A cor do humor (§3) pinta olhos e boca.
- **Pausa = olhos fechados** (F02): fica óbvio, sem texto, que o Pulso não está observando.
- **Microanimações que dão vida:** piscar a intervalos irregulares (3–6 s), olhar para o lado de vez em
  quando e inclinar levemente o rosto. Sem elas o Pulso parece uma imagem parada.
- **Emojis:** pequenos e raros, só para reforçar um estado (💤 sono, 💧 água). Nunca no lugar
  dos olhos.
- **Sem câmera nem sensores extras:** o LOOI tem rodas, LEDs e câmera; o Pulso não usa nada disso.
- Referência (marketing e resenhas): [resenha](https://techbuzzireland.com/2026/02/11/looi-robot-review/),
  [Hackster](https://hackster.io/news/tangiblefuture-s-looi-turns-smartphones-into-ambulatory-companion-robots-with-chatgpt-support-fddc772c62b2).

## 8. Mensagens e tom de voz
O Pulso fala na primeira pessoa, em frases curtas e carinhosas, sem culpa nem bronca.
- ✅ "Psiu! Um gole d'água? 💧" · ❌ "Você não bebe água há 45 minutos."
- ✅ "Hora de esticar as pernas" · ❌ "ALERTA: pausa obrigatória."
- ✅ "Tô de olhos fechados. Me acorda quando quiser." (pausa) · ❌ "Monitoramento desativado."

As mensagens do sistema (erros, ajustes) são neutras e dizem como resolver:
- ✅ "Esse atalho já é usado por outro programa. Escolha outra combinação."

## 9. Telas-chave
**T01 — Pulso**
```
┌──────────────────────────────────────────┐
│ Pulso  Cérebro   Saúde                 ⚙ │
├──────────────────────────────────────────┤
│       (😴 Observação pausada, só se pausado)     │
│  Contente: está tudo tranquilo (legenda) │
│                 ╭─────╮                  │
│                ( ◕ ‿ ◕ )                 │
│                 ╰─────╯                  │
│        ╭──────────────────────────╮      │
│        │ Que bom que você voltou! │      │
│        ╰──────────────────────────╯      │
│                                          │
│   [ 💚 Carinho ]  [ 💧 Bebi   ]  [ ⏸ ]   │
├──────────────────────────────────────────┤
│  18:42 [ Pausar agora ]  💧 4 copos hoje │
└──────────────────────────────────────────┘
```

**T02 — Cérebro**
```
┌──────────────────────────────────────────┐
│ Raster de pulsos ❓  ·:·.:·::·..·:·:·.:·  │
│ Potencial (neurônio 12 ▾) ❓  /\_/\__/|_  │
│ Dopamina ❓  ──^───v──^^─  (💚 dono, ⚙ regra) │
│ Humor ❓  animado ████  contente ██ …     │
│ Pesos oculta→saída ❓  [mapa de calor]    │
│ passo: 2,1 ms · recompensas +37 / −9     │
└──────────────────────────────────────────┘
```

**T03 — Saúde**
```
│ Hoje: 💧 6 copos · 8 focos · maior sequência sem pausa: 1h40 │
│ [barras dos últimos 7 dias: copos e focos]                     │
│ Lembretes de hábito, não é orientação médica.                       │
```

## 10. Acessibilidade
- Tudo funciona pelo teclado: Tab entre os controles, atalhos Ctrl+1/2/3 para as abas e o atalho global de
  pausa.
- Os botões têm texto (não só emoji) e *tooltip*.
- Respeitar o tamanho de fonte do Windows (DPI alto): layout em proporções, nada em pixel fixo, exceto o ícone.
- Animações curtas (< 400 ms). Opção "reduzir animações" nos ajustes, depois do MVP.

## 11. Suposições
- Fonte do sistema (Segoe UI), sem fontes embutidas.
- O desenho do Pulso em formas simples basta para o MVP; a pixel art fica para o F17.

## 12. Perguntas em aberto
- ~~Formato do Pulso~~ — resolvido em 2026-11-06: sem corpo, só fundo escuro com olhos, boca e pequenos emojis (§7.1).

## Histórico de revisões
| Data | Mudança |
|------|---------|
| 2026-11-05 | Versão inicial |
| 2026-11-06 | Direção visual do rosto: fundo escuro, olhos, boca e pequenos emojis, inspirada no LOOI (§2, §3, §7 e §7.1) |
