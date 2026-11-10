# Métricas de comparação entre modelos

Somente o modelo híbrido de 2.076 registros é mantido como artefato ativo. A
tabela resume candidatos anteriores e o modelo atual medidos no mesmo conjunto
reservado de 100 tarefas.

| Modelo comparado | Registros de treino | MAE memória (MiB) | MAE tempo (s) | Cobertura conjunta | Conclusões supervisionadas | Orçamento médio de memória |
|---|---:|---:|---:|---:|---:|---:|
| Padrão anterior | 96 | 5,979 | 0,0377 | 83% | 85/100 | 38,62 MiB |
| Candidato intermediário | 1.576 | 6,202 | 0,0558 | 90% | 90/100 | 46,74 MiB |
| Híbrido ativo | 2.076 | 6,079 | 0,0229 | 100% | 100/100 | 59,54 MiB |

O híbrido teve a maior cobertura e concluiu mais tarefas nessa comparação. Seu
orçamento médio de memória também foi maior. Os workloads são sintéticos,
executados em uma máquina; estes números não demonstram desempenho em código
arbitrário nem generalização para outros ambientes. Os dados brutos das 100
tarefas ficam locais; este documento mantém apenas as métricas comparativas.
