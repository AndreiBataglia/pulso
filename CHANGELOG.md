# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versões seguem [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado
- Fundação do projeto: `pyproject.toml`, layout `src/pulso/`, comando `pulso --version`, testes e CI (etapa 0).
- Sensores de nível B (CPU, RAM, hora, ociosidade, categoria do programa em primeiro plano e trocas por minuto),
  relógio injetável, laço mínimo com pausa de privacidade e `pulso --print-sensors` (etapa 1).
- Cérebro sem aprendizado: neurônio LIF, rede de pulso em numpy (entrada de Poisson, oculta 80E+20I, saída com
  inibição lateral), contrato `Engine`, codificador, decodificador com histerese e
  `pulso --print-brain [--fake-sensors]` (etapa 2). Custo medido: 1,6 ms por segundo real.
- Aprendizado: STDP com rastro de elegibilidade e dopamina como erro de previsão (R-STDP) na oculta→saída,
  `Engine.reward`, regras de recompensa (dono e automáticas, com filtro de cliques repetidos),
  `cerebro.npz` com versão e gravação atômica, `AutoSaver` e semente guardada (etapa 3).
  Custo medido: 2,7 ms por segundo real. Limitação conhecida: 1 de 6 sementes não aprende o cenário de teste.
- O pet aparece: janela PySide6 com o rosto desenhado em QPainter (5 humores e "dormindo", transições suaves,
  piscar e olhar de lado), balão de fala, botões Carinho, Bronca e Pausa (só ícone), janela no tamanho mínimo, selo
  de pausa (só aparece pausado), legenda do humor, reação ao carinho/bronca, boas-vindas no primeiro uso, tema claro/escuro do Windows e `PetController`
  (o laço de 1 s sem Qt). `pulso` abre a janela (`--fake-sensors` usa o roteiro falso) (etapa 4).
- Aba **Cérebro** (pyqtgraph): raster de pulsos por camada, potencial de 3 neurônios, dopamina com a cor de quem a deu,
  pulsos por humor, mapa de pesos (com modo "só o que mudou"), ❓ em cada gráfico, congelar/continuar, Ctrl+1/Ctrl+2
  e rodapé com o custo da rede. `Engine.snapshot()` e `Engine.reward` devolvendo a dopamina (etapa 5). Custo medido:
  ~13 ms por volta de 1 s com a aba visível e nenhum a mais com ela escondida ou a janela minimizada.

### Alterado
- A barra de abas aparece (Pet · Cérebro); a janela cresce ao abrir o Cérebro e volta ao tamanho do pet.
- `Engine.reward` passa a devolver a dopamina entregue (`value − r̄`).
- Primária clara escurecida de `#0F8A7E` para `#0D7F74`: o texto branco do botão dava 4,24:1 (mínimo 4,5:1).
- `pulso` sem argumentos agora abre o app (antes imprimia a ajuda).
