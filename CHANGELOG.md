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
