# ML inicial: protocolo, uso e resultados

## Modelo e fronteira de autorização

O primeiro modelo aprende dois valores: pico de espaço virtual em MiB e duração
de parede em segundos. O treinamento usa
[DecisionTreeRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeRegressor.html),
com profundidade máxima 4, pelo menos 2 amostras por folha e semente 336.
Os dois alvos são transformados por `log1p` antes do ajuste. Esses parâmetros
foram fixados antes da avaliação; não houve busca de hiperparâmetros no teste.

As 11 features são tamanho da entrada e do código, contagens de nós AST,
chamadas, laços, compreensões, imports, leituras, escritas e alocações, além do
maior literal numérico. Identificador, família, partição, medições e saídas não
entram no modelo. Os argumentos de execução também não são usados.

A árvore é exportada em JSON: não há carregamento de pickle ou joblib.
A inferência valida o esquema, as features e os nós, rejeitando valores não
finitos e referências cíclicas. Ela pode ser feita sem importar scikit-learn;
a biblioteca é necessária para treinar. O caminho do modelo é explícito.

As recomendações adicionam margens fixas: `ceil(memória * 1,5 + 8)` MiB e
`tempo * 2 + 0,15` s. A política `authorize()` aplica os tetos e as permissões
do operador depois dessas margens. Leitura e escrita continuam determinadas
por AST, não por um classificador treinado. Uma previsão maior não amplia a
autoridade. Não há escalada de recursos nem troca automática de método após falha.

## Dados e reprodução

`collect` cria 32 tarefas determinísticas em quatro famílias: alocação de
bytearray, cálculo, leitura de texto e escrita de arquivo. Cada tarefa é
executada duas vezes com limites de referência de 256 MiB, 5 s de parede,
3 s de CPU e 4 MiB por arquivo de saída. A coleta precisa passar pelo `doctor`.
Só medições com retorno zero, sem timeout e com pico virtual positivo entram
no dataset; as saídas das duas repetições devem coincidir.

Das oito variantes por família, os índices 2 e 6 são reservados para teste.
Há 24 tarefas de treino e 8 de teste, com variantes das mesmas famílias em
ambas as partições. O alvo de cada tarefa é o máximo das duas medições de cada
recurso. Essa pequena coleta serve para demonstrar o pipeline, não para estimar
desempenho em famílias inéditas ou tarefas de agentes reais.

O dataset JSON guarda código, texto de entrada, partição e medições completas.
`train` recalcula as features, ignora cópias pré-calculadas em datasets antigos,
recusa tarefas duplicadas e não ajusta a árvore com rótulos do teste.
Datasets externos devem seguir `sentinela-measurements-v1`, com a mesma estrutura
do arquivo incluído. O operador responde pela origem e veracidade dos dados;
a validação estrutural não atesta que uma medição externa foi realizada.

Os comandos de reprodução estão no [README](../README.md#ml-inicial).
`train` não executa os scripts; `collect` e `evaluate` usam a sandbox.
`evaluate` exige que o SHA-256 do dataset
corresponda ao registrado no modelo. O comando reexecuta somente as tarefas
reservadas, uma vez por método, em ordem embaralhada com semente 336. Sucesso
exige retorno zero, ausência de timeout, stdout igual e mesmos nomes, tamanhos
e hashes de arquivos exportados. O processo termina normalmente quando a
avaliação é concluída; as falhas de tarefas ficam registradas em `correct`.

## Piloto medido em 02/11/2026

Artefatos: [dataset](../data/initial-measurements.json),
[modelo e métricas de predição](../models/initial-tree.json) e
[reexecução completa](../reports/initial-replay.json). O modelo guarda versão
do scikit-learn, parâmetros, instante de treino e SHA-256 dos dados. As medições
guardam seu instante de coleta e a plataforma real.

No teste, o erro absoluto médio da previsão sem margens foi aproximadamente
0,94 MiB de espaço virtual e 0,0094 s de duração. As margens dos três métodos
cobriram as medições de referência de todas as oito tarefas. Essa cobertura
é uma comparação numérica, distinta da reexecução abaixo.

| Método | Reexecuções corretas | Limite médio de memória virtual |
|---|---:|---:|
| Fixo | 8/8 | 128 MiB |
| Heurística | 8/8 | 35 MiB |
| ML | 8/8 | 42,25 MiB |

O ML funciona neste piloto, mas não supera a heurística no limite médio.
As durações observadas foram próximas de 0,05 s, sem repetições suficientes
para afirmar ganho temporal. Limite de espaço virtual não é consumo de RAM
física nem reserva de memória. A amostragem de `/proc` pode perder picos curtos,
e as medições dependem da máquina e da carga.

O conjunto é pequeno e autoral, sem conjunto de validação separado. As margens
são conservadoras e fixas. Antes de justificar uso mais amplo, faltam famílias
reservadas, tarefas reais, validação de margens, mais repetições e tratamento
de mudanças de ambiente. Nenhum desses resultados certifica a sandbox para
execução pública de código hostil.
