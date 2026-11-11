# Instalação e execução

Requisitos: Linux, Python 3.11+ e Bubblewrap com namespaces de usuário e rede habilitados. Em Debian/Ubuntu, o pacote do executor é bubblewrap. Algumas políticas corporativas/containers impedem a criação de namespaces; nesse caso doctor deve falhar. Não execute como root nem desative o isolamento para contornar a falha.

Na raiz do checkout atual:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/sentinela doctor
```

O checkout atual tem uma única entrada de execução: `sentinela`, implementada
em `src/sentinela/cli.py`.

As versões das dependências usadas nas medições estão fixadas em `requirements.txt`. Um modelo joblib deve ser carregado apenas de uma origem confiável: o projeto fornece seu hash no congelamento. Isso não transforma pickle/joblib em um formato seguro para arquivos arbitrários.

## Demonstração com o modelo congelado

```bash
.venv/bin/sentinela run examples/analisar.py --input examples/entrada.csv --output demo-output --method supervised
```

`analisar.py` espera linhas CSV com duas colunas inteiras. `--input examples/entrada.csv` monta o arquivo em `/input/data.txt`; o exemplo soma a segunda coluna, grava `relatorio.json` em `/output` e imprime uma confirmação. `entrada.csv` contém três linhas para demonstração.

O controlador exporta somente arquivos regulares diretamente em `/output`, não segue symlinks e não sobrescreve arquivos existentes no destino. O modelo pode omitir uma capacidade e causar falha; não há ampliação automática. Use `--method fixed` ou `--method heuristic` para comparar. Não se promete suporte a quaisquer scripts externos: bibliotecas disponíveis são as da Python stdlib do host, expostas somente para leitura.

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
SENTINELA_INTEGRATION=1 .venv/bin/python -m pytest -q tests/test_sandbox.py
.venv/bin/sentinela security
```

Os testes de integração requerem permissões de namespaces. A suíte comum os ignora explicitamente para não reportar execução simulada como isolamento real. O comando security executa nove casos controlados e uma verificação de rejeição de capacidade de rede.

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

Não há limite agregado de processos ou memória, seccomp específico ou autenticação multiusuário. Portanto o protótipo avalia contenção funcional de tarefas controladas e integração com ML. Implantação para código deliberadamente hostil exige endurecimento adicional e auditoria.
