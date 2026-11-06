# Etapa 2 — O neurônio e a rede (2026-11-06)

> Objetivo: a rede pulsa e escolhe um humor, ainda sem aprender.

## O que foi feito
- `brain/lif.py`: o neurônio LIF (`LIFParams`, `LIFPopulation`), vetorizado em numpy.
- `brain/engine.py`: o contrato `Engine` e o `StepResult`.
- `brain/numpy_engine.py`: a rede (entrada de Poisson → oculta 80E + 20I → saída 5 × 10, com inibição lateral).
- `brain/encoding.py`: `SensorFrame` → 63 taxas de pulso.
- `brain/decoding.py`: contagem por grupo → humor, com histerese.
- `sensors/fake.py`: `demo_scenario()`, quatro "momentos do dia" para ver o humor mudar sem ler o PC.
- `pulso --print-brain [--fake-sensors] [--max-seconds N]`: o humor a cada 10 s.
- 43 testes novos (60 no total), incluindo o contrato do `Engine` e a medição de custo.

## Conceitos aprendidos

### O neurônio LIF (*leaky integrate-and-fire*)
Um balde furado. O potencial de membrana `V` é o nível de água:

    V  ←  V + (dt / τm) · (V_repouso − V + drive)  +  saltos_sinápticos

- **Vazamento:** o termo `V_repouso − V` puxa `V` de volta para −65 mV. Quanto menor a `τm` (20 ms), mais
  rápido o balde esvazia.
- **Integração:** cada pulso que chega dá um salto em `V` igual ao peso da sinapse (em mV).
- **Disparo:** se `V` chega a −50 mV, o neurônio dispara, `V` volta a −65 mV e ele fica **refratário** 2 ms
  (não reage a nada, como um balde que acabou de ser virado).

Traço real do nosso código, com um empurrão constante de 25 mV (`*` = valor de `V` a cada 1 ms; o pico em
−49 é só a marca do disparo):

```
 -49.0 |                 *                   *                   *                   *                   *
 -51.1 |              ***                 ***                 ***                 ***                 ***
 -53.2 |          ****                ****                ****                ****                ****
 -55.4 |        **                  **                  **                  **                  **
 -57.5 |     ***                 ***                 ***                 ***                 ***
 -59.6 |   **                  **                  **                  **                  **
 -61.8 | **                  **                  **                  **                  **
 -63.9 |*                   *                   *                   *                   *
 -66.0 |                  **                  **                  **                  **                  **
       +----------------------------------------------------------------------------------------------------
spikes em t = [17, 37, 57, 77, 97]   →   um pulso a cada 20 ms = 50 Hz
```

**Frequência teórica.** Com o empurrão `D` (a tensão para a qual `V` tenderia se nada o interrompesse), o
tempo entre pulsos é `t_ref + τm · ln(D / (D − 15))`. Para `D = 25`: `2 + 20 · ln(2,5) ≈ 20,3 ms`, ou
~49 Hz. O código deu 50 Hz. O teste (`test_lif.py`) confere isso para `D` = 20, 30 e 50 mV, com 10% de folga
porque o método de Euler com passo de 1 ms erra um pouco. Há ainda um limiar (*rheobase*): com `D ≤ 15 mV` o
neurônio **nunca dispara**, por mais que se espere.

### Codificação por taxa
A rede só entende pulsos, e os sensores dão números. A ponte é a **taxa**: quanto maior o valor, mais pulsos
por segundo. Cada entrada é um gerador de **Poisson**: a cada milissegundo sorteia-se um número e, se ele for
menor que `taxa · dt` (100 Hz = 10% por ms), sai um pulso. O pulso exato é aleatório, mas a média é a taxa.

- **Números** (CPU, RAM, ociosidade, trocas) viram um par de grupos: "alto" (taxa = x) e "baixo" (taxa = 1 − x).
  Assim a rede reage a "pouca CPU" tão facilmente quanto a "muita", sem depender de peso negativo.
- **Rótulos** (categoria, faixa de 4 h do dia) são *one-hot*: um grupo por valor, só o atual dispara.
- Cada valor lógico é repetido 3 vezes (`REPEAT`): a média de 3 geradores ruidosos é menos ruidosa que 1.
- Leitura inválida → silêncio total. A rede não recebe informação inventada.

Total: (4 números × 2 + 7 categorias + 6 faixas) × 3 = **63 entradas**.

### Inibição lateral (*winner-take-all*)
Na saída há 5 grupos de 10 neurônios, um por humor. Cada neurônio **inibe todos os neurônios dos outros
grupos** (e nenhum do próprio). Quando um grupo começa a ganhar, ele cala os rivais, o que o deixa ainda mais
forte: uma competição em que o vencedor leva quase tudo. Sem isso, os 5 grupos disparariam parecido e o
vencedor seria quase sorteio.

