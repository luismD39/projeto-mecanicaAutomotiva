# AutoScan Pro | Plano de Testes

Usar pytest para backend e testes de integração. Para o frontend, realizar verificação manual estruturada e, se viável sem complexidade excessiva, adicionar testes automatizados.

## Backend e banco
- Aplicação inicia em modo de teste.
- Banco é criado corretamente.
- Seeds podem rodar repetidamente sem duplicar códigos.
- Chaves estrangeiras estão habilitadas.
- Entradas inválidas são rejeitadas.
- Veículo cadastrado permanece após reinício.
- Apenas um veículo pode estar ativo.

## Veículos
- Criar veículo válido.
- Rejeitar marca/modelo vazios.
- Rejeitar ano fora da faixa definida.
- Rejeitar quilometragem negativa.
- Editar veículo existente.
- Consultar ID inexistente retorna 404.
- Política de exclusão com histórico é respeitada.

## Simulador
- Modo normal retorna leituras válidas.
- Aceleração aumenta RPM e TPS de modo coerente.
- Desaceleração reduz RPM/TPS.
- Superaquecimento aumenta ECT.
- Tensão baixa reduz tensão.
- Sensor desconectado retorna validade inválida/null, não um número normal.
- Reset desativa cenários e restaura estado.
- Testes podem fixar valores/relógio para evitar flakiness.

## Scanner e diagnóstico
- Scanner exige veículo ativo.
- Varredura gera ID e persiste snapshot.
- Falhas ativadas aparecem no resultado esperado.
- Diagnóstico sem falhas também é persistido.
- DTC não é tratado como confirmação de componente defeituoso.
- Resultados históricos não mudam quando o simulador muda.

## Catálogo
- Busca por código exato.
- Busca por descrição.
- Código inexistente retorna 404.
- Descrições e recomendações incluem ressalva de contexto veicular.

## Relatórios
- PDF é gerado para diagnóstico existente.
- Diagnóstico inexistente retorna 404.
- PDF contém veículo, data, falhas e leituras.
- PDF contém aviso explícito de simulação didática.

## Frontend: roteiro manual
1. Abrir dashboard.
2. Cadastrar veículo.
3. Ativar veículo.
4. Observar indicadores atualizando.
5. Abrir Live Data.
6. Alterar modo para aceleração.
7. Abrir laboratório e ativar superaquecimento.
8. Verificar alerta no dashboard.
9. Iniciar scanner.
10. Abrir detalhes de DTC.
11. Restaurar condições normais.
12. Consultar histórico.
13. Baixar PDF.
14. Atualizar a página e confirmar persistência.

## Critério de liberação
Não declarar uma funcionalidade concluída se o botão correspondente não funcionar, se os dados não persistirem quando deveriam ou se não houver tratamento para erro básico.
