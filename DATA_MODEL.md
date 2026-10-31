# AutoScan Pro | Modelo de Dados

Banco: SQLite. Use chaves primárias inteiras, chaves estrangeiras habilitadas (`PRAGMA foreign_keys = ON`), datas em ISO 8601 e consultas parametrizadas.

## Tabelas propostas

### vehicles
- id INTEGER PRIMARY KEY
- make TEXT NOT NULL
- model TEXT NOT NULL
- year INTEGER NOT NULL
- engine TEXT
- fuel_type TEXT NOT NULL
- mileage_km REAL NOT NULL DEFAULT 0
- created_at TEXT NOT NULL
- updated_at TEXT NOT NULL
- is_active INTEGER NOT NULL DEFAULT 0

Regra: idealmente apenas um veículo ativo por vez. Garantir isso na camada de serviço/transação.

### fault_codes
- id INTEGER PRIMARY KEY
- code TEXT NOT NULL UNIQUE
- description TEXT NOT NULL
- system TEXT NOT NULL
- explanation TEXT NOT NULL
- causes_json TEXT NOT NULL
- symptoms_json TEXT NOT NULL
- checks_json TEXT NOT NULL
- created_at TEXT NOT NULL

As listas podem ser armazenadas como JSON válido em TEXT, com validação na aplicação.

### diagnostics
- id INTEGER PRIMARY KEY
- vehicle_id INTEGER NOT NULL REFERENCES vehicles(id)
- started_at TEXT NOT NULL
- completed_at TEXT NOT NULL
- source TEXT NOT NULL DEFAULT 'simulation'
- status TEXT NOT NULL
- summary TEXT NOT NULL
- scenario_snapshot_json TEXT NOT NULL
- sensor_snapshot_json TEXT NOT NULL
- findings_json TEXT NOT NULL

O campo `findings_json` guarda o resultado do motor de regras no momento da varredura, para que o histórico não mude se as regras ou limites forem alterados depois.

O campo `source` deve permanecer `simulation` na versão 1.0.

### diagnostic_faults
- id INTEGER PRIMARY KEY
- diagnostic_id INTEGER NOT NULL REFERENCES diagnostics(id) ON DELETE CASCADE
- fault_code_id INTEGER NOT NULL REFERENCES fault_codes(id)
- status TEXT NOT NULL DEFAULT 'stored'
- evidence TEXT
- UNIQUE(diagnostic_id, fault_code_id)

### sensor_readings
- id INTEGER PRIMARY KEY
- diagnostic_id INTEGER REFERENCES diagnostics(id) ON DELETE CASCADE
- sensor_key TEXT NOT NULL
- display_name TEXT NOT NULL
- value REAL
- unit TEXT NOT NULL
- recorded_at TEXT NOT NULL
- validity TEXT NOT NULL DEFAULT 'valid'

Para o histórico, persistir snapshots associados ao diagnóstico. Leituras transitórias do dashboard não precisam ser todas gravadas; evitar crescimento desnecessário do banco.

## Relacionamentos
- Um veículo possui muitos diagnósticos.
- Um diagnóstico possui muitas falhas relacionadas.
- Um código DTC pode aparecer em muitos diagnósticos.
- Um diagnóstico possui várias leituras de sensores.

## Integridade
- Não excluir um veículo com histórico sem uma política explícita. Preferir impedir exclusão e explicar ao usuário ou implementar exclusão lógica.
- Excluir diagnóstico deve remover suas relações e leituras associadas.
- Inserir códigos iniciais de forma idempotente (seed pode ser executado várias vezes sem duplicar).
- Não salvar objetos Python serializados com pickle. Usar JSON.
