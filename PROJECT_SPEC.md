# AutoScan Pro | Especificação do Projeto

**Versão do documento:** 1.0  
**Idioma do produto:** Português do Brasil  
**Contexto:** projeto acadêmico para apresentação no SENAI  
**Tipo:** aplicação web local, com simulação didática de diagnóstico automotivo

## 1. Resumo executivo

O AutoScan Pro é um software didático que simula o fluxo de trabalho de um scanner automotivo. O usuário cadastra ou seleciona um veículo fictício, inicia uma varredura simulada, acompanha parâmetros do motor, provoca falhas em um laboratório de cenários, consulta códigos OBD-II, recebe análises baseadas em regras e gera relatórios PDF com histórico.

O projeto deve parecer um produto comercial bem acabado, mas manter transparência técnica: na primeira versão, não existe conexão física com ECU, adaptador ELM327 ou veículo. Leituras e falhas são geradas pelo simulador interno.

## 2. Objetivos

- Demonstrar a relação entre programação, eletrônica e mecânica automotiva.
- Apresentar dados simulados de sensores em um dashboard dinâmico.
- Explicar códigos de diagnóstico OBD-II reais.
- Demonstrar como regras de diagnóstico podem relacionar códigos e parâmetros.
- Armazenar veículos, varreduras, falhas e leituras.
- Gerar relatórios técnicos em PDF.
- Fornecer uma demonstração interativa confiável para uma apresentação escolar.

## 3. Público e cenário de uso

Usuário principal: estudante/apresentador e professor avaliador. O sistema deve ser fácil de demonstrar em um computador, sem internet obrigatória após a instalação das dependências. Não exigir login na primeira versão.

## 4. Escopo da versão 1.0

### Incluído
1. Dashboard.
2. Cadastro, edição, seleção e exclusão de veículos.
3. Simulador de ECU e parâmetros de sensores.
4. Scanner OBD-II simulado.
5. Catálogo pesquisável de códigos DTC.
6. Diagnóstico baseado em regras explícitas.
7. Laboratório para ativar/desativar cenários de falha.
8. Histórico de diagnósticos.
9. Relatório PDF.
10. Dados fictícios de demonstração.
11. Testes automatizados e documentação.

### Fora do escopo da versão 1.0
- Comunicação real com veículos, ECU, CAN, ISO 9141, KWP2000 ou J2534.
- Conexão Bluetooth/USB com ELM327.
- Programação ou regravação de ECU.
- Apagar falhas reais de um veículo.
- Recomendações de reparo definitivas ou substituição automática de peças.
- Inteligência artificial generativa.
- Aplicativo móvel nativo, autenticação multiusuário ou hospedagem pública.

Esses itens podem ser considerados em versões futuras, sem comprometer a entrega acadêmica.

## 5. Módulos funcionais

### 5.1 Dashboard
Exibir:
- veículo ativo (marca, modelo, ano, motor e quilometragem);
- estado da conexão simulada com a ECU;
- quantidade de DTCs ativos/armazenados no último diagnóstico;
- RPM;
- temperatura do líquido de arrefecimento (ECT);
- velocidade do veículo (VSS);
- carga calculada do motor;
- posição da borboleta (TPS);
- tensão do módulo;
- gráfico de evolução de pelo menos RPM e temperatura;
- resumo do último diagnóstico;
- alertas e acesso rápido ao scanner/laboratório.

Os indicadores devem atualizar sem recarregar a página. Usar polling moderado (por exemplo, 1 segundo) ou outra abordagem simples. Evitar criar múltiplos timers ao navegar entre telas.

### 5.2 Gerenciamento de veículos
Campos:
- fabricante/marca (obrigatório);
- modelo (obrigatório);
- ano (obrigatório, validado);
- motorização (opcional);
- combustível (gasolina, etanol, flex, diesel, GNV, híbrido, elétrico ou outro);
- quilometragem (não negativa);
- identificador opcional (não solicitar VIN real; se houver campo, deixar claro que dados fictícios devem ser usados).

