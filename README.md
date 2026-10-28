# Sentinela ML

Projeto da equipe **Futhienas** para a disciplina INF0336 — Sistemas Operacionais.

## Equipe

| Participante | Matrícula |
|---|---:|
| Wender Viana Faria Santos | 202401832 |
| William Félix Ferreira Alves da Silva | 202405859 |
| Wryel Teodoro de Morais | 202405860 |
| Lourenço Tabosa Paniago | 202401799 |

## Objetivo

O Sentinela ML recomenda limites de execução e permissões de entrada e saída para scripts Python. Uma política determinística restringe cada recomendação aos tetos definidos pelo operador. A versão atual inclui um planejador heurístico e um executor local isolado com Bubblewrap.

## Como funciona

1. O planejador examina a sintaxe Python (AST), o tamanho do código e, quando fornecido, o tamanho do arquivo de entrada.
2. A regra heurística sugere limites de memória e tempo e indica se detectou operações de leitura e escrita.
3. `authorize()` valida a sugestão e limita recursos e permissões ao teto do operador.
4. O executor roda o script em Bubblewrap, com rede isolada, entrada somente leitura, diretório de saída separado e limites de recursos por processo.

As sugestões são uma referência inicial, não uma previsão treinada nem uma garantia de que um script terminará. Use `--method fixed` para comparar com um perfil fixo.

A análise AST é estática: pode não reconhecer chamadas por aliases, execução dinâmica ou wrappers. Revise a recomendação e use o perfil fixo quando a tarefa depender de uma permissão que a heurística não detectou.

## Funcionalidades

- `status`: mostra versão e comandos disponíveis.
- `doctor`: verifica Bubblewrap e executa uma pequena prova do isolamento.
- `plan`: analisa um script e imprime sinais estáticos, sugestão e orçamento autorizado em JSON.
- `run`: executa o script isolado e devolve métricas, saída padrão e hashes dos arquivos exportados.
- Política fail-closed para valores inválidos, permissões desconhecidas e recomendações acima do teto externo.

## Instalação

Requer Linux, Python 3.11 ou superior, Bubblewrap (`bwrap`) e namespaces de usuário e rede habilitados. Em Debian/Ubuntu, instale o pacote `bubblewrap`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps -e .
```

A execução falha fechada se Bubblewrap ou os namespaces necessários não estiverem disponíveis. Não execute como root nem desative o isolamento para contornar uma falha do `doctor`.

## Verificar o ambiente

Exibir a versão e os comandos disponíveis:

```bash
.venv/bin/sentinela status
```

Testar Bubblewrap e os namespaces necessários:

```bash
.venv/bin/sentinela doctor
```

## Planejar recursos

```bash
.venv/bin/sentinela plan examples/uppercase.py \
  --input examples/entrada.txt --allow-write
```

A resposta JSON inclui as features encontradas, a sugestão heurística e o orçamento depois da política de autorização. Ajuste os tetos com `--max-memory-mb`, `--max-wall-seconds`, `--cpu-seconds` e `--output-mb`.

## Executar um script isolado

```bash
.venv/bin/sentinela run examples/uppercase.py \
  --input examples/entrada.txt --output demo-output --method heuristic
```

Leia o resultado em `demo-output/result.txt`. Use uma pasta de saída nova: o controlador não sobrescreve arquivos existentes. Para comparar com um perfil fixo:

```bash
.venv/bin/sentinela run examples/uppercase.py \
  --input examples/entrada.txt --output demo-fixed --method fixed
```

Scripts executados na sandbox podem ler `/input/data.txt` e escrever em `/output`. Só arquivos regulares diretamente no diretório de saída são exportados; symlinks não são seguidos.

## Testes

```bash
.venv/bin/python -m pytest -q
```

## Estrutura do projeto

```text
src/                 módulos da aplicação: política, análise AST, recomendações e sandbox
examples/            script e entrada para a demonstração
tests/               testes do contrato da política
```

## Limites de segurança

`RLIMIT_AS` restringe espaço virtual por processo, não a memória física agregada. O protótipo não configura quotas agregadas por cgroup, limite total de processos ou seccomp específico e não é uma plataforma para executar código deliberadamente hostil em produção. O `doctor` e a demonstração verificam funcionamento em casos controlados; não certificam segurança contra escapes do kernel ou ataques sofisticados.
