# Referências e aplicação no projeto

As fontes fundamentam menor privilégio, isolamento Linux, árvores aleatorizadas e práticas de avaliação supervisionada. A aplicação e os limites de cada referência são descritos abaixo.

1. SALTZER, Jerome H.; SCHROEDER, Michael D. The protection of information in computer systems. Proceedings of the IEEE, v. 63, n. 9, p. 1278-1308, 1975. DOI: 10.1109/PROC.1975.9939. Disponível em: <https://www.cs.virginia.edu/~evans/cs551/saltzer/>.
   **Uso:** menor privilégio, mediação e separação entre recomendação estatística e autorização determinística. O modelo não recebe autoridade para criar novos acessos.

2. GEURTS, Pierre; ERNST, Damien; WEHENKEL, Louis. Extremely randomized trees. Machine Learning, v. 63, p. 3-42, 2006. DOI: 10.1007/s10994-006-6226-1. Disponível em: <https://doi.org/10.1007/s10994-006-6226-1>.
   **Uso:** fundamentação do ensemble Extra Trees para regressão de recursos e classificação multirrótulo de capacidades. O artigo não comprova desempenho neste domínio.

3. PEDREGOSA, Fabian et al. Scikit-learn: machine learning in Python. Journal of Machine Learning Research, v. 12, n. 85, p. 2825-2830, 2011. Disponível em: <https://www.jmlr.org/papers/v12/pedregosa11a.html>.
   **Uso:** implementação dos estimadores supervisionados, métricas e reprodução com semente fixa.

4. CONTAINERS PROJECT. Bubblewrap: low-level unprivileged sandboxing tool. [S. l.]: Containers Project, [s. d.]. Disponível em: <https://github.com/containers/bubblewrap>.
   **Uso:** execução sem privilégios com namespaces, mounts seletivos e rede isolada. A segurança depende da configuração e do kernel; usar Bubblewrap não certifica a aplicação.

5. LINUX MAN-PAGES PROJECT. getrlimit(2): get/set resource limits. [S. l.]: Linux man-pages, [s. d.]. Disponível em: <https://www.man7.org/linux/man-pages/man2/getrlimit.2.html>.
   **Uso:** aplicação de RLIMIT_AS, RLIMIT_CPU, RLIMIT_FSIZE, RLIMIT_NOFILE e desativação de core dumps. AS limita espaço virtual por processo, não memória física agregada.

6. LINUX MAN-PAGES PROJECT. namespaces(7): overview of Linux namespaces. [S. l.]: Linux man-pages, [s. d.]. Disponível em: <https://www.man7.org/linux/man-pages/man7/namespaces.7.html>.
   **Uso:** separação de processos, mounts, rede e outros recursos. Namespace de cgroup não equivale à criação de limites de cgroup.

7. SCIKIT-LEARN DEVELOPERS. Common pitfalls and recommended practices. In: Scikit-learn 1.5.2 documentation. [S. l.], 2024. Disponível em: <https://scikit-learn.org/1.5/common_pitfalls.html>.
   **Uso:** impedir fit em validação/teste e excluir das features informações que só surgem depois da execução. O protocolo também separa famílias de programas.

8. 2026-2-INF0336-OPERATINGSYSTEMS. INF0336: Seminário: modelo de relatório. Repositório assets, 2026. Disponível em: <https://github.com/2026-2-INF0336-OperatingSystems/assets/blob/main/README.md>.
   **Uso:** estrutura dos relatórios incrementais: resumo de até dez orações, introdução, metodologia, fluxograma, resultados, discussão, conclusão e referências. Cópia local: references/INF0336-modelo.md. O repositório consultado não fornece tema gráfico de slides.
