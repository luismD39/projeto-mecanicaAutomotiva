# AutoScan Pro | Plano de Desenvolvimento

Desenvolver em etapas pequenas, mantendo o sistema executável ao final de cada etapa.

## Fase 0 | Inspeção e planejamento
- Inspecionar repositório.
- Confirmar Python disponível e versão.
- Criar plano de implementação detalhado.
- Não sobrescrever arquivos existentes sem verificar seu conteúdo.

**Entrega:** estrutura inicial e decisões registradas.

## Fase 1 | Fundação
- Criar ambiente virtual.
- Configurar Flask.
- Criar aplicação e rota de saúde `/api/health`.
- Configurar SQLite e inicialização do banco, já criando todas as tabelas de `DATA_MODEL.md` (sem dados).
- Criar `requirements.txt` e README inicial.

**Aceitação:** servidor inicia localmente e endpoint de saúde responde.

## Fase 2 | Design system e navegação
- Criar layout principal.
- Sidebar e cabeçalho.
- Tema escuro e componentes reutilizáveis.
- Estados de carregamento, vazio e erro.
- Navegação funcional entre páginas.

**Aceitação:** todas as páginas principais abrem e não existem links quebrados.

## Fase 3 | Veículos e persistência
- Usar a tabela `vehicles` criada na Fase 1 (o seed de códigos DTC fica na Fase 6).
- Implementar CRUD de veículos.
- Implementar veículo ativo.
- Validar formulários no frontend e backend.

**Aceitação:** cadastro persiste após reiniciar a aplicação.

## Fase 4 | Simulador de ECU
- Implementar serviço com estado de simulação.
- Criar modos normal, aceleração e desaceleração.
- Criar snapshot de sensores com unidades e validade.
- Criar cenários de falha.
- Implementar reset.
- Criar endpoints e testes.

**Aceitação:** ativar cenário altera o snapshot de modo previsível e reset restaura valores normais.

## Fase 5 | Dashboard e Live Data
- Conectar dashboard à API.
- Atualizar cartões periodicamente.
- Implementar gráficos Chart.js.
- Controlar ciclo de vida do polling.
- Mostrar origem simulada dos dados.

**Aceitação:** dados e gráficos atualizam sem recarregar a página e sem duplicar requisições.

## Fase 6 | Catálogo DTC e scanner
- Inserir códigos iniciais.
- Implementar busca e detalhe.
- Implementar fluxo de varredura.
- Persistir diagnóstico e snapshots.
- Exibir resultados e evidências.

**Aceitação:** varredura cria registro consultável no histórico.

## Fase 7 | Motor de regras
- Implementar regras em serviço separado.
- Cada regra retorna evidências, nível e recomendações.
- Diferenciar código armazenado de hipótese.
- Testar limites e combinações.

**Aceitação:** testes cobrem condições normais, alertas e casos críticos.

## Fase 8 | Laboratório de falhas
- Criar tela para ativar/desativar cenários.
- Exibir cenários ativos.
- Implementar restauração.
- Garantir que cenários influenciem a próxima varredura.

**Aceitação:** demonstração pode ser repetida sem reiniciar o servidor.

## Fase 9 | Histórico e PDF
- Listar e filtrar diagnósticos.
- Criar tela de detalhes.
- Gerar PDF com aviso didático.
- Testar PDF e persistência.

**Aceitação:** PDF baixado contém dados do diagnóstico selecionado e aviso de simulação.

## Fase 10 | Qualidade e entrega
- Executar testes.
- Corrigir erros.
- Verificar acessibilidade básica e responsividade.
- Revisar segurança e validação.
- Atualizar README e capturas de tela se possível.
- Preparar roteiro de demonstração.
- Preparar pacote portátil: a apresentação será em **outro computador** (Windows), possivelmente sem internet e sem permissão de administrador. Incluir dependências offline e um script de inicialização com duplo clique.

**Aceitação:** instalação limpa documentada, todos os fluxos prioritários funcionando e o pacote portátil testado numa pasta diferente da de desenvolvimento.

## Estratégia de execução com Claude Code
1. Não pedir para implementar tudo em uma única alteração gigantesca.
2. Concluir uma fase, testar e revisar.
3. Manter um checklist de tarefas atualizado.
4. Ao final de cada fase, resumir arquivos alterados, testes e pendências.
5. Só começar a fase seguinte quando a anterior estiver funcional, salvo dependência justificada.