Ações: criar, listar, visualizar, editar, selecionar como ativo e excluir com confirmação. Não permitir exclusão silenciosa. O histórico relacionado deve ser preservado ou a exclusão deve ser bloqueada/explicada; preferir exclusão lógica ou bloqueio se houver diagnósticos associados.

### 5.3 Simulador de ECU
Criar serviço de simulação determinístico quando solicitado por testes e configurável para demonstração. Deve gerar leituras coerentes entre si, por exemplo:
- RPM;
- ECT (temperatura do líquido de arrefecimento);
- VSS (velocidade);
- carga calculada;
- TPS;
- MAF ou MAP (não é necessário simular ambos inicialmente);
- tensão do módulo;
- estado da ventoinha;
- correções de combustível, se incluídas.

A simulação deve ter modos:
- normal/ocioso;
- aceleração;
- desaceleração;
- falha ativada.

As leituras devem conter valor, unidade, timestamp e estado/validade. Não apresentar dados aleatórios sem coerência física básica. Separar a geração de dados da API e da interface.

### 5.4 Scanner OBD-II simulado
Fluxo:
1. verificar veículo ativo;
2. iniciar sessão de varredura;
3. exibir progresso visual por etapas;
4. obter snapshot de sensores e falhas simuladas;
5. executar regras de análise;
6. persistir diagnóstico, leituras e códigos encontrados;
7. exibir resumo e detalhes.

A animação de progresso pode ser controlada no frontend, mas o resultado deve vir do backend. Evitar declarar que módulos reais foram acessados. Usar rótulos como “ECU simulada”, “varredura didática” e “dados simulados”.

### 5.5 Catálogo de códigos DTC
Implementar pesquisa por código e texto. Cada registro deve conter:
- código;
- descrição curta em português;
- sistema/categoria;
- explicação;
- possíveis causas (lista);
- sintomas comuns (lista);
- verificações recomendadas (lista);
- observação de que o código direciona a investigação, mas não confirma uma peça defeituosa.

Começar com estes códigos (revisar descrição técnica antes de inserir):
- P0101: faixa/desempenho do circuito do sensor/medidor de fluxo de ar de massa (MAF).
- P0115: mau funcionamento do circuito do sensor de temperatura do líquido de arrefecimento do motor (ECT).
- P0128: temperatura do líquido de arrefecimento abaixo da temperatura de regulação do termostato.
- P0171: sistema muito pobre, banco 1.
- P0300: falhas aleatórias/múltiplas de combustão detectadas.
- P0301: falha de combustão detectada no cilindro 1.
- P0420: eficiência do sistema catalisador abaixo do limite, banco 1.
- P0500: mau funcionamento do sensor de velocidade do veículo.

Os códigos são padronizados, mas a interpretação, causas prováveis e procedimentos podem variar conforme veículo, motor e fabricante.

### 5.6 Diagnóstico baseado em regras
Implementar regras transparentes em Python, não um modelo de IA. Cada resultado deve conter:
- título;
- nível (informativo, atenção ou crítico);
- evidências observadas;
- hipóteses possíveis;
- verificações recomendadas;
- regra que disparou (identificador interno);
- aviso de que é uma orientação didática.

Exemplos de regras didáticas:
- ECT acima de um limite configurável: temperatura elevada.
- ECT muito alta e ventoinha simulada desligada: possível anomalia no comando/acionamento da ventoinha.
- tensão de alimentação abaixo do limite didático: investigar bateria, conexões e sistema de carga.
- DTC P0301: investigar ignição, injeção e condição mecânica do cilindro, sem concluir que a vela ou bobina está defeituosa.
- P0171 junto de correção de combustível positiva: evidência compatível com mistura pobre; investigar entrada falsa de ar, alimentação e sensores.

Os limites devem estar em configuração centralizada e ser identificados como didáticos, não universais. Permitir ajustar limites no código/configuração, não necessariamente em tela na primeira versão.

### 5.7 Laboratório de falhas
Tela de demonstração que permite ativar e desativar cenários:
- superaquecimento;
- tensão baixa;
- sensor ECT desconectado/valor inválido;
- falha de combustão no cilindro 1;
- mistura pobre;
- falha de velocidade.

