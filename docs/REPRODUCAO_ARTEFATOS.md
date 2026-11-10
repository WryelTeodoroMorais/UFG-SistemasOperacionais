# Reprodução dos materiais

O experimento Python não depende de Codex, LLM pago, Node.js ou ferramentas proprietárias. Instale os requisitos e siga EXECUCAO.md. Resultados de memória e tempo variam com hardware, kernel e carga; reproduzir o protocolo não significa obter os mesmos valores ou hashes de modelos retreinados.

Relatórios e PDFs gerados a partir de execuções são saídas locais. Protocolos resumidos, resultados consolidados e fontes dos gráficos usados no relatório permanecem no repositório.

Apresentações e roteiros são materiais locais separados do código versionado. A fonte de slides, quando necessária, usa @oai/artifact-tool do runtime do Codex; essa biblioteca não integra as dependências públicas do projeto.

O modelo e os dados ativos ficam congelados por hash. Uma alteração posterior
à consulta do teste deve ser avaliada em uma nova amostra independente; não
substitua silenciosamente os artefatos desta avaliação.
