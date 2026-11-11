# Dados medidos e rastreabilidade

Os benchmarks são autorais e não contêm dados pessoais nem conteúdo externo. Os
programas e entradas são sintéticos/controlados; os alvos de recursos vêm de
execuções reais em Bubblewrap. Não representam tarefas de produção ou uma amostra
representativa de agentes reais.

| Arquivo | Uso | Famílias | Registros |
|---|---|---:|---:|
| `train.jsonl` | Ajuste do modelo ativo | 67 | 3.300 |
| `validation.jsonl` | Seleção das margens | 5 | 100 |
| `test.jsonl` | Avaliação final reservada | 17 | 850 |

As partições totalizam 4.250 registros; o teste corresponde a 20%. As famílias
de teste são distintas das de treino e validação, e seus registros não são
usados para ajustar o modelo.

Cada registro preserva identificador, semente, família, partição, hashes do
código e da entrada, features anteriores à execução, capacidades declaradas e
três referências. Os alvos são os maiores valores observados de VmPeak e
duração. RSS, stdout, stderr e hashes das saídas também são guardados.
Identificador, família, partição e medidas posteriores à execução não entram no
estimador.

Os geradores em `src/sentinela/tasks/` reconstroem programas e entradas; os
alvos são medições, não valores calculados por fórmula. Capacidades são rótulos
do contrato de cada tarefa, não Linux capabilities nem uma regra causal para
código arbitrário. O protocolo e as features estão em
[METODOLOGIA.md](../docs/METODOLOGIA.md).

Os resumos JSON registram contagens, famílias, ambiente de medição e SHA-256 de
cada arquivo. `models/frozen.json` registra os hashes de treino, validação e
modelo para detectar divergências entre os dados e o artefato avaliado.

Os relatórios completos ficam em `reports/`, ignorados pelo Git. A comparação
final resumida está em [COMPARACAO_MODELOS.md](../docs/COMPARACAO_MODELOS.md).
