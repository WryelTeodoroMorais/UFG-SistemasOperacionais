# Guia técnico do Sentinela ML

Instruções de instalação, execução, reprodução e limites do protótipo.
O [relatório incremental do projeto](../README.md) reúne a motivação, a metodologia,
os resultados e o planejamento das próximas semanas.

Versão descrita: **0.1.0**. [Histórico de alterações](../CHANGELOG.md).
Os comandos deste guia devem ser executados na raiz do repositório.

## Como funciona

O planejador analisa o código Python e o tamanho da entrada. O método
`heuristic` usa regras; `ml` usa uma árvore treinada para memória virtual e
duração; `fixed` fornece a referência de 128 MiB e 2 s. As permissões de
leitura e escrita são identificadas por AST nos métodos heurístico e ML.
A política `authorize()` restringe todos os métodos aos tetos do operador.

O executor usa Bubblewrap, entrada somente leitura em `/input/data.txt`, saída
em `/output` e rede externa isolada. Sem suporte ao isolamento, falha fechada.
As sugestões não garantem conclusão: aliases, chamadas dinâmicas e argumentos
do script podem representar demandas que a análise não reconhece.

## Instalação

Requer Linux, Python 3.11+, Bubblewrap (`bwrap`) e namespaces de usuário e rede
habilitados. Em Debian/Ubuntu, instale o pacote `bubblewrap`. Não execute como root.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps -e .
source .venv/bin/activate
sentinela doctor
```

Os comandos abaixo pressupõem esse ambiente ativado. `sentinela status` mostra
versão, comandos e métodos disponíveis; `sentinela --help` lista as opções.

## Planejar e executar

```bash
sentinela plan examples/uppercase.py --input examples/entrada.txt --allow-write
sentinela run examples/uppercase.py --input examples/entrada.txt --output demo-output
```

O método padrão é `heuristic`; para usar o perfil fixo, acrescente
`--method fixed`. O exemplo exporta `demo-output/result.txt`. Somente arquivos
regulares diretamente em `/output` são exportados; symlinks não são seguidos.
Arquivos existentes nunca são sobrescritos.

Os tetos são `--max-memory-mb`, `--max-wall-seconds`, `--cpu-seconds` e
`--output-mb`. `plan` exige `--allow-write` para autorizar saída;
`run` permite saída por padrão e aceita `--no-write` para bloqueá-la.
Essa opção restringe `/output`; o `/tmp` interno continua disponível.
Se nenhum arquivo for exportado, a pasta de saída não é criada.

### Argumentos e relatórios

```bash
sentinela run examples/text_stats.py --input examples/entrada.txt \
  --output demo-stats --method fixed --arg=--save --report execution-report.json
```

O exemplo conta linhas, palavras e caracteres e exporta `stats.json`.
Repita `--arg` para passar argumentos literalmente em `sys.argv`, sem shell
(máximo de 128 argumentos e 32 kB). Use `--arg=--opcao` para valores com hífen.
Para exibir somente stdout, remova `--arg=--save` e acrescente `--no-write`.

`--report` salva no host o mesmo JSON exibido em stdout, inclusive em falhas do
script e timeout, independentemente de `--no-write`. Todos os destinos JSON
precisam ser novos e suas pastas devem existir. Um relatório existente impede
a execução. Erros que impedem o início da sandbox são exibidos em stderr.
`run` e `security` retornam 0 em sucesso, 1 em falha da tarefa/ensaio e 2 em erro
de ambiente ou argumentos. Os demais comandos retornam 0 quando concluídos e
2 em erro operacional; o argparse usa 2 para erros de sintaxe da CLI.

## ML inicial

O modelo incluído já foi treinado com medições reais:

```bash
sentinela run examples/uppercase.py --input examples/entrada.txt \
  --output demo-ml --method ml --model models/initial-tree.json
```

As mesmas opções `--method ml --model ...` funcionam em `plan`.
O modelo é obrigatório; não há troca automática para heurística.
Para coletar, treinar e avaliar outro modelo:

```bash
sentinela collect --output data/new-measurements.json
sentinela train --data data/new-measurements.json --output models/new-tree.json
sentinela evaluate --data data/new-measurements.json \
  --model models/new-tree.json --output reports/new-replay.json
