# Avaliação da agregação CSV

fused lê e converte cada linha uma vez. auto usa ML apenas se a validação aprovar sua promoção.

## Promoção de ML

A regra exige pelo menos 5% menos tempo que a fusão, sem mais violações das metas de RSS em 24, 64 e 128 MiB.

| Meta | ML na validação (s) | Fusão (s) | Variação ML |
|---:|---:|---:|---:|
| 24 MiB | 0.90034 | 0.89422 | -0.68% |
| 64 MiB | 0.90040 | 0.89422 | -0.69% |
| 128 MiB | 0.90032 | 0.89422 | -0.68% |

ML não foi promovido. auto usa a fusão sem carregar as árvores.

## Teste reservado

O teste contém 18 tarefas em seis arquivos; cada método teve três repetições. As saídas foram comparadas com um oráculo independente.

| Método | Tempo do lote (s) | RSS médio (MiB) | Maior RSS (MiB) | Metas de 64 MiB |
|---|---:|---:|---:|---:|
| Sempre memória | 2.9438 | 33.073 | 77.711 | 15/18 |
| Sempre blocos | 5.3063 | 14.304 | 16.215 | 18/18 |
| Uma passagem | 2.4991 | 11.670 | 11.793 | 18/18 |
| Heurística | 4.7534 | 17.072 | 24.762 | 18/18 |
| ML experimental | 2.5138 | 11.670 | 11.793 | 18/18 |
| Auto atual | 2.4991 | 11.670 | 11.793 | 18/18 |
| Oráculo medido | 2.4265 | 12.767 | 18.594 | 18/18 |

As 162 execuções de referência produziram a saída esperada. No replay automático, 18/18 saídas e metas foram atendidas; o auto não carregou árvores.

Os tempos pareados somam medianas das alternativas e custos de decisão; a CLI completa é medida abaixo.

## Replay da CLI

Dois CSVs de 100.000 linhas, com 8 e 16 colunas, seis consultas e três repetições. O tempo inclui amostragem, decisão, cópia, sandbox e exportação.

| Método | Tempo mediano (s) | RSS médio mediano (MiB) | Maior RSS (MiB) | Metas atendidas |
|---|---:|---:|---:|---:|
| Sempre memória | 0.6666 | 63.191 | 77.543 | 3/6 |
| Sempre blocos | 2.0547 | 15.230 | 16.289 | 6/6 |
| Heurística | 2.0673 | 15.275 | 16.336 | 6/6 |
| Uma passagem | 0.4683 | 11.719 | 11.812 | 6/6 |
| Auto atual | 0.4789 | 11.619 | 11.762 | 6/6 |

## Limites

Benchmark sintético, um operador conhecido, uma máquina, cache aquecido e três repetições. RSS é medido por processo; os resultados não se estendem a programas arbitrários nem têm teste de significância.

O protocolo está em protocol.json. Os arquivos detalhados da avaliação ficam locais. Consulte também docs/FUSAO_E_JUSTIFICATIVA.md.
