# Reprodução do modelo e da avaliação

O projeto não depende de Codex, LLM pago, Node.js ou ferramentas proprietárias.
Instale os requisitos conforme [EXECUCAO.md](EXECUCAO.md). Resultados de tempo e
memória podem variar com hardware, kernel e carga.

O checkout inclui os dados finais, o modelo ativo e a política congelada. Em
uma cópia limpa, verifique Bubblewrap e execute:

```bash
.venv/bin/sentinela doctor
.venv/bin/sentinela evaluate test
```

A avaliação usa as 850 tarefas versionadas em 17 famílias. Ela não precisa
recolher os alvos. O comando executa as três estratégias e grava
`reports/test.json`, sem sobrescrever um relatório existente. O diagnóstico que
fundamenta os resultados deste fechamento está em
`reports/test-modelo-final.json`, local e ignorado pelo Git.

Para repetir em uma raiz temporária com exatamente os dados e o par de modelo do
checkout:

```bash
mkdir -p /tmp/sentinela-final-replay/{data,models}
cp data/{train,validation,test}.jsonl /tmp/sentinela-final-replay/data/
cp models/{model.joblib,frozen.json} /tmp/sentinela-final-replay/models/
PYTHONPATH=src .venv/bin/python -m sentinela.cli \
  --root /tmp/sentinela-final-replay evaluate test
```

O avaliador grava `/tmp/sentinela-final-replay/reports/test.json`. Use outra
raiz para uma nova execução; a duração pode variar entre replays. O relatório
final registra hashes dos três splits, do modelo e da configuração, além da
revisão de origem, ambiente e comando usados.

Os vetores de atributos armazenados nos JSONL podem ser regenerados com
`python scripts/refresh_features.py`. O script reconstrói cada tarefa e confere
semente, hash de código, hash e tamanho da entrada antes de atualizar os
atributos, seus nomes e os metadados de resumo; não recolhe nem recalcula alvos
ou medições.

`models/model.joblib` e `models/frozen.json` formam um par: o segundo registra os
hashes do primeiro, do treino e da validação. O carregador rejeita artefatos
incompatíveis. Para treinar outro candidato, use uma cópia de trabalho nova.