Requisitos:
- indicar claramente quais cenários estão ativos;
- permitir ativar um ou mais cenários quando isso não gerar contradição;
- botão “Restaurar condições normais”;
- refletir os cenários no simulador de ECU, dashboard e próxima varredura;
- não modificar dados históricos já salvos;
- permitir repetir a demonstração.

### 5.8 Histórico
Listar diagnósticos com:
- data/hora;
- veículo;
- quantidade de DTCs;
- estado/resumo;
- acesso ao detalhe.

Filtros por veículo e intervalo de datas. Permitir visualizar leituras e falhas associadas. Preservar snapshots históricos mesmo que o simulador mude depois.

**Diagnósticos x Histórico (itens separados na sidebar):**
- **Diagnósticos** abre o detalhe do diagnóstico mais recente (ou do selecionado no Histórico): DTCs armazenados, condições observadas, hipóteses, evidências, recomendações e botão de PDF. Sem diagnóstico salvo, mostra estado vazio com acesso ao Scanner.
- **Histórico** é a lista com filtros; cada linha abre a tela Diagnósticos daquele registro.

### 5.9 Relatórios PDF
Gerar PDF em português contendo:
- título AutoScan Pro;
- identificação do veículo;
- data/hora;
- aviso destacado “SIMULAÇÃO DIDÁTICA: não representa leitura de um veículo real”;
- resumo do resultado;
- códigos e descrições;
- evidências e recomendações;
- tabela de parâmetros e unidades;
- identificador do diagnóstico.

O relatório deve ser legível, com paginação e cabeçalho/rodapé quando necessário. O PDF deve ser gerado no backend e baixado pelo navegador.

## 6. Requisitos não funcionais

- Executar localmente em Windows 10/11 e, se possível, Linux.
- Interface em pt-BR.
- Não exigir internet durante o uso normal.
- Código organizado, tipado quando útil e comentado em pontos não óbvios.
- Validação no frontend e backend.
- Tratamento de erros e logs.
- Consultas SQL parametrizadas.
- Não armazenar credenciais ou dados sensíveis.
- Testes automatizados para serviços e rotas importantes.
- Interface responsiva, preferencialmente desktop-first.
- Não depender de imagens externas para que o sistema funcione. Usar ícones SVG locais ou CSS quando possível.

## 7. Design de interface

Direção visual:
- fundo: #111827;
- superfícies/painéis: #1F2937;
- azul de ação: #0EA5E9;
- verde normal: #22C55E;
- âmbar atenção: #F59E0B;
- vermelho crítico: #EF4444;
- texto principal claro e texto secundário cinza.

Layout:
- sidebar à esquerda com logotipo AutoScan Pro;
- itens: Dashboard, Veículos, Scanner, Dados em tempo real, Diagnósticos, Laboratório de falhas, Histórico e Códigos DTC;
- barra superior com veículo ativo e status da ECU simulada;
- conteúdo em cartões;
- gráficos com Chart.js;
- badges e ícones acompanhados por texto, nunca apenas cor.

## 8. Critérios de aceitação

A versão 1.0 estará pronta quando:
1. A aplicação iniciar seguindo o README.
2. O usuário conseguir cadastrar, editar e selecionar um veículo.
3. O dashboard mostrar dados simulados e atualizar sem recarregar.
4. Os controles de aceleração e cenários alterarem os dados de forma coerente.
5. O scanner executar uma varredura simulada e persistir o resultado.
6. O catálogo pesquisar os códigos definidos.
7. As regras gerarem resultados explicáveis com evidências e recomendações.
8. O laboratório ativar/desativar cenários e restaurar estado normal.
9. O histórico listar e abrir diagnósticos anteriores.
10. O PDF ser gerado e conter o aviso de simulação.
11. Os principais fluxos possuírem testes automatizados.
12. Não haver botões principais sem ação.
13. A documentação explicar instalação, execução, testes e limitações.
14. A interface deixar inequívoco que não existe conexão real com veículo na versão 1.0.
