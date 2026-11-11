# Reprodução do modelo e da avaliação

O projeto não depende de Codex, LLM pago, Node.js ou ferramentas proprietárias.
Instale os requisitos conforme [EXECUCAO.md](EXECUCAO.md). Resultados de tempo e
memória podem variar com hardware, kernel e carga.

O clone inclui o dataset final, o modelo ativo e a política congelada. Em uma
cópia limpa, verifique Bubblewrap e execute:

```bash
.venv/bin/sentinela doctor
.venv/bin/sentinela evaluate test
```

A avaliação usa as 850 tarefas versionadas em 17 famílias reservadas. O clone
não precisa coletar novamente os alvos. O comando reproduz as três estratégias
e grava `reports/test.json`; não sobrescreve relatório existente. A execução
que gerou as métricas documentadas está em `reports/test-final.json`, local e
ignorada pelo Git.

Para recriar os dados de uma partição vazia, use `sentinela collect train`,
`sentinela collect validation` ou `sentinela collect test`. Cada workload recebe
três referências em Bubblewrap. `collect test --append` acrescenta apenas IDs
ausentes a uma coleta parcial e não treina o modelo.

`models/model.joblib` e `models/frozen.json` formam um par: o segundo registra os
hashes do primeiro, do treino e da validação. O carregador recusa usar artefatos
cujo conteúdo não corresponda a esses hashes. Para treinar outro candidato, use
um diretório de trabalho separado, preserve o teste final intocado e gere um
novo teste independente após congelar os pesos e as margens.

A apresentação, o roteiro e os relatórios detalhados permanecem locais, fora do
histórico Git.
