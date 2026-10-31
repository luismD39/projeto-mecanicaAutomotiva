# AutoScan Pro | Instruções para Claude Code

## Papel
Atue como engenheiro de software responsável por projetar, implementar, testar e documentar o AutoScan Pro. Trabalhe diretamente neste repositório, inspecionando primeiro o estado atual dos arquivos antes de modificar qualquer coisa.

## Fonte de verdade
- Leia `PROJECT_SPEC.md` antes de implementar funcionalidades.
- Consulte `DATA_MODEL.md`, `API_SPEC.md`, `DEVELOPMENT_PLAN.md` e `TEST_PLAN.md` quando trabalhar nas respectivas áreas.
- Em caso de conflito, priorize esta ordem: requisitos explícitos do usuário na conversa atual, `PROJECT_SPEC.md`, demais documentos e, por último, decisões tomadas por você.
- Não descarte funcionalidades já implementadas sem explicar o motivo.

## Objetivo do produto
Criar um aplicativo web local, em português do Brasil, chamado AutoScan Pro. É um simulador didático de diagnóstico automotivo. A primeira versão NÃO se conecta a um veículo real: todos os dados de ECU/sensores são simulados. Os códigos OBD-II utilizados devem ser reais e suas descrições tecnicamente cuidadosas.

## Stack preferencial
- Backend: Python 3.11+ e Flask.
- Persistência: SQLite.
- Frontend: HTML5, CSS3 e JavaScript moderno sem framework obrigatório.
- Gráficos: Chart.js.
- PDF: ReportLab.
- Testes: pytest.
- Dependências e comandos devem ser documentados.

Não adicione frameworks ou dependências grandes sem justificar o benefício. Prefira soluções simples, legíveis e fáceis de manter por um estudante do Ensino Médio/SENAI.

## Regras de engenharia
1. Comece inspecionando o repositório e identificando o que já existe.
2. Antes de cada etapa, apresente um plano curto e implemente em incrementos pequenos.
3. Não crie somente telas estáticas: botões, formulários, filtros e ações visíveis devem funcionar.
4. Valide entradas no backend, mesmo quando também houver validação no frontend.
5. Use consultas parametrizadas no SQLite.
6. Não coloque regras de negócio dentro das rotas HTTP; mantenha-as em `services/`.
7. Trate erros com respostas consistentes e mensagens úteis em português.
8. Não use dados pessoais reais. Inclua apenas veículos e cenários fictícios de demonstração.
9. Não invente precisão técnica: limites de sensores devem ser configuráveis e identificados como didáticos/ilustrativos quando não forem especificações de um veículo específico.
10. O sistema deve diferenciar claramente: código de falha armazenado, condição observada e hipótese diagnóstica. Um DTC não confirma sozinho a peça defeituosa.
11. Não implemente “inteligência artificial” fictícia. O diagnóstico inicial será baseado em regras explícitas e explicáveis.
12. Não alegue comunicação OBD-II real na versão simulada.
13. Gere e mantenha `README.md`, instruções de instalação e arquivo de dependências atualizados.
14. Não deixe TODOs em funcionalidades declaradas como concluídas.
15. Execute testes relevantes após cada etapa e corrija falhas antes de prosseguir.

## Experiência e interface
- Toda a interface em português do Brasil.
- Visual de software profissional de diagnóstico automotivo.
- Tema escuro, fundo próximo de #111827, painéis #1F2937, azul #0EA5E9, verde #22C55E.
- Cores de estado consistentes: normal, atenção e crítico. Não dependa somente da cor: inclua texto/ícones.
- Layout responsivo para desktop e telas menores.
- Navegação lateral persistente e estados vazios/carregando/erro bem tratados.
- Acessibilidade básica: labels, foco visível, contraste razoável e botões com nomes claros.

## Fluxo de trabalho
- Trabalhe por etapas na ordem de `DEVELOPMENT_PLAN.md`.
- Ao terminar uma etapa, informe arquivos criados/alterados, funcionalidades entregues, testes executados e limitações restantes.
- Não avance para uma integração com hardware sem autorização explícita.
- Se uma decisão importante estiver ambígua, faça uma pergunta objetiva. Caso contrário, escolha a solução mais simples e registre a decisão.

## Critérios de conclusão
O projeto só pode ser considerado concluído quando os critérios de aceitação de `PROJECT_SPEC.md` e `TEST_PLAN.md` forem atendidos, os testes passarem e o README permitir que outra pessoa instale e execute o sistema do zero.
