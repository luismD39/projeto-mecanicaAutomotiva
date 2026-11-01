# AutoScan Pro

Simulador didático de diagnóstico automotivo, feito como projeto acadêmico para o SENAI.

> **Importante:** a versão 1.0 é uma **simulação**. Ela não se conecta a veículos, ECU ou adaptadores ELM327. Os códigos OBD-II usados são reais, mas todas as leituras e falhas são geradas pelo simulador interno.

## Estado atual

| Fase | Situação |
|---|---|
| 1. Fundação (Flask, SQLite, `/api/health`) | Concluída |
| 2. Layout, tema escuro e navegação | Concluída |
| 3. Cadastro de veículos e veículo ativo | Concluída |
| 4. Simulador de ECU (API) | Concluída |
| 5. Dashboard e Dados em tempo real | Concluída |
| 6. Catálogo DTC e Scanner | Concluída |
| 7. Motor de regras e tela Diagnósticos | Concluída |
| 8. Laboratório de falhas | Concluída |
| 9 e 10 | Pendentes (ver `DEVELOPMENT_PLAN.md`) |

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

## ECU simulada

O simulador (`app/services/simulator.py`) mantém um estado que evolui com o tempo: velocidade, borboleta, temperatura, tensão e correção de combustível. As leituras são calculadas a partir desse estado, então ficam coerentes entre si. Por exemplo, a rotação acompanha a velocidade e a marcha, e a carga cai na desaceleração (corte de combustível). **Todos os parâmetros são didáticos/ilustrativos**, não especificações de um veículo real, e ficam no dicionário `PARAMS`.

| Método | Endereço | Ação |
|---|---|---|
| GET | `/api/sensors/live` | Leitura atual de todos os sensores |
| POST | `/api/simulator/mode` | `{"mode": "idle" \| "accelerating" \| "decelerating"}` |
| GET | `/api/simulator/scenarios` | Modo atual e cenários (ativos ou não) |
| POST | `/api/simulator/scenarios/<id>/activate` | Ativa um cenário (409 se contradizer outro) |
| POST | `/api/simulator/scenarios/<id>/deactivate` | Desativa um cenário |
| POST | `/api/simulator/reset` | Volta ao normal: parado, sem cenários |

| Cenário (`id`) | O que acontece | DTC gerado |
|---|---|---|
| Superaquecimento (`overheating`) | Ventoinha não liga; temperatura sobe ~1 °C/s até ~125 °C | nenhum (condição observada) |
| Tensão baixa (`low_voltage`) | Tensão cai para ~11,6 V | nenhum (condição observada) |
| Sensor ECT desconectado (`ect_disconnected`) | Temperatura `null`/inválida; ECU liga a ventoinha por segurança | P0115 |
| Falha de combustão cil. 1 (`misfire_cyl1`) | Rotação oscila mais na marcha lenta | P0301 |
| Mistura pobre (`lean_mixture`) | Correções de combustível positivas (~+14% e ~+16%) | P0171 |
| Falha de velocidade (`vss_failure`) | Velocidade informada fica em 0 km/h mesmo em movimento | P0500 |

"Superaquecimento" e "Sensor ECT desconectado" não podem ficar ativos juntos: sem o sensor, o superaquecimento não poderia ser observado.

### Laboratório de falhas

A tela **Laboratório de falhas** é o painel da demonstração:
- um cartão por cenário, com descrição, o DTC que ele gera (com link para o catálogo) e o botão **Ativar/Desativar**;
- cenários em conflito ficam bloqueados, com a explicação no próprio cartão;
- o resumo no topo mostra os cenários ativos e o botão **Restaurar condições normais** (desativa todos e volta ao modo parado);
- o quadro "Efeito agora" mostra ao vivo os sensores que mais mudam: temperatura, tensão, rotação, velocidade, correção de combustível e ventoinha.

Os cenários afetam o Dashboard, os Dados em tempo real e a **próxima** varredura. Diagnósticos já salvos não mudam. A demonstração pode ser repetida quantas vezes quiser, sem reiniciar o servidor.