```

A coleta executa 32 tarefas duas vezes. O treino usa 24 tarefas; a avaliação
compara os três métodos nas outras 8, verificando stdout e arquivos exportados.
No piloto incluído, todos concluíram 8/8. O limite médio foi 128 MiB no fixo,
35 MiB na heurística e 42,25 MiB no ML, sem vantagem sobre a heurística.
São variações dos mesmos quatro tipos de tarefa, sem evidência de funcionamento
em tipos ausentes do treino.

[Protocolo e resultados](ML_INICIAL.md) ·
[Dados](../data/initial-measurements.json) · [Modelo](../models/initial-tree.json) ·
[Reexecução](../reports/initial-replay.json).

## Validação

```bash
python -m pytest -q
SENTINELA_INTEGRATION=1 python -m pytest -q
sentinela security --output security-report.json
```

A primeira execução testa sem namespaces; a segunda inclui a integração real.
`security` executa nove ensaios: tarefa legítima, escrita na entrada, caminho do
host, rede, permissões de entrada/saída, memória, timeout e tamanho de arquivo.
Cada recusa deve apresentar o erro esperado, não apenas uma falha genérica.

## Limites

RLIMIT_AS limita espaço virtual por processo, não RAM física agregada. Também
são aplicados RLIMIT_CPU, RLIMIT_FSIZE, RLIMIT_NOFILE e limite de tempo decorrido.
O protótipo não controla recursos agregados por cgroup nem implementa uma
política seccomp específica. As medições internas podem ser adulteradas por
código adversarial. Os ensaios controlados não certificam proteção contra
escapes ou ataques ao kernel; este protótipo não se destina a executar código
hostil como serviço público.

O código está em `src/`, os testes em `tests/`, os exemplos em `examples/` e os
artefatos experimentais em `data/`, `models/` e `reports/`.

## Leitura das métricas

O [relatório de avaliação](../reports/initial-replay.json) contém uma entrada em
`results` por método e tarefa. O README apresenta a média das oito entradas de
cada método; os picos de memória são calculados por execução antes da média.

| Campo em `execution` | Indicador apresentado | Medição e unidade |
|---|---|---|
| `budget.memory_mb` | Limite médio de memória virtual | Limite autorizado de espaço virtual por processo, em MiB. |
| `wall_seconds` | Tempo decorrido | Intervalo medido pelo supervisor interno, convertido de segundos para ms. Inclui a criação e supervisão do processo filho; não inclui o planejamento nem a preparação completa da sandbox. |
| `cpu_seconds` | Tempo de CPU | Soma de tempo de usuário e de sistema do processo filho, obtida por `wait4` e convertida de segundos para ms. |
| `peak_rss_mb` | Pico médio de RAM | Pico de memória residente do processo filho, obtido de `ru_maxrss`, em MiB. |
| `peak_vms_mb` | Pico médio de memória virtual | Maior `VmPeak` observado por amostragem em `/proc`, em MiB. A amostragem pode perder picos muito curtos. |

Os limites configurados e o consumo observado são medidas diferentes. Nenhum
desses indicadores mede o uso agregado de RAM da sandbox. O piloto tem uma
reexecução por método e tarefa, sem repetições suficientes para concluir
superioridade de desempenho a partir de pequenas diferenças.

## Dados e verificações do piloto

A coleta usa limites de referência de 256 MiB de memória virtual, 5 s de tempo
decorrido, 3 s de CPU e 4 MiB por arquivo de saída. Ela exige um diagnóstico
bem-sucedido pelo `doctor`, medições válidas e saídas iguais nas duas repetições.

Dados externos devem seguir o esquema `sentinela-measurements-v1`, conforme o
[arquivo incluído](../data/initial-measurements.json). O treino recalcula as
características a partir do código e da entrada, recusa tarefas duplicadas e
exige medições bem-sucedidas, finitas e positivas. A validação do formato não
comprova a origem ou a veracidade de medições externas.

A avaliação exige que o SHA-256 dos dados corresponda ao registrado no modelo.
As reexecuções usam ordem embaralhada com semente 336. A correção compara retorno
zero, ausência de timeout, saída do terminal e nomes, tamanhos e hashes SHA-256
dos arquivos. As falhas de tarefas ficam registradas no campo `correct`;
concluir o comando de avaliação não significa que todas as tarefas passaram.

O modelo registra versão do scikit-learn, parâmetros, instante de treino e
SHA-256 dos dados. Seu carregamento valida o esquema e a árvore, rejeitando
valores não finitos e referências cíclicas.
