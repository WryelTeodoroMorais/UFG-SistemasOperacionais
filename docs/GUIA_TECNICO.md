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
| `train` | Ajusta o modelo híbrido ativo e grava sua configuração congelada usando a validação. |
| `evaluate DIVISAO` | Avalia `validation` ou `test` quando os dados e o modelo necessários estão disponíveis. |
| `security` | Executa os ensaios funcionais de contenção. |
| `plan-csv ARQUIVOS...` | Mostra a decisão para a operação CSV conhecida sem iniciar o sandbox. |
| `process-csv ARQUIVOS... --output PASTA` | Executa essa operação CSV isolada e mede tempo e RSS. |

Exemplo de uso do modelo distribuído:

```bash
.venv/bin/sentinela doctor
.venv/bin/sentinela run examples/analisar.py \
  --input examples/entrada.csv --output demo-output --method supervised
```

O comando `run` trata scripts Python. Os comandos CSV tratam somente a
agregação numérica documentada em [Fusão e justificativa](FUSAO_E_JUSTIFICATIVA.md).

## Estratégias CSV

A CLI oferece duas estratégias:

- `auto` (padrão): aplica a regra de promoção validada; sem modelo CSV aprovado,
  usa a agregação `fused` em uma passagem.
- `fused`: escolhe explicitamente a mesma agregação de uma passagem.

As implementações `memory`, `blocks` e `heuristic` permanecem como baselines
internas de benchmark, sem opções correspondentes na CLI.

## Fluxo de execução

Para `run`, o projeto extrai características do código e da entrada, o modelo
recomenda recursos e capacidades, e `authorize()` limita a recomendação ao teto
definido pelo operador. O sandbox aplica os limites e disponibiliza entrada
somente para leitura, saída controlada e rede isolada. A recomendação do modelo
não pode conceder permissões além desse teto.

O modelo de recursos de `run` é independente do otimizador da operação CSV.

## Artefatos congelados

`models/model.joblib` contém o modelo de recursos ativo e é carregado por
`run --method supervised`. `models/frozen.json` guarda suas margens e os hashes
do modelo, do treino e da validação; os dois arquivos formam um par, e o
carregador rejeita divergências. `evolution/fusion/frozen.json` pertence à
decisão CSV: documenta por que o ML foi reprovado na validação e `auto` usa
`fused`. Sem esse arquivo, o runtime também cai em `fused`, mas o registro
congelado preserva a evidência da decisão.

## Organização do código

- `src/sentinela/`: pacote ativo e único caminho de execução da CLI, sandbox,
  política, modelo e estratégias CSV.
- `data/` e `models/`: dados medidos, modelo e configuração ativos.
- `evolution/fusion/`: protocolo, configuração congelada e relatório da avaliação
  CSV. Dados brutos e saídas de benchmark ficam locais.
- `scripts/`: reprodução de experimentos e benchmarks. O pacote da fusão inclui
  arquivos rastreados pelo Git e dois CSVs de demonstração; saídas ficam locais.
- `tests/`: verificações da implementação ativa.
