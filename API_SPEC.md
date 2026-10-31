# AutoScan Pro | Contrato inicial da API REST

Prefixo: `/api`. Respostas JSON em UTF-8. Usar códigos HTTP apropriados e mensagens de erro consistentes.

## Formato de erro sugerido
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Verifique os campos informados."
  }
}
```

## Veículos
- `GET /api/vehicles`: lista veículos.
- `POST /api/vehicles`: cria veículo.
- `GET /api/vehicles/<id>`: detalhes.
- `PUT /api/vehicles/<id>`: atualiza.
- `DELETE /api/vehicles/<id>`: exclui, se permitido pela política de histórico.
- `POST /api/vehicles/<id>/activate`: define veículo ativo.

Exemplo de criação:
```json
{
  "make": "Volkswagen",
  "model": "Golf",
  "year": 2018,
  "engine": "1.4 TSI",
  "fuel_type": "gasolina",
  "mileage_km": 78500
}
```

## ECU simulada e sensores
- `GET /api/sensors/live`: snapshot atual.
- `POST /api/simulator/mode`: define modo `idle`, `accelerating` ou `decelerating`.
- `GET /api/simulator/scenarios`: lista cenários ativos.
- `POST /api/simulator/scenarios/<scenario_id>/activate`: ativa cenário.
- `POST /api/simulator/scenarios/<scenario_id>/deactivate`: desativa cenário.
- `POST /api/simulator/reset`: restaura estado normal.

Exemplo de snapshot:
```json
{
  "source": "simulation",
  "timestamp": "2026-01-01T12:00:00Z",
  "sensors": {
    "rpm": {"value": 2450, "unit": "rpm", "validity": "valid"},
    "coolant_temperature": {"value": 92, "unit": "°C", "validity": "valid"},
    "vehicle_speed": {"value": 65, "unit": "km/h", "validity": "valid"},
    "engine_load": {"value": 48, "unit": "%", "validity": "valid"},
    "throttle_position": {"value": 32, "unit": "%", "validity": "valid"},
    "battery_voltage": {"value": 13.8, "unit": "V", "validity": "valid"}
  },
  "fan": {"on": false}
}
```
Valores acima são ilustrativos.

## Scanner e diagnósticos
- `POST /api/scanner/start`: inicia uma varredura para o veículo ativo.
- `GET /api/diagnostics`: lista diagnósticos; aceitar filtros como `vehicle_id`, `from`, `to`.
- `GET /api/diagnostics/<id>`: detalhe, leituras, DTCs e análises.

A varredura deve persistir um snapshot imutável dos dados usados no resultado. Retornar `diagnostic_id`, `status`, `summary`, `faults` e `findings`.

## Catálogo DTC
- `GET /api/fault-codes`: lista/pesquisa com `q`.
- `GET /api/fault-codes/<code>`: detalhes do código.

## PDF
- `GET /api/reports/<diagnostic_id>/pdf`: retorna PDF para download; validar se diagnóstico existe.

## Regras gerais
- Validar todos os parâmetros.
- Não confiar em `vehicle_id` enviado sem confirmar existência.
- Retornar 404 para recursos inexistentes.
- Retornar 400/422 para entrada inválida.
- Não expor stack traces ao navegador.
- Não alegar que os endpoints simulados leem uma ECU real.
