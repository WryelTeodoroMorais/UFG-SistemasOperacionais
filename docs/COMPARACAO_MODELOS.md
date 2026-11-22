# Métricas de comparação

Esta página registra os resultados do modelo atual e mantém as rodadas anteriores
como histórico. O relatório completo, `reports/test-modelo-final.json`, é local
e ignorado pelo Git.

## Resultados finais do modelo

| Método | Conclusões | Limite médio de memória | Limite médio de tempo | Tempo observado médio | Capacidades omitidas / excedentes |
|---|---:|---:|---:|---:|---:|
| Fixo | 850/850 (100,0%) | 128,00 MiB | 2,000 s | 0,13473 s | 0 / 900 |
| Heurística | 770/850 (90,6%) | 50,65 MiB | 1,286 s | 0,12452 s | 0 / 0 |
| Supervisionado final | 850/850 (100,0%) | 45,14 MiB | 0,357 s | 0,13184 s | 0 / 0 |

O modelo manteve as conclusões e permissões corretas com limites médios menores
que a heurística, mas não foi mais rápido.

| Métrica preditiva | Resultado |
|---|---:|
| MAE de memória | 2,866 MiB |
| MAE de tempo | 0,03608 s |
| F1 micro de capacidades | 1,000 |
| Correspondência exata de capacidades | 100,0% |
| Capacidades omitidas / excedentes | 0 / 0 |

O modelo concluiu 50/50 tarefas em cada uma das 17 famílias. As famílias com
falhas anteriores foram corrigidas:

| Família | Falhas na rodada anterior | Resultado final |
|---|---|---:|
| `buffer_slice_checksum` | 20 `MemoryError` | 50/50 |
| `set_intersection_report` | 30 `MemoryError` | 50/50 |
| `jsonl_dedupe` | 5 `MemoryError` e 17 timeouts | 50/50 |

A versão final usa sinais gerais de `range`, compreensões materializadas e
alocações `bytearray`/`bytes`, além de envelopes calibrados com treino. Nenhuma
regra depende do nome da família; os detalhes estão em
[Metodologia](METODOLOGIA.md).

### Como interpretar este resultado

O modelo concluiu 50/50 tarefas em cada uma das 17 famílias. Nas três famílias
com falhas em uma rodada anterior, a versão atual também concluiu todas as
tarefas. O tempo observado do ML foi 0,13184 s, contra 0,12452 s da heurística;
o ganho ficou nas conclusões e nos limites configurados.

## Resultados anteriores

A apresentação da semana 3 registra 768/850 conclusões do modelo e 770/850 da
heurística na segunda rodada. A rodada de referência local registrou 781/850
para o modelo, 770/850 para a heurística e 850/850 para o perfil fixo. O modelo
então usava 14 features e margens menores.

Uma repetição local anterior ao ajuste final registrou 756/850 conclusões para
o modelo, 770/850 para a heurística e 850/850 para o perfil fixo. Nela, o modelo
teve 55 `MemoryError` — 20 em `buffer_slice_checksum`, 30 em
`set_intersection_report` e 5 em `jsonl_dedupe` — e 39 timeouts, incluindo 17 em
`jsonl_dedupe`. As durações variaram entre rodadas; o host não foi isolado, por
isso essas diferenças não podem ser atribuídas somente ao modelo. Esses
números descrevem versões anteriores e não são o resultado do artefato atual.

## Artefatos

Os hashes do modelo, treino e validação ficam em `models/frozen.json`. A
cobertura na validação foi 100/100 com margens 1,5/2,0. Os comandos de
reprodução estão em [Reprodução do modelo e da avaliação](REPRODUCAO_ARTEFATOS.md).
