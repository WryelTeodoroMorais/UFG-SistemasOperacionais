# Ganho real e justificativa de uso

Esta versão corrige o problema da referência anterior: o modo em blocos relia e reconvertia o CSV para cada consulta. Como as consultas são conhecidas e aditivas, isso era trabalho evitável. Melhorar a seleção entre duas implementações inferiores não bastava para justificar o projeto nem ML.

## Implementação de uma passagem

A nova estratégia fused lê o CSV uma vez, converte cada linha para inteiros uma vez e calcula a soma das colunas. Em vez de atualizar cada consulta individualmente, classifica essa soma em um intervalo dos limiares 0, 997, 1994 etc. Depois acumula os intervalos para produzir as mesmas contagens e somas de todas as consultas.

Não mantém uma lista de todos os registros nem um bloco inteiro de linhas. A memória depende do registro atual, dos buffers do CSV e dos pequenos vetores de consultas, em vez de crescer como uma cópia de todo o arquivo. O algoritmo trata números negativos e valores exatamente iguais aos limiares; os testes verificam o resultado contra um cálculo independente.

| Estratégia | Leitura e conversão | Dados mantidos |
|---|---|---|
| memory | Uma leitura, depois percorre os registros a cada consulta | Todos os registros |
| blocks | Uma leitura e conversão para cada consulta | Um bloco de registros |
| fused | Uma leitura e conversão para todas as consultas | Registro atual e acumuladores |

Isso se aplica a esta operação conhecida de agregação, não a qualquer programa Python. O comando run continua disponível para execução de scripts; ele não reescreve algoritmos automaticamente.

## Como usar

`auto` é o padrão recomendado: segue a política validada e usa `fused` quando nenhum modelo ML é promovido. `fused` executa a referência de uma passagem diretamente. A CLI aceita somente essas duas opções; `memory`, `blocks` e `heuristic` ficam restritas aos scripts de benchmark.

Os CSVs de benchmark são sintéticos e ficam locais, fora do Git. A fase `fit` se recusa a substituir uma rodada existente; para repetir o experimento, use uma cópia de trabalho sem `evolution/fusion/` e rode `.venv/bin/python scripts/benchmark_fusion.py --phase fit`, seguido de `--phase final`. Para experimentar a CLI em um clone, troque os caminhos abaixo por `examples/entrada.csv` ou por seus próprios arquivos.

```bash
cd "/home/wryel/Documentos/Sistemas Operacionais/sentinela-ml"

.venv/bin/sentinela process-csv \
  evolution/fusion/inputs/test-100000-8.csv \
  evolution/fusion/inputs/test-100000-16.csv \
  --strategy auto --memory-target-mb 64 --passes 6 \
  --output "teste-fusao-$(date +%s)"
```

As comparações com `memory`, `blocks` e `heuristic` estão no relatório e nos scripts de benchmark; essas referências não são opções da CLI. `auto` segue a regra atual de promoção e, sem modelo aprovado na validação, escolhe uma passagem sem carregar árvores.

Antes de executar, consulte o plano para ver a estratégia escolhida, as features amostradas e as estimativas por arquivo:

```bash
.venv/bin/sentinela plan-csv \
  evolution/fusion/inputs/test-100000-8.csv \
  --strategy auto --memory-target-mb 64 --passes 6
```

`plan-csv` não inicia o sandbox. O JSON lista limiares, coluna consultada, metadados amostrados, estratégia e candidatos previstos quando o modelo estiver promovido. Para executar, use os mesmos argumentos em `process-csv` e informe uma pasta nova com `--output`. Estimativas de RSS e tempo são previsões, não garantias.

A meta de RSS orienta decisões e é verificada depois da execução; não é uma quota rígida de RAM física. Os limites de execução são iguais entre estratégias. Permanecem os limites de isolamento documentados em EXECUCAO.md.

### Consultar seus próprios dados

Você pode escolher os limiares e uma coluna, em vez de ficar limitado ao operador fixo do benchmark:

```bash
.venv/bin/sentinela process-csv examples/entrada.csv \
  --value-column 1 --thresholds 0,20,100 --strategy auto \
  --output "consulta-coluna-$(date +%s)"
```

