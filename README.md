# INF0336 - Seminário

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

1. [Semana 1 — Apresentação inicial da proposta (PowerPoint)](docs/apresentacoes/semana-1/apresentacao-semana-1.pptx) e [versão PDF](docs/apresentacoes/semana-1/apresentacao-semana-1.pdf).
2. [Semana 3 — Apresentação dos resultados (PowerPoint)](docs/apresentacoes/semana-3/apresentacao-semana-3.pptx) e [versão PDF](docs/apresentacoes/semana-3/apresentacao-semana-3.pdf).

## Resumo

O projeto recomenda limites de recursos e acessos para scripts Python em
sandbox Linux; uma política externa aplica o teto do operador. A versão final
usa 17 atributos estáticos e envelopes calibrados com treino. Na avaliação
final, concluiu 850/850 tarefas em 17 famílias (50/50 por família), contra
770/850 da heurística; seus limites médios foram 45,14 MiB e 0,357 s, contra
50,65 MiB e 1,286 s da heurística. A execução observada do ML foi 0,132 s,
contra 0,125 s da
heurística: o ganho foi em contenção funcional e limites configurados, não em
velocidade. O protocolo e a interpretação estão em
[Metodologia](docs/METODOLOGIA.md) e
[Métricas de comparação](docs/COMPARACAO_MODELOS.md).

## Introdução

### Motivação

Limites amplos permitem uso desnecessário de recursos; limites restritos podem
interromper tarefas legítimas. O projeto investiga se previsões baseadas no
código ajudam a escolher limites, mantendo a autorização sob controle externo.

### Revisão bibliográfica

Saltzer e Schroeder [1] fundamentam o princípio do menor privilégio. Extra Trees
[2] e scikit-learn [3] fundamentam os estimadores. Bubblewrap [4] e os manuais
Linux de limites [5] e namespaces [6] descrevem os mecanismos de isolamento.
As práticas de avaliação do scikit-learn [7] orientam a separação entre treino,
validação e teste.

### Objetivos

Construir um executor isolado, estimar recursos e acessos, comparar o modelo
com uma heurística e um perfil fixo, e medir a contenção funcional.

## Metodologia

### Conjunto de dados e análise inicial

Os workloads são sintéticos e organizados por famílias inteiras em cada
partição, reduzindo a semelhança entre treino e teste.

| Partição | Tarefas | Famílias |
|---|---:|---:|
| Treino | 3.300 | 67 |
| Validação | 100 | 5 |
| Teste | 850 | 17 |

O teste corresponde a 20% dos 4.250 exemplos. Cada tarefa tem três execuções
de referência. Os workloads são sintéticos e foram criados para este projeto.

### Modelos e infraestrutura

O modelo usa 17 características estáticas do código e da entrada. Extra Trees
estima memória e acessos de leitura/escrita; Gradient Boosting estima tempo.
Características de faixas, coleções materializadas e alocações literais ajudam
a identificar padrões de consumo sem regras pelo nome da tarefa. Envelopes
calibrados apenas no treino protegem entradas e coleções grandes. O executor usa
Bubblewrap, namespaces, rede isolada e limites Linux de memória virtual, CPU,
tamanho de arquivo e descritores. A política externa restringe cada
recomendação ao teto do operador.

### Métricas e fluxograma

Medimos conclusão correta, MAE de memória e tempo, F1 de acessos, omissões,
excessos, limites configurados e duração observada. Uma conclusão exige saída
de sucesso sem timeout e correspondência do stdout e dos arquivos esperados.

![Fluxo de coleta, treinamento, autorização e execução](docs/figures/fluxograma.png)

*Figura 1 — Fluxo do experimento. Fonte: elaboração da equipe.*

## Resultados

### Funcionamento do protótipo

A suíte cobre componentes unitários e de integração. O comando `sentinela security`
executa nove casos controlados e verifica se a política rejeita pedidos de
acesso à rede. Os comandos de verificação e os limites estão no [guia de
execução](docs/EXECUCAO.md).

### Comparação dos métodos — versão final

| Método | Tarefas concluídas | Memória configurada | Limite de tempo | Tempo observado | Acessos omitidos/excedentes |
|---|---:|---:|---:|---:|---:|
| Fixo | 850/850 | 128,00 MiB | 2,000 s | 0,135 s | 0/900 |
| Heurística | 770/850 | 50,65 MiB | 1,286 s | 0,125 s | 0/0 |
| Supervisionado final | 850/850 | 45,14 MiB | 0,357 s | 0,132 s | 0/0 |

*Tabela 1 — Resultados finais em 850 tarefas. Fonte: [métricas de comparação](docs/COMPARACAO_MODELOS.md).*

O modelo concluiu 50/50 tarefas em cada família com limites médios menores que
a heurística, mas não foi mais rápido. O histórico das rodadas está em
[Métricas de comparação](docs/COMPARACAO_MODELOS.md).

### Limites configurados e duração medida

![Comparação dos métodos nos resultados finais de 850 tarefas](docs/figures/method-comparison.png)

*Figura 2 — Conclusões, limites médios e duração observada. Fonte: elaboração da equipe.*

## Discussão

A política que limita a recomendação aplica o princípio do menor privilégio
[1]. Extra Trees e os estimadores do scikit-learn fundamentam a previsão de
recursos [2, 3], enquanto a separação das famílias segue cuidados para evitar
vazamento entre variantes [7]. Bubblewrap e os limites de recursos e namespaces
do Linux fornecem os mecanismos de isolamento usados pelo protótipo [4–6]. A
avaliação compara workloads sintéticos executados em uma máquina Linux; o
ambiente e o protocolo estão detalhados na [metodologia](docs/METODOLOGIA.md).

## Conclusão

O projeto integra recomendação de recursos, autorização por política e
execução isolada de scripts Python. Na avaliação final, o modelo concluiu
850/850 tarefas, contra 770/850 da heurística, com limites médios menores. O
tempo observado foi 0,132 s para o modelo e 0,125 s para a heurística; o ganho
ficou na contenção funcional e nos limites configurados.

## Referências

1. SALTZER, Jerome H.; SCHROEDER, Michael D. The protection of information in computer systems. *Proceedings of the IEEE*, v. 63, n. 9, p. 1278–1308, 1975. [Texto](https://www.cs.virginia.edu/~evans/cs551/saltzer/).
2. GEURTS, Pierre; ERNST, Damien; WEHENKEL, Louis. Extremely randomized trees. *Machine Learning*, v. 63, p. 3–42, 2006. [DOI](https://doi.org/10.1007/s10994-006-6226-1).
3. PEDREGOSA, Fabian et al. Scikit-learn: machine learning in Python. *Journal of Machine Learning Research*, v. 12, n. 85, p. 2825–2830, 2011. [Artigo](https://www.jmlr.org/papers/v12/pedregosa11a.html).
4. CONTAINERS PROJECT. Bubblewrap: low-level unprivileged sandboxing tool. [Repositório](https://github.com/containers/bubblewrap).
5. LINUX MAN-PAGES PROJECT. getrlimit(2): get/set resource limits. [Manual](https://www.man7.org/linux/man-pages/man2/getrlimit.2.html).
6. LINUX MAN-PAGES PROJECT. namespaces(7): overview of Linux namespaces. [Manual](https://www.man7.org/linux/man-pages/man7/namespaces.7.html).
7. SCIKIT-LEARN DEVELOPERS. Common pitfalls and recommended practices. [Documentação](https://scikit-learn.org/1.5/common_pitfalls.html).
