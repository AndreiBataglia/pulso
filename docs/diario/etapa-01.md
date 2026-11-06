# Etapa 1 — Sensores e pausa de privacidade (2026-11-06)

> Objetivo: ver no terminal o que o Pulso "sente" e provar que a pausa desliga tudo.

## O que foi feito
- `clock.py`: relógio injetável (`SystemClock` e `FakeClock`).
- `sensors/base.py`: `SensorFrame` (a leitura de 1 s) e o protocolo `Sensor`.
- `sensors/categories.py`: tabela processo → categoria; desconhecido cai em "outro".
- `sensors/fake.py`: `ScriptedSensor`, que segue um roteiro e conta quantas vezes foi lido.
- `sensors/windows.py`: o sensor real (psutil + ctypes).
- `loop.py`: `SensorLoop` com `pause()`/`resume()`.
- `pulso --print-sensors`: uma linha por segundo, sem gravar nada.
- 17 testes, incluindo o de pausa (zero chamadas) e o *grep* de privacidade.

## Conceitos aprendidos

### Como o Windows informa a janela ativa
`GetForegroundWindow()` devolve o *handle* (número de identificação) da janela em primeiro plano.
`GetWindowThreadProcessId()` traduz esse handle no **PID** (número do processo dono da janela). Com o PID,
o `psutil.Process(pid).name()` dá o nome do executável (`code.exe`). Só esse nome vira categoria.

### Como o Windows informa a ociosidade
`GetLastInputInfo()` guarda o instante (em ms desde que o Windows ligou) da última tecla ou movimento de mouse
**de qualquer programa**, sem dizer qual tecla foi. `GetTickCount()` dá o "agora" na mesma escala; a
diferença é a ociosidade. Os dois contadores são de 32 bits e dão a volta a cada ~49 dias, por isso a conta
usa módulo `2**32`. Isso **não é um *keylogger***: o Windows só diz *quando*, nunca *o quê*.

### Por que o título da janela não é lido
O título costuma ter conteúdo pessoal (assunto de e-mail, nome de documento, página aberta). O nome do
processo basta para saber "isto é código" ou "isto é navegador". O que não se lê não pode vazar; por isso
um teste varre `src/` e falha se aparecer a função que lê títulos (ou qualquer outra de teclado/hook).

### ctypes
Biblioteca padrão do Python para chamar funções de DLLs (aqui, `user32` e `kernel32`) sem instalar nada.
Cuidado: declarar o tipo de retorno (`restype`) evita que um número de 64 bits seja truncado.

### Relógio injetável
O código recebe um `Clock` em vez de chamar `time` direto. No teste, o `FakeClock` avança o tempo sem
esperar: o teste das trocas por minuto "passa 61 s" em microssegundos.

### Pausa de verdade
`tick()` testa `paused` **antes** de chamar o sensor. O `ScriptedSensor.calls` prova: 50 voltas pausado, zero
leituras. Pausa que só "esconde" o resultado não serviria.

### Falha vira "desconhecido"
Se o sensor lança um erro, o laço devolve `SensorFrame.unknown()` (`valid=False`, valores neutros) e segue.
No log vai só o **tipo** do erro, nunca a mensagem, que poderia carregar dado do sensor.

## Como testar
- `pytest` — roda tudo (17 testes).
- `pulso --print-sensors` — alterne entre VS Code e o navegador e veja a coluna `categoria` mudar;
  mexa o mouse e veja `ocioso` voltar a 0. `Ctrl+C` para parar.

## Decisões e observações
- O `SensorFrame` ficou com `cpu_percent`, `ram_percent`, `hour_of_day`, `idle_seconds`, `category`,
  `app_switches_last_min` e `valid`.
- O `--print-sensors` mostra a categoria, não o nome do processo.
- Trocas por minuto: janela deslizante de 60 s guardando só instantes. A primeira leitura não conta como troca.

## Ficou para depois
- Botão, ícone da bandeja e atalho global da pausa (dependem da interface, etapa 4+).
- Ler a tabela de categorias extras do `config.toml` (etapa de configuração).