Roteiro sugerido para a apresentação:
1. Em **Veículos**, cadastre e ative um veículo fictício.
2. No **Dashboard**, mostre os indicadores normais.
3. No **Laboratório**, ative "Superaquecimento" e "Falha de combustão no cilindro 1".
4. Volte ao **Dashboard** e espere a temperatura subir (cerca de 20 a 30 s) até aparecer o alerta.
5. No **Scanner**, faça a varredura e mostre a diferença entre DTC, condição observada e hipótese.
6. Clique no código **P0301** para abrir o catálogo.
7. No **Laboratório**, clique em "Restaurar condições normais" e faça outra varredura limpa.

O estado do simulador fica na memória: ao reiniciar o servidor, ele volta ao normal. Os cadastros (banco) não são afetados. Há **um simulador por servidor**: todas as abas e telas abertas veem o mesmo estado.

### Limites de normal / atenção / crítico

O Dashboard e a tela Dados em tempo real classificam cada leitura com selo (ícone + texto) e cor. Os limites são **didáticos/ilustrativos** e ficam em `app/services/sensor_status.py`:

| Sensor | Atenção | Crítico |
|---|---|---|
| Temperatura (ECT) | ≥ 105 °C | ≥ 115 °C |
| Tensão do módulo | ≤ 13,0 V ou ≥ 14,8 V | ≤ 12,0 V ou ≥ 15,5 V |
| Rotação | ≥ 5500 rpm | ≥ 6500 rpm |
| Correções de combustível (curto e longo prazo) | ≤ −10% ou ≥ +10% | ≤ −20% ou ≥ +20% |

Sensor sem leitura (ex.: ECT desconectado) aparece como **"Sem leitura"**. Velocidade, carga, borboleta e MAF não têm limite.

### Telas

- **Dashboard**:
  - indicadores principais e gráficos de rotação e temperatura do último minuto;
  - alertas, estado da ECU simulada, veículo ativo e último diagnóstico.
- **Dados em tempo real**:
  - todos os sensores;
  - botões de modo de condução (marcha lenta, aceleração, desaceleração);
  - gráfico do parâmetro escolhido.

As duas telas consultam `/api/sensors/live` a cada 1 segundo, sem recarregar a página. O próximo pedido só sai depois que o anterior termina, nunca há dois ao mesmo tempo, e a atualização pausa quando a aba fica em segundo plano.

O Chart.js 4.4.1 (licença MIT) está em `app/static/vendor/`, dentro do projeto, para funcionar sem internet.

## Catálogo de códigos DTC

O catálogo começa com os 8 códigos da especificação (P0101, P0115, P0128, P0171, P0300, P0301, P0420 e P0500). Cada um traz descrição em português, sistema, explicação, possíveis causas, sintomas e verificações recomendadas.

O conteúdo fica em **`app/data/fault_codes.json`**, para ser revisado ou ampliado sem mexer no código. A cada inicialização ele é carregado no banco: códigos novos são inseridos e os existentes são atualizados, sem duplicar. Se o arquivo tiver um campo vazio ou mal formatado, o servidor não inicia e mostra qual código está com problema.

A busca aceita código (`P0301`, `p030`) ou palavras (`combustao`, `mistura pobre`) e ignora acentos e maiúsculas.

| Método | Endereço | Ação |
|---|---|---|
| GET | `/api/fault-codes?q=texto` | Busca (sem `q`, lista todos) |
| GET | `/api/fault-codes/<código>` | Detalhe (404 se não existir) |

## Scanner

A tela Scanner faz a varredura no veículo ativo. As etapas de progresso são uma animação na tela; o resultado vem do servidor, que:

1. confere se há veículo ativo (se não houver, responde 409 com explicação);
2. lê a ECU simulada e classifica cada leitura (normal, atenção, crítico);
3. busca no catálogo os DTCs gerados pelos cenários ativos;
4. salva o diagnóstico, os códigos e as leituras numa única transação.

O resultado separa três coisas:

