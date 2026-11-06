# Etapa 0 — Fundação e GitHub (2026-11-05)

> Objetivo: um repositório "profissional" ainda vazio de funcionalidades, mas com testes, lint e CI.

## O que foi feito
- `gh` instalado (`winget install GitHub.cli`) e login feito com `gh auth login --web`.
- `git init -b main`, `pyproject.toml`, layout `src/pulso/`, `.gitignore`, `LICENSE` (MIT), `CHANGELOG.md`, `README.md`.
- `pulso --version` (em `src/pulso/__main__.py`) e um teste que o confere.
- CI em `.github/workflows/ci.yml`: ruff e pytest no `windows-latest`, Python 3.12 e 3.13.
- Decisões: nome do pet e do repositório **Pulso / `pulso`**; licença MIT em nome de Andrei Bataglia.
- Por ora o `pyproject.toml` só declara `numpy` e `psutil`; PySide6 e pyqtgraph entram na etapa 4,
  quando a interface nascer (deixa o CI mais rápido até lá).

## Conceitos aprendidos

### venv (ambiente virtual)
Uma pasta (`.venv/`) com um Python próprio e as bibliotecas só deste projeto. Evita que um projeto
quebre o outro por versões diferentes. Criar: `python -m venv .venv`; ativar: `.venv\Scripts\activate`.
Nunca vai para o Git (está no `.gitignore`).

### pyproject.toml
O "RG" do projeto, num formato padrão (PEP 621): nome, versão, Python mínimo, dependências, extras
(`[dev]` = pytest e ruff, só para quem desenvolve) e **comandos** (`[project.scripts]`: `pulso` chama
`pulso.__main__:main`). O mesmo arquivo guarda a configuração do ruff e do pytest.

### Layout `src/`
O código fica em `src/pulso/`, não na raiz. Assim os testes só importam o pacote **instalado**
(`pip install -e .`), como um usuário faria, e erros de empacotamento aparecem cedo. `-e` (editável)
faz as mudanças no código valerem sem reinstalar.

### pytest e ruff
- **pytest** roda as funções `test_*` em `tests/`; falhou um `assert`, o teste falha.
- **ruff** é o *linter* (acha erros e imports sobrando: `ruff check`) e o formatador (`ruff format`).
  Em `docs/` ele é desligado: lá há trechos de código ilustrativos que não devem ser reescritos.

### CI (integração contínua)
Um robô do GitHub (Actions) que, a cada push ou PR, cria uma máquina Windows limpa, instala o projeto e
roda ruff e pytest. Se algo falha, o selo no README fica vermelho. Prova que "funciona na minha máquina"
também funciona em outra. A matriz testa duas versões do Python.

### Conventional Commits
Padrão de mensagem de commit: `tipo(escopo): resumo`. Tipos comuns: `feat` (novidade), `fix` (correção),
`docs`, `test`, `chore` (manutenção), `ci`. Ex.: `chore: fundação do projeto`. Facilita ler o histórico
e gerar o changelog.

### Fluxo branch → PR → tag
1. Trabalha-se numa **branch** (`etapa-NN-nome`), sem mexer na `main`.
2. Abre-se um **Pull Request**; o CI roda e alguém revisa.
3. Com o CI verde, faz-se o *merge* na `main`.
4. Uma **tag** (`v0.NN.0`) marca aquele ponto da história como uma versão.

### Licença MIT
Permite que qualquer pessoa use, copie e modifique o código, desde que mantenha o aviso de copyright.
Sem garantia nenhuma. Combina com o PySide6 (LGPL) usado mais adiante.

## Como testar
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pulso --version      # pulso 0.0.1
pytest               # 1 passed
ruff check .
ruff format --check .
```

## Ficou para depois
- Criar o repositório público no GitHub, o primeiro push, o PR e a tag: só com autorização do dono.
- Conferir que o CI ficou verde no GitHub (depende do push).
- Pendências do diário da sessão 00 (formato do pet, retomada automática da observação, pomodoro manual
  ou automático) ficam para as etapas em que forem necessárias.
