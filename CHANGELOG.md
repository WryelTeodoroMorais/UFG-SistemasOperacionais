# Histórico de alterações

## 0.1.0

Versão inicial que consolida as duas primeiras semanas:

- Política determinística de recursos e permissões, com rejeição de recomendações inválidas.
- Planejamento heurístico por AST e tamanho da entrada.
- ML inicial para recursos: árvore treinável, coleta real e inferência por JSON.
- Comandos `collect`, `train` e `evaluate`, além de `--method ml --model ...` em `plan` e `run`.
- Piloto com 24 tarefas de treino e 8 reservadas, medições e comparação com fixo e heurística.
- Execução isolada com Bubblewrap e perfis fixo e heurístico.
- Argumentos literais do script via `--arg`, bloqueio de escrita via `--no-write` e relatório de execução via `--report`.
- Comandos `status`, `doctor`, `plan`, `run` e `security`.
- Nove ensaios funcionais de contenção com relatório JSON opcional.
- Testes de integração do executor, exemplos e protocolo do ML inicial.
- Exemplo de contagem de texto com saída em stdout ou arquivo JSON.