1. **Códigos de falha armazenados (DTC)**: o que a ECU simulada registrou. Todo código vem com a ressalva de que não confirma sozinho a peça defeituosa.
2. **Condições observadas**: leituras fora dos limites didáticos (podem existir sem nenhum DTC, como no superaquecimento).
3. **Hipóteses**: geradas pelo motor de regras (abaixo), indicando o que investigar.

## Motor de regras

As regras ficam em `app/services/rules.py`. São funções Python explícitas, **sem inteligência artificial**. Cada resultado traz:
- título e nível (Informativo, Atenção ou Crítico);
- evidências observadas;
- hipóteses possíveis;
- verificações recomendadas;
- identificador da regra que disparou;
- aviso de orientação didática.

| Regra | Dispara quando | Nível |
|---|---|---|
| `R-ECT-ALTA` | ECT ≥ 105 °C | Atenção (Crítico a partir de 115 °C) |
| `R-VENTOINHA` | ECT ≥ 100 °C com ventoinha desligada | Atenção (Crítico a partir de 115 °C) |
| `R-ECT-SINAL` | Sem leitura válida de ECT (cita P0115 e a ventoinha de segurança, se presentes) | Atenção |
| `R-TENSAO-BAIXA` | Tensão ≤ 13,0 V com motor funcionando (≥ 400 rpm) | Atenção (Crítico a partir de 12,0 V) |
| `R-TENSAO-ALTA` | Tensão ≥ 14,8 V | Atenção (Crítico a partir de 15,5 V) |
| `R-COMBUSTAO` | DTC P0300 ou P0301 (se houver P0171 junto, sugere investigar a mistura primeiro) | Atenção |
| `R-MISTURA-POBRE` | DTC P0171 com correções positivas (LTFT ≥ 10% ou soma ≥ 20%); sem correções altas, vira Informativo | Atenção / Informativo |
| `R-CORRECAO-ALTA` | Correções positivas altas sem DTC | Atenção |
| `R-VELOCIDADE` | DTC P0500, ou velocidade 0 com rotação ≥ 1500 rpm e borboleta ≥ 10% | Atenção |
| `R-DTC-GERAL` | Qualquer outro DTC sem regra específica | Informativo |

Os limites são **didáticos/ilustrativos**. As faixas dos sensores vêm de `sensor_status.THRESHOLDS` (as mesmas do Dashboard). Os limites próprios das regras ficam em `rules.RULE_LIMITS`.

As regras rodam no momento da varredura e o resultado é salvo junto com o diagnóstico. Mudar uma regra depois **não altera** diagnósticos já salvos.

A tela **Diagnósticos** mostra o diagnóstico mais recente, ou um específico com `/diagnosticos?id=N` (o Dashboard usa esse link).

O diagnóstico guarda uma cópia de tudo o que foi lido. Mudar o simulador, os limites ou o catálogo depois **não altera** diagnósticos já salvos.

| Método | Endereço | Ação |
|---|---|---|
| POST | `/api/scanner/start` | Faz a varredura e salva (201) |
| GET | `/api/diagnostics/<id>` | Diagnóstico salvo: veículo, DTCs, condições e leituras |

## Erros

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
  static/vendor/  bibliotecas de terceiros (Chart.js)
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
- O "modo falha ativada" da especificação é representado pelos cenários de falha, que podem ser combinados com qualquer modo de condução.
- Cenários como superaquecimento e tensão baixa **não geram DTC**: eles servem para mostrar a diferença entre condição observada e código de falha armazenado.
- O simulador avança no tempo a cada consulta. Nos testes, um relógio falso e uma semente fixa (`seed`) deixam os resultados sempre iguais.
- O servidor escuta apenas em `127.0.0.1` (não fica acessível pela rede).
- A interface usa páginas separadas renderizadas pelo Flask (uma URL por tela), não uma aplicação de página única. Ao trocar de tela, os timers da anterior são encerrados automaticamente.
- Nenhum arquivo é carregado da internet (fontes do sistema, ícones SVG locais), porque a apresentação será em outro computador, possivelmente offline.

## Limitações

- Sem conexão real com veículo (fora do escopo da versão 1.0).
- Sem login: a aplicação é local e de uso único.
