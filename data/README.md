# Dados medidos e rastreabilidade

Os benchmarks são autorais e não contêm dados pessoais nem conteúdo externo. Os
programas e entradas são sintéticos/controlados; os alvos de recursos vêm de
execuções reais em sandbox Linux. Não representam tarefas de produção ou uma
amostra de agentes reais.

| Arquivo | Uso | Registros |
|---|---|---:|
| `train.jsonl` | Treino do único modelo ativo | 2.076 |
| `validation.jsonl` | Seleção das margens do modelo ativo | 100 |
| `test.jsonl` | Avaliação original complementar | 24 |

Os 2.076 registros de treino já estão reunidos em `train.jsonl`. A comparação
entre modelos usa também um conjunto reservado de 100 tarefas cujos registros
brutos são locais; apenas as métricas resumidas estão em
[COMPARACAO_MODELOS.md](../docs/COMPARACAO_MODELOS.md).

Cada registro guarda identificador, semente, família, partição, hashes do código
e da entrada, features anteriores à execução, contrato de capacidades, três
execuções e `observed_at_utc`, que registra o instante real da medição. Os alvos
são os maiores valores observados de VmPeak e duração entre as três referências.
RSS, stdout, stderr e hashes das saídas também são preservados. Identificador,
família, partição e medidas posteriores à execução não alimentam o estimador.

As entradas podem ser reconstruídas pelos geradores em `src/sentinela/tasks/`.
Não há telemetria gerada por fórmula: os programas e entradas são sintéticos,
mas os alvos foram medidos em execuções reais. Capacidade é um rótulo do
contrato da tarefa, não uma Linux capability nem uma inferência causal sobre
código arbitrário.

Os resumos JSON registram contagens, famílias, ambiente de medição e SHA-256 de
cada arquivo. O modelo congelado registra os hashes de treino e validação para
detectar divergências entre os dados e os artefatos usados na avaliação.
