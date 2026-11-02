# INF0336 - Seminário

Trabalho consolidado até a **semana 2**. As instruções de instalação, uso e reprodução estão no
[guia técnico](docs/GUIA_TECNICO.md).

## Título do Seminário

Sandbox e previsão de recursos com aprendizado de máquina

## Equipe

| Matrícula | Nome completo |
|---|---|
| 202401832 | Wender Viana Faria Santos |
| 202405859 | William Félix Ferreira Alves da Silva |
| 202405860 | Wryel Teodoro de Morais |
| 202401799 | Lourenço Tabosa Paniago |

## Apresentações

1. [Apresentação da segunda semana](docs/apresentacoes/semana-2/apresentacao-semana-2.pptx) e [versão PDF](docs/apresentacoes/semana-2/apresentacao-semana-2.pdf).

## Resumo

Este trabalho avalia recomendações de recursos para scripts Python executados em uma sandbox Linux. Comparamos um perfil fixo, regras heurísticas e uma árvore de decisão treinada com medições reais. Uma política independente restringe acessos e aplica os tetos do operador. No piloto da semana 2, os três métodos concluíram corretamente as oito tarefas de teste. A heurística recomendou o menor limite médio de memória virtual, enquanto os tempos e o consumo de RAM foram próximos. O fluxo está funcional, mas ainda não demonstra vantagem do ML.

## Introdução

### Motivação

Uma sandbox restringe o ambiente de execução, mas o operador ainda precisa escolher limites de recursos. Valores altos permitem consumo desnecessário; valores baixos podem interromper tarefas legítimas. Investigamos se o aprendizado de máquina ajuda a recomendar limites menores, preservando a correção das tarefas.

### Revisão bibliográfica

O menor privilégio de Saltzer e Schroeder (1975) orienta a separação entre recomendação e autorização. Kwon et al. (2013), com o Mantis, motivam o uso de características dos programas para prever desempenho, sem garantir que seus resultados se transfiram para este estudo.

Pedregosa et al. (2011) e a documentação do scikit-learn fundamentam a implementação da árvore e os cuidados de avaliação. A documentação do Bubblewrap e o manual getrlimit(2) descrevem o isolamento e os limites Linux utilizados.

### Objetivos

- Executar scripts sob permissões e tetos definidos pelo operador.
- Treinar um modelo para prever memória virtual e tempo decorrido.
- Comparar suas recomendações e o consumo observado com os métodos fixo e heurístico.

## Metodologia

### Conjunto de dados e análise inicial

Uma **tarefa** é um programa com sua entrada definida. Criamos 32 tarefas autorais, com oito variações de tamanho em cada um dos quatro tipos abaixo. Cada tarefa foi executada duas vezes, totalizando **64 medições de referência**.

| Tipo de tarefa | Atividade | Treino | Teste |
|---|---|---:|---:|
| Alocação | Criar blocos de memória. | 6 | 2 |
| Cálculo | Realizar operações numéricas. | 6 | 2 |
| Leitura | Ler arquivos de texto. | 6 | 2 |
| Escrita | Gravar arquivos. | 6 | 2 |
| **Total** | | **24** | **8** |

A coleta foi local, na sandbox, com limites de referência de 256 MiB de memória virtual e 5 s de tempo decorrido. O alvo de cada tarefa é o maior valor medido de cada recurso nas duas execuções. Os quatro tipos aparecem tanto no treino quanto no teste. Os códigos, entradas e medições estão no [conjunto de dados](data/initial-measurements.json).

### Modelos e infraestrutura

O protótipo utiliza Python 3.11 ou superior, Linux, Bubblewrap e scikit-learn.

| Método | Como recomenda recursos |
|---|---|
| Fixo | Perfil constante de 128 MiB de memória virtual e 2 s. |
| Heurística | Regras sobre o código e o tamanho da entrada. |
| ML | Árvore de decisão de regressão treinada com o consumo medido. |

A árvore (`DecisionTreeRegressor`) recebe 11 características, como tamanhos do código e da entrada e quantidade de laços e chamadas. Ela aprende condições que agrupam exemplos para estimar pico de memória virtual e tempo decorrido. A profundidade máxima é 4, e somente as tarefas de treino ajustam o modelo.

As previsões recebem margens e passam pela política de autorização, que aplica os tetos do operador. As permissões de leitura e escrita são identificadas por análise estática, sem aprendizagem. O treinamento está explicado em [ML inicial](docs/ML_INICIAL.md); os comandos e controles do executor estão no [guia técnico](docs/GUIA_TECNICO.md).

### Métricas e fluxograma

Com o modelo fixo, cada tarefa de teste foi reexecutada uma vez por método: **24 reexecuções de avaliação**. Uma execução correta termina sem erro ou timeout e produz as saídas esperadas no terminal e nos arquivos.

Comparamos correção, limite configurado de memória virtual, tempo decorrido, tempo de CPU e pico de RAM. Também calculamos o erro das previsões e sua cobertura das medições de referência.

![Coleta, treinamento, recomendação, autorização e execução](docs/figures/fluxograma.png)

*Figura 1 — Fluxo do experimento. Fonte: elaboração da equipe.*

### Planejamento para as próximas semanas

