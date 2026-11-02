# ML inicial: técnica, treinamento e resultados

## Qual técnica está sendo usada?

Usamos **aprendizado supervisionado com uma árvore de decisão de regressão**,
implementada pelo
[DecisionTreeRegressor do scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeRegressor.html).

É supervisionado porque o treino recebe exemplos com consumo já medido.
É regressão porque prevê valores numéricos: **pico de memória virtual, em MiB,
e tempo decorrido, em segundos**. Uma única árvore prevê os dois valores;
o modelo não prevê diretamente o consumo de RAM.

A árvore aprende condições sobre as características dos programas, separando
os exemplos em grupos. Para uma nova tarefa, percorre essas condições até
uma folha, que fornece as duas estimativas. Essas condições são aprendidas
com os dados, em vez de serem escritas manualmente como na heurística.

## Como o modelo é treinado?

1. **Coletar exemplos.** O comando `collect` executa 32 tarefas autorais,
   divididas em alocação de memória, cálculo, leitura e escrita. Cada tipo tem
   oito variações de tamanho, e cada tarefa é executada duas vezes na sandbox:
   são 64 medições de referência.
2. **Preparar as entradas e os valores esperados.** Para cada tarefa, extraímos
   11 características do código e da entrada, incluindo tamanhos, estrutura
   sintática, chamadas e laços. Os valores que o modelo deve aprender são o
   maior pico de memória virtual e o maior tempo decorrido das duas medições.
   Assim, as duas execuções formam **um exemplo por tarefa**.
3. **Separar treino e teste.** Usamos 24 tarefas no ajuste e reservamos oito
   para teste: as variações de índice 2 e 6 de cada tipo. As tarefas de teste
   não ajustam a árvore. Identificador, tipo de tarefa, saídas e medições não
   entram como características; os argumentos do script também não entram.
4. **Ajustar a árvore.** O comando `train` usa as características das tarefas
   de treino e seus consumos medidos. Antes do ajuste, aplica `log1p` aos dois
   valores esperados para reduzir diferenças de escala. A árvore é limitada
   a profundidade 4, com pelo menos duas tarefas por folha e semente 336.
   Esses parâmetros foram fixados antes da avaliação.
5. **Salvar e avaliar.** A árvore é exportada em JSON, com previsões convertidas
   de volta às unidades originais. Mantemos o modelo fixo e reexecutamos as
   oito tarefas de teste com os métodos fixo, heurístico e ML, uma vez por método.

`train` usa as medições salvas e não executa os scripts novamente. `collect`
e `evaluate` executam as tarefas na sandbox. O JSON permite fazer previsões
sem carregar pickle ou joblib; o scikit-learn é necessário para o treinamento.

## Como a previsão é usada?

Antes da execução, adicionamos margens fixas às estimativas:

- Memória virtual: `ceil(memória prevista × 1,5 + 8)` MiB.
- Tempo decorrido: `tempo previsto × 2 + 0,15` s.

Depois, a política `authorize()` aplica os tetos e as permissões do operador.
O modelo recomenda recursos; não concede acessos. Leitura e escrita continuam
identificadas por análise estática do código. Não há aumento automático de
recursos nem troca de método após uma falha.

Os comandos de coleta, treino e avaliação estão no
[guia técnico](GUIA_TECNICO.md#ml-inicial).

## Resultados do piloto

Artefatos: [dados](../data/initial-measurements.json),
[modelo treinado](../models/initial-tree.json) e
[relatório de avaliação](../reports/initial-replay.json).

| Método | Tarefas corretas | Limite médio de memória virtual (MiB) |
|---|---:|---:|
| Fixo | 8/8 | 128 |
| Heurística | 8/8 | 35 |
| ML | 8/8 | 42,25 |

Uma tarefa correta termina sem erro ou timeout e produz a mesma saída esperada
no terminal e nos arquivos. O erro absoluto médio das previsões sem margens
foi de aproximadamente 0,94 MiB e 0,0094 s. Os limites dos três métodos cobriram
as medições de referência das oito tarefas.

**O ML funcionou no piloto, mas não superou a heurística no limite recomendado.**
Os tempos médios ficaram próximos de 50 ms e o pico médio de RAM próximo de
12,3 MiB nos três métodos. As medições de execução estão detalhadas no
[README](../README.md#tempos-e-consumo-medidos).

## Limitações

O conjunto é pequeno, e os mesmos quatro tipos de tarefa aparecem no treino
e no teste. Não há validação separada para escolher modelos ou calibrar
margens. Uma reexecução por método e tarefa também não é suficiente para
concluir ganho de desempenho a partir de pequenas diferenças.

Limite de memória virtual não é consumo de RAM. As medições dependem da
máquina e da carga, e a amostragem pode perder picos curtos. A próxima avaliação
precisa de mais tarefas, tipos ausentes do treino e medições repetidas.
Os resultados não certificam segurança para execução pública de código hostil.