### Histerese
O humor só é decidido a cada 10 s (somando os pulsos da janela), e o desafiante precisa passar o humor atual
por mais de 25%. É o termostato: liga num ponto e desliga em outro, para não ficar ligando e desligando
quando a temperatura está bem no limite.

### Excitatórios e inibitórios na camada oculta
80 neurônios excitatórios (pesos ≥ 0) e 20 inibitórios (pesos ≤ 0). Sem os inibitórios, a atividade
se retroalimenta e a rede dispara toda de uma vez. É a proporção 80/20 observada no córtex.

### Por que ~200 neurônios bastam
Esta é a justificativa, não uma prova: (1) a decisão é grosseira, 5 humores a partir de ~60 números; (2) a
camada oculta funciona como um conjunto de "características aleatórias" que a saída combina, e 100 delas já
dão variedade de sobra para separar poucos contextos; (3) o ruído dos pulsos cai com a raiz do número de
neurônios que "votam" (10 por humor); (4) mais neurônios custariam CPU o tempo todo. Se a etapa 3 mostrar
que falta capacidade, `NetworkConfig` permite crescer sem mexer no resto.

## Medições

### Custo (orçamento do TRD §5.1: 20 ms por segundo real)
**1,6 ms** para os 100 passos de 1 s real, nesta máquina (Python 3.13, numpy). Cerca de 12× abaixo do
orçamento, então **não precisa de thread**: a decisão do TRD §5.1 continua valendo (laço único no `QTimer`).
O teste `test_cost_of_one_real_second_fits_the_budget` falha se passar de 20 ms.

### Atividade da rede
Com os pesos calibrados, a camada oculta dispara em média ~21 Hz por neurônio quando o roteiro de demonstração
está rodando. Os pesos iniciais saíram de experimentos (valores
anteriores deixavam a saída muda ou saturada) e ficaram em `NetworkConfig`: entrada → oculta 4 mV, oculta →
saída 4 mV, inibição lateral 3 mV.

### O humor muda com o contexto? Sim, mas ainda sem sentido próprio
Com pesos sorteados, o humor mudou entre os 4 momentos do roteiro em **8 de 10 sementes**; nas outras 2,
um grupo ganhou em todos os contextos. O teste exige ≥ 6 de 10 para não ficar frágil. Isso é esperado: a rede
ainda **não aprendeu** nada, então "sonolento na madrugada" é coincidência da semente 1 (que também fica
sonolento de manhã, no código), não conhecimento.
A etapa 3 (STDP + dopamina) é a que dá sentido a essas trocas.

## Como testar
- `pytest` — 60 testes.
- `pulso --print-brain --fake-sensors` — roda o roteiro de 4 minutos em um instante e imprime o humor a cada
  10 s, marcando `(mudou)`. Com a semente usada (1): sonolento até 120 s, contente de 130 a 180 s (o momento do
  chat) e sonolento de novo a partir de 190 s (a madrugada).
- `pulso --print-brain` — com os sensores reais, em tempo real; só imprime o humor, nunca dados dos sensores.
  Foi rodado 20 s no teste real e funcionou.

## Decisões e observações
- O contrato `Engine` cresce por etapas: agora `step`, `state_dict`, `load_state_dict`; `reward` entra na
  etapa 3 e `snapshot` na 5. Não coloquei métodos "de enfeite" que ainda não fazem nada.
- `state_dict` guarda os **4 conjuntos de pesos** (não só os plásticos), senão carregar numa rede com outra
  semente daria conexões fixas incoerentes com os pesos carregados.
- O tamanho de entrada padrão do motor (63) é repetido em `NetworkConfig` para o motor não importar o
  codificador; um teste garante que os dois números casam.
- As linhas do `ruff` ficaram em 100 colunas (a configuração do `pyproject.toml`), embora o TRD §5 diga 120;
  vale alinhar o doc na revisão da etapa.

## Tropeços (para não repetir)
- Um script que escreve `"\n"` dentro de texto Python o transformou em quebra de linha de verdade e quebrou o
  arquivo: para texto com `\n`, usar a ferramenta Edit.
- Com relógio falso e sem limite de passos, o laço nunca para. No modo falso o padrão agora é a duração do roteiro.

## Ficou para depois
- Aprendizado (STDP, elegibilidade, dopamina) e gravar os pesos em disco: etapa 3.
- `snapshot()` e os gráficos: etapa 5.
- Escolher a semente do cérebro de verdade (hoje 1 para a demonstração) e como ela é guardada: etapa 3 (`brain_store`).
