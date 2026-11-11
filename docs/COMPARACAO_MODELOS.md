# Métricas de comparação

Comparação no teste final congelado de 850 tarefas em 17 famílias inéditas. O
mesmo sandbox, entrada, teto externo e oráculo de saída foram usados para os
três métodos; cada método teve um replay por tarefa.

| Método | Conclusões | Limite médio de memória | Limite médio de parede | Tempo observado médio | Capacidades omitidas / excedentes |
|---|---:|---:|---:|---:|---:|
| Fixo | 850/850 (100,0%) | 128,00 MiB | 2,000 s | 0,122 s | 0 / 900 |
| Heurística | 770/850 (90,6%) | 50,65 MiB | 1,286 s | 0,115 s | 0 / 0 |
| Supervisionado | 781/850 (91,9%) | 39,56 MiB | 0,246 s | 0,114 s | 0 / 0 |

O modelo concluiu 11 tarefas a mais que a heurística. Reduziu o limite médio
configurado de memória em 21,9% e o limite médio de parede em 80,9%. O tempo
observado médio ficou praticamente igual entre modelo e heurística; o resultado
mostra orçamentos menores, não aceleração medida do programa nem redução de RAM
física.

| Métrica preditiva do modelo | Resultado |
|---|---:|
| MAE de memória | 5,309 MiB |
| MAE de tempo | 0,0462 s |
| F1 micro de capacidades | 1,000 |
| Correspondência exata de capacidades | 100,0% |
| Capacidades omitidas / excedentes | 0 / 0 |

| Família | Supervisionado | Heurística |
|---|---:|---:|
| `buffer_slice_checksum` | 30/50 | 15/50 |
| `jsonl_dedupe` | 32/50 | 50/50 |
| `schedule_conflict_count` | 49/50 | 35/50 |
| `set_intersection_report` | 20/50 | 20/50 |

As outras 13 famílias tiveram 50/50 conclusões nos dois métodos. As falhas
ficaram concentradas em tarefas de buffer, deduplicação e conjuntos. O modelo
tem vantagem modesta na taxa de conclusão; os intervalos descritivos de Wilson
se sobrepõem (89,9%–93,5% para o modelo e 88,4%–92,4% para a heurística). Como
há variantes correlacionadas dentro das famílias, os intervalos não demonstram
superioridade populacional.

O teste usa 17 famílias que não aparecem no treino ou na validação; nenhum
registro do teste é usado para escolher features, pesos ou margens. Os detalhes
por tarefa ficam em `reports/test-final.json`, arquivo local ignorado pelo Git.
