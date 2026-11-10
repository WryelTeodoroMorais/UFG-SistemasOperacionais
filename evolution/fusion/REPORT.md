# Ganho real: agregação fundida e verificação da necessidade de ML

O projeto anterior escolhia entre carregar tudo em memória e reler o CSV para cada consulta. Essa referência era fraca: consultas aditivas conhecidas podem compartilhar a leitura, a conversão e a soma de cada linha. A versão atual implementa essa fusão e compara o modelo contra ela.

## Uso prático

Executar várias contagens/somas por limiar em CSVs numéricos, por exemplo, relatórios solicitados por agentes sobre dados tabulares. O operador é conhecido e as implementações têm a mesma saída. A fusão não reescreve qualquer programa ou aplicação automaticamente. A sandbox continua oferecendo execução delimitada; sua cópia de entrada e seus custos de inicialização permanecem na medição.

## Validação e promoção de ML

Um regressor Extra Trees de 128 árvores foi treinado no treino e calibrado na validação para prever RAM e tempo dos três candidatos. A regra, fixada antes do teste, exige pelo menos 5% de redução do tempo em relação a sempre usar fusão, sem mais violações de metas de RSS, em todas as metas 24/64/128 MiB.

| Meta | Tempo ML na validação (s) | Tempo fusão (s) | Ganho relativo ML |
|---|---:|---:|---:|
| 24 MiB | 0.90034 | 0.89422 | -0.68% |
| 64 MiB | 0.90040 | 0.89422 | -0.69% |
| 128 MiB | 0.90032 | 0.89422 | -0.68% |

ML promovido: **False**. Motivo: fused_baseline_not_beaten_on_validation. Teste utilizado na promoção: False.

O resultado negativo é preservado: escolher a mesma implementação fundida acrescentou custo de inferência/carga sem benefício. O auto atual, portanto, não usa as árvores nesse caso. O ganho do produto deve ser atribuído à eliminação de trabalho redundante, e não ao modelo supervisionado. O código e os dados da avaliação de ML permanecem entregues e reproduzíveis.

## Teste reservado com configuração congelada

18 tarefas lógicas de seis arquivos novos, com tamanhos distintos dos do treino/validação e três estratégias por tarefa. Cada alternativa teve três repetições, com ordem embaralhada. Todas as estratégias foram verificadas contra um oráculo independente que inclui negativos e valores de fronteira.

| Método | Tempo pareado do lote (s) | Média dos picos RSS (MiB) | Maior pico (MiB) | Meta de 64 MiB atendida |
|---|---:|---:|---:|---:|
| Sempre memória | 2.9438 | 33.073 | 77.711 | 15/18 |
| Sempre blocos | 5.3063 | 14.304 | 16.215 | 18/18 |
| Uma passagem | 2.4991 | 11.670 | 11.793 | 18/18 |
| Heurística | 4.7534 | 17.072 | 24.762 | 18/18 |
| ML experimental | 2.5138 | 11.670 | 11.793 | 18/18 |
| Auto atual | 2.4991 | 11.670 | 11.793 | 18/18 |
| Oráculo medido | 2.4265 | 12.767 | 18.594 | 18/18 |

Execuções de referência corretas no teste: 162. Reexecução automática: 18/18 saídas corretas e 18/18 metas atendidas. O auto carrega árvores: False.

Os tempos pareados somam medianas das alternativas medidas e custos de decisão; não são uma única execução completa da CLI. O orçamento externo é igual entre as estratégias. RSS é RAM residente do processo, não apenas concessão de memória virtual. As metas de RSS são objetivos de seleção e verificação, não quotas rígidas de RSS.

## Lote completo: caminho real da CLI

Dois arquivos de 100000 linhas, 8 e 16 colunas, seis consultas por arquivo. Três repetições por método, ordem embaralhada. O tempo inclui amostragem, decisão, cópia, sandbox e exportação; exclui a inicialização do interpretador da CLI. São arquivos já presentes no teste, usados como demonstração sem retreino.

| Método | Mediana do tempo completo (s) | Mediana da média dos picos RSS (MiB) | Maior pico (MiB) | Metas atendidas |
|---|---:|---:|---:|---:|
| Sempre memória | 0.6666 | 63.191 | 77.543 | 3/6 |
| Sempre blocos | 2.0547 | 15.230 | 16.289 | 6/6 |
| Heurística | 2.0673 | 15.275 | 16.336 | 6/6 |
| Uma passagem | 0.4683 | 11.719 | 11.812 | 6/6 |
| Auto atual | 0.4789 | 11.619 | 11.762 | 6/6 |

Ganhos do auto atual nesse lote:

- Contra Sempre memória: 28.16% menos tempo e 81.61% menor média de picos RSS.
- Contra Sempre blocos: 76.69% menos tempo e 23.71% menor média de picos RSS.

## Justificativa e conclusão

Há uma justificativa operacional concreta: reduzir leitura, conversão e cálculo repetidos em agregações conhecidas, preservando os resultados e o isolamento. O ganho é medido em tempo e RAM efetivos. Para essa operação, não houve justificativa de produção para ML; a política usa a referência eficiente e evita custo estatístico desnecessário. O estudo supervisionado continua relevante como avaliação comparativa, inclusive por permitir essa conclusão negativa.

Não se deve afirmar inovação do algoritmo de fusão, necessidade universal de IA, otimização de código arbitrário ou economia de energia. O projeto agora oferece uma melhoria real para um operador delimitado, com atribuição correta da causa do ganho. Para justificar ML em outro operador, será necessária nova rodada e novas referências fortes; não bastará comparar com implementações deliberadamente inferiores.

Limitações: dados autorais sintéticos, uma máquina, cache de arquivos aquecido, três repetições e sem teste de significância. Tamanhos novos do mesmo operador não provam generalização a programas novos. O consumo é RSS por processo; não inclui PSS ou RAM total do host. As restrições de isolamento do protótipo permanecem descritas no guia de execução.

O resumo e o protocolo são versionados; os CSVs, replays e JSONs detalhados ficam locais. Guia: ../../docs/FUSAO_E_JUSTIFICATIVA.md.
