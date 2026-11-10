# Protocolo experimental definido antes do teste

## Pergunta e hipótese

Um recomendador supervisionado consegue reduzir os limites configurados e as capacidades excedentes de uma sandbox sem reduzir a conclusão correta de tarefas em relação a perfis fixos e uma heurística? Reduzir o limite configurado não significa reduzir consumo físico nem reservar menos RAM: essas grandezas são relatadas separadamente.

Hipóteses: H1, recomendar limites de espaço virtual e tempo conforme o programa evita superdimensionamento uniforme; H2, classificar acesso à entrada e saída pode reduzir capacidades excedentes; H3, erros de generalização podem impedir tarefas novas, portanto segurança do executor e qualidade do modelo devem ser avaliadas separadamente. Não se presume vitória de ML.

## Escopo implementado

Execução de scripts Python/stdlib recebidos como arquivos, interface que pode ser chamada por um agente externo, sem API paga ou LLM obrigatório. O projeto não implementa um agente gerador completo e não avalia gerações de LLM reais. O usuário autoriza explicitamente os arquivos de entrada e o destino; o modelo não cria caminhos ou concede rede. O protótipo trabalha com uma entrada nomeada /input/data.txt e saídas em /output.

Bubblewrap monta /usr e bibliotecas como somente leitura, cria namespaces e expõe somente a entrada selecionada. A rede externa fica isolada e a política rejeita capacidade de rede. O processo Python recebe limites de espaço virtual, CPU, tamanho individual de arquivo e descritores; o supervisor limita tempo de parede. Sem suporte a namespaces, a execução falha fechada, sem fallback para execução no host.

Limitações de isolamento: este protótipo não implementa quota agregada de disco/tmpfs, memória de cgroup, limite agregado de processos nem política seccomp específica. Não deve ser publicado como serviço multiusuário para código hostil. A medição do supervisor no mesmo namespace não é resistente a adulteração por código adversarial. Os ensaios avaliam erros controlados, não evasão deliberada nem exploits de kernel.

## Dados e rotulagem

Benchmarks autorais controlados em 42 famílias. As tarefas têm tamanhos variados e sementes determinísticas. Não são dados observados em produção nem uma amostra representativa de agentes reais.

| Partição | Conteúdo | Amostras |
|---|---|---:|
| Treino | 35 famílias reunidas no dataset final | 2.076 |
| Validação | Cinco famílias reservadas para margens | 100 |
| Teste original | Duas famílias reservadas | 24 |

A comparação entre candidatos foi feita também em 100 tarefas reservadas cujos
registros brutos ficam locais. O resumo das métricas está em
[COMPARACAO_MODELOS.md](COMPARACAO_MODELOS.md).

A atribuição de famílias é fixa antes da coleta. O teste só é gerado e medido após congelar o modelo e as margens. Conhecer a especificação de um experimento futuro não autoriza usar suas medições ou resultados antecipadamente. Variantes de uma família ficam na mesma partição; não há divisão aleatória de linhas quase idênticas.

Cada tarefa tem três execuções de referência com limite amplo de 256 MiB de espaço virtual por processo, 5 s de parede e 3 s de CPU. O alvo é o máximo das três medições de VmPeak e duração, para reduzir subestimação por ruído. VmPeak é amostrado de /proc e pode perder picos muito curtos. RSS vem de wait4/rusage e é registrado, mas não é o alvo do RLIMIT_AS. Espera artificial de 40 ms mantém dados vivos para a amostragem: isso introduz um piso temporal que limita a validade da previsão de tempo.

Capacidades são rótulos autorais dos contratos: ler entrada e escrever saída. Nos programas construídos, a saída esperada é verificada por stdout e hashes dos arquivos. Os rótulos não resultam de revisão humana independente nem de demonstração causal universal de necessidade. A capacidade escrita no relatório é um acesso lógico, não uma Linux capability de privilégio.

## Features e aprendizado supervisionado

Features disponíveis antes da execução: tamanho da entrada, tamanho do código, contagem de nós AST, laços, compreensões, chamadas, imports, chamadas de leitura/escrita, ordenação, JSON, hash, alocação e maior literal numérico. Identificador, família, split, tempo medido e memória medida ficam fora da entrada do modelo. O maior literal é conhecido no código; nos benchmarks de alocação ele torna a demanda especialmente previsível, o que restringe a generalização.

O único modelo ativo é híbrido: Extra Trees estima memória e capacidades, e
Gradient Boosting estima tempo. O classificador e o estimador Extra Trees usam
128 árvores, min_samples_leaf=2, random_state=336 e n_jobs=1. A validação
seleciona as margens; o teste não é usado para ajuste.

Margens candidatas: memória em {1,10; 1,35; 1,70; 2,10} e tempo em {1,5; 2,0; 3,0}. A recomendação adiciona 4 MiB e 80 ms e impõe mínimos de 24 MiB e 200 ms. A validação seleciona a maior cobertura conjunta de memória/tempo, privilegiando cobertura de pelo menos 95% quando possível e, nos empates, o menor orçamento de memória e a menor margem de tempo. Cobertura de medições não garante sucesso na reexecução. A margem escolhida permanece congelada no teste.

O controlador intersecta as capacidades sugeridas com o teto externo. Recursos não finitos ou capacidades desconhecidas são rejeitados. Erros de omissão podem fazer a tarefa falhar; não há escalada automática de permissões nem retentativas ocultas que mudem a comparação.

## Baselines e métricas

Perfil fixo: 128 MiB, 2 s e ambas as capacidades. Heurística: 32 MiB mais 64 vezes o tamanho da entrada em MiB, limitado a 256 MiB; 1 s mais o tamanho da entrada em MiB; leitura/escrita detectadas por chamadas AST. A regra não usa nomes de famílias. Controle de CPU e saída é idêntico entre métodos. Um replay por método/tarefa, com ordem embaralhada deterministicamente; as três execuções de referência não são três repetições da comparação.

Métricas de regressão: MAE do pico de espaço virtual e duração. Classificação: F1 micro, correspondência exata, capacidades omitidas e excedentes. Resultado operacional: código de saída zero, ausência de timeout e igualdade de stdout/hashes de saída com a referência. Relatar sucesso por família, limite médio configurado e duração observada. Intervalos de Wilson são apenas descritivos, pois variantes compartilham família; não há conclusão de significância ou superioridade populacional.

## Reprodutibilidade

Os registros preservam o instante real de observação e hashes dos arquivos. As
partições são definidas por família e por protocolo; os carregadores não usam
calendário ou rótulo de etapa para decidir quais dados podem ser lidos. A
configuração congelada registra os hashes de treino, validação e modelo.

## Fluxograma

![Fluxograma das fases e da separação de dados](figures/fluxograma.png)

As etapas de coleta e a política externa são separadas do fit. O teste só
alimenta a avaliação final.
