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

1. [Apresentação da segunda semana](docs/apresentacoes/semana-2/apresentacao-semana-2.pptx) e [versão PDF](docs/apresentacoes/semana-2/apresentacao-semana-2.pdf).

## Resumo

O projeto avalia um modelo que recomenda limites de recursos e acessos para
programas Python executados em sandbox Linux. Uma política independente aplica
os tetos definidos pelo operador.

O dataset contém 3.300 exemplos de treino. No teste de 850 tarefas, o modelo
concluiu 781, contra 770 da heurística. Seu orçamento médio foi menor, mas o
tempo de execução observado ficou praticamente igual. Os resultados se
limitam aos workloads controlados deste projeto.

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

O teste corresponde a 20% dos 4.250 exemplos e não é usado para ajustar o
modelo. Cada tarefa tem três execuções de referência. Não há dados de usuários
nem revisão humana independente.

### Modelos e infraestrutura

O modelo usa 14 características do código e da entrada. Extra Trees estima
memória e acessos de leitura/escrita; Gradient Boosting estima tempo. O
executor usa Bubblewrap, namespaces, rede isolada e limites Linux de memória
virtual, CPU, tamanho de arquivo e descritores. A política externa restringe
cada recomendação ao teto do operador.

### Métricas e fluxograma

Medimos conclusão correta, MAE de memória e tempo, F1 de acessos, omissões,
excessos, limites configurados e duração observada. Uma conclusão exige saída
de sucesso sem timeout e correspondência do stdout e dos arquivos esperados.

![Fluxo de coleta, treinamento, autorização e execução](docs/figures/fluxograma.png)

*Figura 1 — Fluxo do experimento. Fonte: elaboração da equipe.*

### Operação CSV

A operação CSV usa `fused`, que lê e processa cada linha uma vez. A seleção por
ML só é usada se passar o critério de promoção; os resultados e comandos estão
em [Fusão CSV](docs/FUSAO_E_JUSTIFICATIVA.md).

## Resultados

### Funcionamento do protótipo

A validação funcional registrou nove verificações de contenção e 45 testes de
integração com namespaces habilitados. Esses resultados não equivalem a uma
auditoria de segurança.

### Comparação dos métodos

| Método | Tarefas concluídas | Memória configurada | Limite de parede | Tempo observado | Acessos omitidos/excedentes |
|---|---:|---:|---:|---:|---:|
| Fixo | 850/850 | 128,00 MiB | 2,000 s | 0,122 s | 0/900 |
| Heurística | 770/850 | 50,65 MiB | 1,286 s | 0,115 s | 0/0 |
| Supervisionado | 781/850 | 39,56 MiB | 0,246 s | 0,114 s | 0/0 |

*Tabela 1 — Resultados no teste. Fonte: [métricas de comparação](docs/COMPARACAO_MODELOS.md).*

### Tempos e consumo medidos

![Comparação dos métodos no teste final de 850 tarefas](docs/figures/method-comparison.png)

*Figura 2 — Conclusões, limites médios e duração observada. Fonte: elaboração da equipe.*

Os limites de memória e parede são orçamentos configurados; não representam
RAM física ou duração real. O tempo medido do modelo e da heurística foi
praticamente igual.

## Discussão

O modelo concluiu 11 tarefas a mais que a heurística, mas os intervalos
descritivos se sobrepõem. As tarefas são autorais, executadas em uma máquina, e
cada método teve um replay por tarefa. A memória limitada é espaço virtual por
processo; o protótipo não está pronto para executar código hostil como serviço
público. [Metodologia](docs/METODOLOGIA.md) descreve os limites do experimento.

## Conclusão

O modelo reduziu os limites configurados e obteve mais conclusões corretas que
a heurística neste conjunto. Isso ainda precisa ser confirmado com programas
reais e outros ambientes.

## Referências

1. SALTZER, Jerome H.; SCHROEDER, Michael D. The protection of information in computer systems. *Proceedings of the IEEE*, v. 63, n. 9, p. 1278–1308, 1975. [Texto](https://www.cs.virginia.edu/~evans/cs551/saltzer/).
2. GEURTS, Pierre; ERNST, Damien; WEHENKEL, Louis. Extremely randomized trees. *Machine Learning*, v. 63, p. 3–42, 2006. [DOI](https://doi.org/10.1007/s10994-006-6226-1).
3. PEDREGOSA, Fabian et al. Scikit-learn: machine learning in Python. *Journal of Machine Learning Research*, v. 12, n. 85, p. 2825–2830, 2011. [Artigo](https://www.jmlr.org/papers/v12/pedregosa11a.html).
4. CONTAINERS PROJECT. Bubblewrap: low-level unprivileged sandboxing tool. [Repositório](https://github.com/containers/bubblewrap).
5. LINUX MAN-PAGES PROJECT. getrlimit(2): get/set resource limits. [Manual](https://www.man7.org/linux/man-pages/man2/getrlimit.2.html).
6. LINUX MAN-PAGES PROJECT. namespaces(7): overview of Linux namespaces. [Manual](https://www.man7.org/linux/man-pages/man7/namespaces.7.html).
7. SCIKIT-LEARN DEVELOPERS. Common pitfalls and recommended practices. [Documentação](https://scikit-learn.org/1.5/common_pitfalls.html).