O índice começa em zero: 1 seleciona a segunda coluna. Nesse exemplo, o relatório contém três linhas e as consultas: limiar 0, contagem 3, soma 60; limiar 20, contagem 2, soma 50; limiar 100, contagem 0, soma 0. Sem --value-column, cada registro vale a soma de suas colunas. Com --header, a primeira linha é ignorada. Os demais campos ainda devem ser inteiros; não é um leitor genérico de tabelas mistas.

--thresholds aceita de 1 a 8 inteiros em ordem crescente, sem repetições, e substitui --passes. Para iniciar com um valor negativo, use a forma --thresholds=-10,0,997. `auto` usa a fusão por regra algébrica para consultas configuráveis e informa `ml_used=false`: esses operadores não participaram do treino, e os percentuais do benchmark não são extrapolados a eles.

## Onde entra aprendizado supervisionado

A nova rodada mede três candidatos, incluindo fused. O modelo supervisionado prediz RAM e duração por candidato, com as mesmas features prévias da rodada anterior e um indicador adicional da estratégia fundida. Treino e validação usam arquivos separados, e o teste só é gerado depois de congelar os artefatos e a decisão de promoção.

A regra de promoção exige pelo menos 5% de redução no tempo total da validação e nenhuma piora no número de metas de RSS atendidas, em cada meta de 24, 64 e 128 MiB. O custo de inferência e carga das árvores entra na comparação. Essa regra foi especificada antes do teste. Se o modelo não passar, o auto não carrega as árvores e não paga seu custo para tomar uma decisão que uma implementação eficiente já resolve.

Um resultado negativo para ML é parte da análise, não motivo para esconder a referência forte ou tornar os concorrentes artificialmente ruins. A justificativa operacional da ferramenta é executar a agregação com menos trabalho, mesma saída e isolamento. Uma justificativa específica para ML depende de superar essa referência; não será presumida.

## Evidências da rodada nova

O protocolo está em evolution/fusion/protocol.json. O estudo usa 432 execuções de referência: 18 tarefas de treino, 12 de validação e 18 de teste, cada uma executada com três estratégias e três repetições. Todas as variantes de um arquivo permanecem na mesma partição. As sementes, hashes das entradas e hashes do código gerado são registrados. O oráculo de correção usa os valores gerados, com casos explícitos de fronteira e negativos.

O resumo e a decisão de promoção estão em evolution/fusion/REPORT.md e frozen.json. Os CSVs gerados, JSONs brutos de medição e replays ficam locais e não são versionados. Os modos memory, blocks e fused usam exatamente o mesmo orçamento externo. São medidos duração total da requisição ao executor, CPU e pico de RSS real, e não apenas o limite concedido.

A demonstração completa compara os caminhos da CLI, incluindo amostragem da entrada, decisão, cópia, criação da sandbox e exportação. Repete os lotes três vezes com ordem embaralhada. Ela usa arquivos já presentes no teste para ilustrar o comportamento, sem retreino; não é um novo conjunto independente.

## Preservação das entregas e reprodução

Os artefatos brutos de execução permanecem locais; os protocolos e resultados resumidos desta avaliação ficam versionados. O README mantém o relatório consolidado do projeto.

Para repetir a nova coleta em uma cópia limpa sem evolution/fusion:

```bash
.venv/bin/python scripts/benchmark_fusion.py --phase fit
.venv/bin/python scripts/benchmark_fusion.py --phase final
```

Os comandos recusam sobrescrever rodadas fechadas. O código das estratégias é verificado antes do teste para impedir mudanças silenciosas após a coleta. Testes automatizados incluem equivalência de hashes, fronteiras dos limiares, negativos, cabeçalho e rejeição de ML sem benefício na validação. As saídas extensas desse processo são locais e ignoradas pelo Git.

## Limites da conclusão

Benchmarks de CSVs numéricos autorais, uma máquina, cache de arquivos aquecido, três repetições e um operador conhecido. Não demonstram que qualquer aplicação ficará mais rápida, que qualquer código de agente pode ser otimizado ou que ML é universalmente necessário. RSS é do processo executor, não RAM total da máquina nem consumo de energia. A decisão de promoção é baseada na validação; o teste relata o que ocorreu sem novo ajuste.