| Semana | Atividade e entrega prevista |
|---|---|
| 3 | Ampliar os dados e separar tipos de tarefa entre treino, validação e teste. |
| 4 | Calibrar margens e comparar modelos com fixo e heurística; selecionar a configuração na validação. |
| 5 | Avaliar tipos de tarefa reservados e consolidar resultados e instruções de reprodução. |

## Resultados

### Funcionamento do protótipo

O executor, a coleta, o treinamento e a avaliação estão integrados. Na validação local registrada para esta entrega, passaram os 35 testes da suíte, incluindo nove ensaios funcionais de contenção. A instalação também foi verificada com execução usando o modelo, argumentos, exportação de arquivo e relatório JSON.

### Comparação dos métodos

| Método | Tarefas corretas | Limite médio de memória virtual (MiB) |
|---|---:|---:|
| Fixo | 8/8 | 128 |
| Heurística | 8/8 | 35 |
| ML | 8/8 | 42,25 |

*Tabela 1 — Resultados nas oito tarefas de teste. Fonte: [relatório de avaliação](reports/initial-replay.json).*

A heurística recomendou o menor limite médio. Antes das margens, o erro absoluto médio do ML foi de aproximadamente 0,94 MiB e 0,0094 s. Os limites dos três métodos cobriram as medições de referência.

### Tempos e consumo medidos

| Método | Tempo decorrido (ms) | Tempo de CPU (ms) | Pico médio de RAM (MiB) |
|---|---:|---:|---:|
| Fixo | 49,73 | 48,27 | 12,24 |
| Heurística | 51,16 | 49,49 | 12,28 |
| ML | 49,18 | 47,60 | 12,35 |

*Tabela 2 — Médias das oito tarefas de cada método. Na memória, calculamos a média dos picos por execução. Fonte: [relatório de avaliação](reports/initial-replay.json).*

O **limite de memória virtual** é um teto configurado, enquanto o **pico de RAM** é o maior uso de memória residente observado por processo. O **tempo decorrido** inclui esperas; o **tempo de CPU** representa o processamento consumido. O tempo medido não inclui o planejamento nem a preparação completa da sandbox. Os detalhes estão no [guia de métricas](docs/GUIA_TECNICO.md#leitura-das-métricas).

## Discussão

Os limites recomendados foram diferentes, mas os tempos e picos de RAM ficaram próximos. Portanto, limites menores não demonstraram menor consumo observado. Como houve apenas uma reexecução por método e tarefa, pequenas diferenças não sustentam uma conclusão de ganho de desempenho.

O conjunto é pequeno, compartilha tipos de tarefa entre treino e teste e não possui validação separada. A máquina e sua carga também influenciam as medições. A avaliação ampliada precisa verificar essas condições antes de justificar o uso do ML em outros cenários.

Os controles e as medições são por processo, sem representar RAM agregada da sandbox. Os ensaios locais verificam casos controlados e não certificam segurança para execução pública de código hostil; os limites operacionais estão no [guia técnico](docs/GUIA_TECNICO.md#limites).

## Conclusão

O piloto confirmou o funcionamento do fluxo, mas ainda não justifica preferir o ML à heurística. As semanas 3 a 5 ampliarão os dados, a seleção por validação e a avaliação em tipos de tarefa reservados.

## Referências

SALTZER, Jerome H.; SCHROEDER, Michael D. The protection of information in computer systems. Proceedings of the IEEE, v. 63, n. 9, p. 1278-1308, 1975. DOI: 10.1109/PROC.1975.9939. Disponível em: https://www.cs.virginia.edu/~evans/cs551/saltzer/. Acesso em: 2 nov. 2026.

KWON, Yongin et al. Mantis: Automatic Performance Prediction for Smartphone Applications. In: USENIX ANNUAL TECHNICAL CONFERENCE, 2013, San Jose. Proceedings of the 2013 USENIX Annual Technical Conference. Berkeley: USENIX Association, 2013. p. 297-308. Disponível em: https://www.usenix.org/conference/atc13/technical-sessions/presentation/kwon. Acesso em: 2 nov. 2026.

PEDREGOSA, Fabian et al. Scikit-learn: machine learning in Python. Journal of Machine Learning Research, v. 12, n. 85, p. 2825-2830, 2011. Disponível em: https://www.jmlr.org/papers/v12/pedregosa11a.html. Acesso em: 2 nov. 2026.

SCIKIT-LEARN DEVELOPERS. DecisionTreeRegressor. Scikit-learn documentation. [S. l.], [s. d.]. Disponível em: https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeRegressor.html. Acesso em: 2 nov. 2026.

SCIKIT-LEARN DEVELOPERS. Common pitfalls and recommended practices. Scikit-learn documentation. [S. l.], [s. d.]. Disponível em: https://scikit-learn.org/stable/common_pitfalls.html. Acesso em: 2 nov. 2026.

CONTAINERS PROJECT. Bubblewrap. GitHub, [s. d.]. Disponível em: https://github.com/containers/bubblewrap. Acesso em: 2 nov. 2026.

LINUX MAN-PAGES PROJECT. getrlimit(2): get/set resource limits. [S. l.], [s. d.]. Disponível em: https://www.man7.org/linux/man-pages/man2/getrlimit.2.html. Acesso em: 2 nov. 2026.

INF0336 OPERATING SYSTEMS. Modelo de relatório do seminário. GitHub, 2026. Disponível em: https://github.com/2026-2-INF0336-OperatingSystems/assets/blob/main/README.md. Acesso em: 2 nov. 2026.
