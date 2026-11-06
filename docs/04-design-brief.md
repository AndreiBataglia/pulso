# Design Brief (UI/UX) — Pulso

> Direção visual e de experiência: como o app deve **parecer** e **se comportar**,
> para que cada tela nova siga o mesmo padrão em vez de ser criada ao acaso.
> Última revisão: 2026-11-05

## 1. Personalidade e princípios
**Fofo, curioso, discreto, transparente.**
- **O pet é o protagonista** na aba T01; os controles ficam embaixo dele, pequenos.
- **Discreto:** nada de som por padrão, nada de pular na frente do trabalho. Os avisos vão para a notificação do
  Windows e para o balão do pet.
- **Transparente:** o dono sempre sabe se está sendo observado (indicador 👁/😴 visível em T01 e no ícone da
  bandeja).
- **Didático:** cada gráfico do cérebro tem um ❓ que explica o que ele mostra em uma ou duas frases.

## 2. Referências
- **Tamagotchi:** um ser simples, com poucas expressões bem legíveis.
- **Neko / Desktop Goose:** o "bichinho que mora no PC", mas aqui comportado (não atrapalha).
- **Painéis de neurociência (Brian2, NEST):** raster de pulsos clássico, com pontos pretos sobre fundo claro.
- **Forest / Pomofocus:** o pomodoro com um contador grande e um único botão.

## 3. Paleta de cores
O tema acompanha o Windows (claro ou escuro).

| Papel | Claro | Escuro | Uso |
|-------|-------|--------|-----|
| Fundo | `#F7F7F5` | `#16181D` | Janela |
| Superfície | `#FFFFFF` | `#20232A` | Cartões, balão de fala |
| Texto principal | `#1F2328` | `#E6EDF3` | |
| Texto secundário | `#59636E` | `#9198A1` | Legendas, rodapés |
| Primária | `#0F8A7E` | `#3CC6B5` | Botões principais, dopamina positiva |
| Sucesso / Aviso / Erro | `#1A7F37` / `#9A6700` / `#CF222E` | `#3FB950` / `#D29922` / `#F85149` | Mensagens; erro também = dopamina negativa |

**Cor do pet por humor** (preenchimento do corpo; os olhos e a boca carregam a expressão):

| Humor | Cor | Expressão |
|-------|-----|-----------|
| Animado | `#FFB347` laranja | Olhos grandes, boca aberta, pulinho |
| Contente | `#7BD389` verde | Olhos em arco, sorriso |
| Entediado | `#A3B1C6` cinza-azulado | Olhos semicerrados, boca reta |
| Sonolento | `#B59CE6` lilás | Olhos fechando, "z" flutuando |
| Preocupado | `#F28C8C` rosado | Sobrancelhas inclinadas, gota de suor |
| Dormindo (pausa) | `#8A8F98` cinza | Olhos fechados, "zzz", sem animação |

- **Contraste:** o texto deve ter pelo menos 4.5:1 (WCAG AA), conferido com uma ferramenta na etapa 4.
- **Cor nunca sozinha:** humor e estado têm sempre forma ou texto junto.

## 4. Tipografia
| Uso | Fonte | Tamanho | Peso |
|-----|-------|---------|------|
| Título da aba / contador do pomodoro | Segoe UI | 28 px | Semibold |
| Fala do pet | Segoe UI | 15 px | Regular |
| Corpo e botões | Segoe UI | 13 px | Regular |
| Números do cérebro (ms, contagens) | Cascadia Mono (cai para Consolas) | 12 px | Regular |

## 5. Espaçamento e layout
- Grade de 8 px; margens de 16 px; espaço de 8 px entre botões.
- Janela padrão de ~520×640, redimensionável. Em T01, o pet ocupa ~55% da altura.
- Abas no topo: **Pet · Cérebro · Saúde**, com o botão ⚙ à direita.

## 6. Componentes
- **Botões:**
  - primário (preenchido): uma ação principal por área, como "Iniciar pomodoro" ou "Salvar";
  - secundário (contorno): os demais;
  - perigo (vermelho): só "Recomeçar cérebro", sempre com confirmação.
- **Balão de fala:** superfície com uma ponta virada para o pet; pode trazer até 2 botões (Bebi / Depois).
- **Selo de estado:** pílula "👁 Observando" (primária) ou "😴 Observação pausada" (cinza), sempre visível em T01.
- **Gráficos (pyqtgraph):**
  - fundo igual à superfície e eixos no texto secundário;
  - camadas no raster: entrada = cinza, oculta excitatória = azul, inibitória = vermelho,
    saída = a cor do humor de cada grupo.
- **Diálogo de configurações:** formulário em grupos (Pomodoro, Água, Privacidade, Cérebro, Sistema), com a
  validação ao lado do campo.

## 7. Ícones e imagens
- **Pet desenhado com QPainter** (formas: corpo arredondado, olhos, boca, extras como "z" e gota). Não usa
  arquivos de imagem no MVP.
- **Ícone da bandeja:** o rosto do pet em 16/32 px, com três variações (normal, pausado com olhos fechados,
  descanso com 🍅).
- Emojis nos botões (💚 💢 💧 🍅 👁), sempre acompanhados de texto.

## 8. Mensagens e tom de voz
O pet fala na primeira pessoa, em frases curtas e carinhosas, sem culpa nem bronca.
- ✅ "Psiu! Um gole d'água? 💧" · ❌ "Você não bebe água há 45 minutos."
- ✅ "Hora de esticar as pernas 🍅" · ❌ "ALERTA: pausa obrigatória."
- ✅ "Tô de olhos fechados. Me acorda quando quiser." (pausa) · ❌ "Monitoramento desativado."

As mensagens do sistema (erros, ajustes) são neutras e dizem como resolver:
- ✅ "Esse atalho já é usado por outro programa. Escolha outra combinação."

## 9. Telas-chave
**T01 — Pet**
```
┌──────────────────────────────────────────┐
│  Pet   Cérebro   Saúde                 ⚙ │
├──────────────────────────────────────────┤
│              👁 Observando               │
│                                          │
│                 ╭─────╮                  │
│                ( ◕ ‿ ◕ )                 │
│                 ╰─────╯                  │
│        ╭──────────────────────────╮      │
│        │ Que bom que você voltou! │      │
│        ╰──────────────────────────╯      │
│                                          │
│      [ 💚 Carinho ]  [ 💢 Bronca ]       │
├──────────────────────────────────────────┤
│  🍅 18:42  [ Pausar ]     💧 4 copos hoje │
│            [ 👁 Pausar observação ]       │
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
│ Hoje: 💧 6 copos · 🍅 8 pomodoros · maior sequência sem pausa: 1h40 │
│ [barras dos últimos 7 dias: copos e pomodoros]                     │
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
- O desenho do pet em formas simples basta para o MVP; a pixel art fica para o F17.

## 12. Perguntas em aberto
- Preferência de formato do pet (bolinha, gato, fantasminha…)? Suposição: uma "bolinha" com olhos, neutra.

## Histórico de revisões
| Data | Mudança |
|------|---------|
| 2026-11-05 | Versão inicial |
