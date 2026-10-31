# AutoScan Pro

Simulador didático de diagnóstico automotivo, feito como projeto acadêmico para o SENAI.

> **Importante:** a versão 1.0 é uma **simulação**. Ela não se conecta a veículos, ECU ou adaptadores ELM327. Os códigos OBD-II usados são reais, mas todas as leituras e falhas são geradas pelo simulador interno.

## Estado atual

| Fase | Situação |
|---|---|
| 1. Fundação (Flask, SQLite, `/api/health`) | Concluída |
| 2. Layout, tema escuro e navegação | Concluída |
| 3. Cadastro de veículos e veículo ativo | Concluída |
| 4 a 10 | Pendentes (ver `DEVELOPMENT_PLAN.md`) |

As telas que ainda não foram implementadas abrem normalmente e informam em qual fase ganham funções. Elas não exibem botões sem ação.

## Requisitos

- Windows 10/11 ou Linux
- Python 3.11 ou mais recente (testado com 3.14.4). No Windows, baixe em <https://www.python.org/downloads/> e marque **"Add python.exe to PATH"** na instalação.
- Internet apenas na instalação (para baixar as dependências). Depois, o programa funciona offline.

## Instalação

Se você recebeu o projeto pelo GitHub, baixe-o primeiro (botão **Code → Download ZIP** e extraia, ou `git clone <endereço do repositório>`).

A pasta `.venv` **não** vai junto no repositório: cada computador cria a sua. No terminal, dentro da pasta do projeto:

```bash
python -m venv .venv
```

Ative o ambiente virtual:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (Prompt de Comando): `.venv\Scripts\activate.bat`
- Linux: `source .venv/bin/activate`

Instale as dependências:

```bash
pip install -r requirements.txt
```

> Se o PowerShell bloquear o `Activate.ps1`, rode uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, ou use os comandos sem ativar o ambiente: `.venv\Scripts\python run.py`.

## Execução

```bash
python run.py
```

Abra <http://127.0.0.1:5000> no navegador. Para conferir só a API, abra <http://127.0.0.1:5000/api/health>.

Se a porta 5000 estiver ocupada, escolha outra antes de iniciar. No PowerShell: `$env:PORT=5050; python run.py`.

O banco SQLite é criado automaticamente em `instance/autoscan.db` na primeira execução. Cada computador tem o seu banco, e ele não vai para o repositório. Para começar do zero, pare o servidor e apague esse arquivo.

## API de veículos

| Método | Endereço | Ação |
|---|---|---|
| GET | `/api/vehicles` | Lista os veículos (o ativo vem primeiro) |
| POST | `/api/vehicles` | Cadastra (201) |
| GET | `/api/vehicles/<id>` | Detalhes (404 se não existir) |
| PUT | `/api/vehicles/<id>` | Atualiza |
| DELETE | `/api/vehicles/<id>` | Exclui (204), ou 409 se houver histórico |
| POST | `/api/vehicles/<id>/activate` | Define como veículo ativo |

Erros de validação retornam 422 com uma mensagem por campo:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "Verifique os campos informados.",
           "fields": {"year": "Informe um ano entre 1996 e 2027."}}}
```

## Testes

```bash
python -m pytest
```

## Estrutura

```
app/
  __init__.py     cria a aplicação Flask (create_app)
  config.py       configurações centrais
  db.py           conexão SQLite e criação das tabelas
  schema.sql      esquema do banco (ver DATA_MODEL.md)
  errors.py       respostas de erro (JSON na API, página HTML nas telas)
  icons.py        ícones SVG locais
  routes/         rotas HTTP (sem regra de negócio); pages.py lista as telas do menu
  services/       regras de negócio
  templates/      HTML (Jinja); base.html tem a sidebar e o cabeçalho
  static/         CSS, JavaScript e imagens (tudo local, funciona sem internet)
tests/            testes pytest
run.py            inicia o servidor local
```

## Documentos de especificação

- `CLAUDE.md`: instruções persistentes para o Claude Code.
- `PROJECT_SPEC.md`: visão, escopo, módulos e critérios de aceitação.
- `DATA_MODEL.md`: estrutura do banco SQLite.
- `API_SPEC.md`: contrato da API REST.
- `DEVELOPMENT_PLAN.md`: fases de implementação.
- `TEST_PLAN.md`: testes e critérios de qualidade.
- `INITIAL_PROMPT.md`: prompt usado para iniciar o trabalho.

## Decisões registradas

- Todas as tabelas são criadas já na Fase 1, a partir de `app/schema.sql`. O script é idempotente e roda a cada inicialização.
- O banco garante que só um veículo esteja ativo por vez, com um índice único parcial.
- A tabela `diagnostics` tem `findings_json` para guardar o resultado das regras no momento da varredura. Assim o histórico não muda se as regras mudarem depois.
- A coluna `source` só aceita `simulation` na versão 1.0.
- O cadastro de veículo não tem campo de identificador/VIN, para não induzir o uso de dados reais.
- Limites didáticos do cadastro: ano de 1996 (início da obrigatoriedade do OBD-II nos EUA) até o ano seguinte ao atual; quilometragem de 0 a 2.000.000 km; fabricante e modelo com até 60 caracteres. Ficam em `app/services/vehicles.py`.
- O primeiro veículo cadastrado vira o ativo automaticamente. Os seguintes precisam ser ativados com o botão "Ativar".
- Política de exclusão: um veículo com diagnósticos no histórico **não pode ser excluído** (resposta 409, com explicação). O histórico é preservado.
- O servidor escuta apenas em `127.0.0.1` (não fica acessível pela rede).
- A interface usa páginas separadas renderizadas pelo Flask (uma URL por tela), não uma aplicação de página única. Ao trocar de tela, os timers da anterior são encerrados automaticamente.
- Nenhum arquivo é carregado da internet (fontes do sistema, ícones SVG locais), porque a apresentação será em outro computador, possivelmente offline.

## Limitações

- Sem conexão real com veículo (fora do escopo da versão 1.0).
- Sem login: a aplicação é local e de uso único.
