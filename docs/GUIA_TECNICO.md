# Guia técnico

Este guia descreve a arquitetura e os comandos da versão atual. Para instalar o
ambiente e executar a demonstração, consulte [Instalação e execução](EXECUCAO.md).
Os comandos devem ser executados na raiz do repositório.

## Entradas do projeto

O pacote instalado é `sentinela`, declarado em `pyproject.toml`, com entrada em
`src/sentinela/cli.py`. A opção global `--root CAMINHO`, quando necessária, deve
vir antes do subcomando; sem ela, o diretório atual é usado. Consulte a sintaxe
com:

```bash
.venv/bin/sentinela --help
.venv/bin/sentinela SUBCOMANDO --help
```

| Comando | Função |
|---|---|
| `doctor` | Verifica se o Bubblewrap e os namespaces necessários funcionam. |
| `run SCRIPT --output PASTA` | Executa um script Python isolado com `fixed`, `heuristic` ou `supervised`. Pode receber `--input ARQUIVO`. |
| `collect DIVISAO` | Mede o conjunto completo `train`, `validation` ou `test`. |
| `collect test --append` | Acrescenta tarefas ausentes e preserva as existentes. |
| `train` | Ajusta o modelo híbrido ativo e grava sua configuração congelada usando a validação. |
| `evaluate DIVISAO` | Avalia `validation` ou `test` quando os dados e o modelo necessários estão disponíveis. |
| `security` | Executa os ensaios funcionais de contenção. |

Exemplo de uso do modelo distribuído:

```bash
.venv/bin/sentinela doctor
.venv/bin/sentinela run examples/analisar.py \
  --input examples/entrada.csv --output demo-output --method supervised
```

O comando `run` executa scripts Python. Eles podem processar entradas CSV,
JSONL ou outros formatos implementados pelo próprio script.

## Fluxo de execução

Para `run`, o projeto extrai características do código e da entrada, o modelo
recomenda recursos e capacidades, e `authorize()` limita a recomendação ao teto
definido pelo operador. O sandbox aplica os limites e disponibiliza entrada
somente para leitura, saída controlada e rede isolada. A recomendação do modelo
não pode conceder permissões além desse teto.

Detalhes das partições, features e avaliação estão em
[Metodologia](METODOLOGIA.md); as métricas finais estão em
[Comparação de modelos](COMPARACAO_MODELOS.md).

## Artefatos congelados

`models/model.joblib` contém o modelo de recursos carregado por
`run --method supervised`; `models/frozen.json` registra as margens e hashes que
validam o par. Parâmetros e critérios de seleção do modelo estão em
[Metodologia](METODOLOGIA.md).

## Organização do código

- `src/sentinela/`: pacote ativo e único caminho de execução da CLI, sandbox,
  política e modelo.
- `data/` e `models/`: dados medidos, modelo e configuração ativos.
- `scripts/`: coleta, treinamento, avaliação e reprodução do experimento.
- `tests/`: verificações da implementação ativa.
