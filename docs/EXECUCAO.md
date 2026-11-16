# Instalação e execução

As medições registradas usam Linux, Python 3.12 e Bubblewrap com namespaces de
usuário e rede habilitados. Em Debian/Ubuntu, instale o pacote `bubblewrap`. Em
ambientes que restringem namespaces, `sentinela doctor` retorna erro.

Instale a versão do checkout ou um wheel gerado. O wheel inclui o modelo
congelado, os conjuntos de treino/validação/teste e os exemplos usados pela
interface:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install .
.venv/bin/sentinela doctor
```

Para instalar o wheel gerado em `dist/`, use:

```bash
.venv/bin/python -m pip install dist/sentinela_ml-0.1.0-py3-none-any.whl
```

O checkout local continua usando `data/` e `models/` da raiz. Fora dele, o
programa usa os recursos incluídos no pacote; arquivos locais fornecidos por
`--root` têm precedência. A entrada de execução é `sentinela`, implementada em
`src/sentinela/cli.py`.

As versões das dependências usadas nas medições estão fixadas em `requirements.txt`. Um modelo joblib deve ser carregado apenas de uma origem confiável: o projeto fornece seu hash no congelamento. Isso não transforma pickle/joblib em um formato seguro para arquivos arbitrários.

## Demonstração com o modelo congelado

```bash
.venv/bin/sentinela run examples/analisar.py --input examples/entrada.csv --output demo-output --method supervised
```

`analisar.py` espera linhas CSV com duas colunas inteiras. `--input examples/entrada.csv` monta o arquivo em `/input/data.txt`; o exemplo soma a segunda coluna, grava `relatorio.json` em `/output` e imprime uma confirmação. `entrada.csv` contém 100 linhas, com valores de 1 a 100 na segunda coluna.

O controlador exporta somente arquivos regulares diretamente em `/output`, não segue symlinks e não sobrescreve arquivos existentes no destino. O modelo pode omitir uma capacidade e causar falha; não há ampliação automática. Use `--method fixed` ou `--method heuristic` para comparar. Não se promete suporte a quaisquer scripts externos: bibliotecas disponíveis são as da Python stdlib do host, expostas somente para leitura.

## Interface web local

Execute `make web` na raiz do repositório e abra
[127.0.0.1:8765](http://127.0.0.1:8765). O servidor escuta no loopback.
Encerre com Ctrl+C. A tela já abre com o script de resumo e o JSONL de validação.

- **Executar Python** oferece exemplos JSONL de treino, validação e teste.
  Você também pode carregar um script e uma entrada próprios; CSV continua
  aceito como entrada para scripts Python. Escolha um método e, para ML, 500,
  1.500 ou 3.300 tarefas de treino.

Os modelos de 500 e 1.500 tarefas usam subconjuntos encaixados e distribuídos
por família do treino versionado. Usam a mesma arquitetura e o mesmo conjunto
de validação do modelo completo. O preparo ocorre no primeiro uso. Para
adiantá-lo, execute `.venv/bin/python -m sentinela.web --prepare-models`.
Os artefatos derivados ficam em `.build/sentinela-web-models/`. A interface
mede cada execução, enquanto a avaliação de 850 tarefas no relatório se refere
ao modelo completo.

## Reproduzir o experimento em uma cópia limpa

O clone já contém o dataset final e o modelo congelado. Para repetir a coleta e o treino em uma cópia limpa, preserve o código e os exemplos, mas comece sem `data/`, `models/` e `reports/`. Execute as fases abaixo; a coleta recusa sobrescrever arquivos existentes:

```bash
.venv/bin/python scripts/run_experiment.py --phase initial
.venv/bin/python scripts/run_experiment.py --phase development
.venv/bin/python scripts/run_experiment.py --phase final
```

O treino usa um único modelo híbrido e a validação escolhe suas margens. Não há etapa separada de seleção nem scripts de expansão por rodada.

## Testes e auditoria

```bash
.venv/bin/python -m pytest -q
make integration
.venv/bin/sentinela security
```

Os testes de integração requerem permissões de namespaces. A suíte comum
marca esses testes como ignorados. `make integration` roda a suíte completa
com integração habilitada. O comando `security` executa nove casos controlados
e uma verificação de rejeição de capacidade de rede.

## Limites efetivos

| Mecanismo | O que faz | O que não demonstra |
|---|---|---|
| Namespace de mounts | Expõe entrada selecionada e bibliotecas | Resistência a exploits do kernel |
| Namespace de rede | Remove conectividade externa do ambiente | Política de domínios ou proxy de rede |
| RLIMIT_AS | Limita espaço virtual por processo | Limite agregado de RSS de vários processos |
| RLIMIT_CPU | Limita segundos de CPU por processo | Cota percentual de CPU/cgroup |
| Timeout externo | Encerra ambiente preso | Progresso semântico de agentes |
| RLIMIT_FSIZE | Limita tamanho de cada arquivo | Quota total de disco/tmpfs |
| Exportação controlada | Evita seguir symlinks e sobrescrever destino | Segurança contra corrida adversarial sofisticada |

O protótipo usa limites por processo e não implementa limites agregados de
processos ou memória, seccomp específico ou autenticação multiusuário. Os
resultados apresentados medem contenção funcional nos workloads controlados
avaliados.
