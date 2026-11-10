"""Relatório de evidência, incluindo resultado negativo para ML."""
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'evolution/fusion'
evaluation=json.loads((BASE/'evaluation.json').read_text())
demo=json.loads((BASE/'demo.json').read_text())
policy=evaluation['policy']
names={'memory':'Sempre memória','blocks':'Sempre blocos','heuristic':'Heurística',
       'fused':'Uma passagem','learned':'ML experimental','auto':'Auto atual','oracle':'Oráculo medido'}
DEMO_METHODS=('memory','blocks','heuristic','fused','auto')
text='''# Ganho real: agregação fundida e verificação da necessidade de ML

O projeto anterior escolhia entre carregar tudo em memória e reler o CSV para cada consulta. Essa referência era fraca: consultas aditivas conhecidas podem compartilhar a leitura, a conversão e a soma de cada linha. A versão atual implementa essa fusão e compara o modelo contra ela.

## Uso prático

Executar várias contagens/somas por limiar em CSVs numéricos, por exemplo, relatórios solicitados por agentes sobre dados tabulares. O operador é conhecido e as implementações têm a mesma saída. A fusão não reescreve qualquer programa ou aplicação automaticamente. A sandbox continua oferecendo execução delimitada; sua cópia de entrada e seus custos de inicialização permanecem na medição.

## Validação e promoção de ML

Um regressor Extra Trees de 128 árvores foi treinado no treino e calibrado na validação para prever RAM e tempo dos três candidatos. A regra, fixada antes do teste, exige pelo menos 5% de redução do tempo em relação a sempre usar fusão, sem mais violações de metas de RSS, em todas as metas 24/64/128 MiB.

| Meta | Tempo ML na validação (s) | Tempo fusão (s) | Ganho relativo ML |
|---|---:|---:|---:|
'''
for target,row in policy['validation'].items():
    text+=f"| {target} MiB | {row['ml_seconds']:.5f} | {row['fused_seconds']:.5f} | {row['relative_gain']*100:.2f}% |\n"
text+=f"\nML promovido: **{policy['ml_enabled']}**. Motivo: {policy['reason']}. Teste utilizado na promoção: {policy['test_used']}.\n"
text+='''
O resultado negativo é preservado: escolher a mesma implementação fundida acrescentou custo de inferência/carga sem benefício. O auto atual, portanto, não usa as árvores nesse caso. O ganho do produto deve ser atribuído à eliminação de trabalho redundante, e não ao modelo supervisionado. O código e os dados da avaliação de ML permanecem entregues e reproduzíveis.

## Teste reservado com configuração congelada

18 tarefas lógicas de seis arquivos novos, com tamanhos distintos dos do treino/validação e três estratégias por tarefa. Cada alternativa teve três repetições, com ordem embaralhada. Todas as estratégias foram verificadas contra um oráculo independente que inclui negativos e valores de fronteira.

| Método | Tempo pareado do lote (s) | Média dos picos RSS (MiB) | Maior pico (MiB) | Meta de 64 MiB atendida |
|---|---:|---:|---:|---:|
'''
for method,row in evaluation['comparison']['64'].items():
    text+=f"| {names[method]} | {row['total_seconds']:.4f} | {row['mean_peak_rss_mb']:.3f} | {row['max_peak_rss_mb']:.3f} | {row['targets_met']}/{row['jobs']} |\n"
text+=f"\nExecuções de referência corretas no teste: {evaluation['correct_reference_executions']}. Reexecução automática: {evaluation['replay_correct']}/{evaluation['replay_jobs']} saídas corretas e {evaluation['replay_targets_met']}/{evaluation['replay_jobs']} metas atendidas. O auto carrega árvores: {evaluation['auto_loads_model_trees']}.\n"
text+='''
Os tempos pareados somam medianas das alternativas medidas e custos de decisão; não são uma única execução completa da CLI. O orçamento externo é igual entre as estratégias. RSS é RAM residente do processo, não apenas concessão de memória virtual. As metas de RSS são objetivos de seleção e verificação, não quotas rígidas de RSS.

## Lote completo: caminho real da CLI

Dois arquivos de 100000 linhas, 8 e 16 colunas, seis consultas por arquivo. Três repetições por método, ordem embaralhada. O tempo inclui amostragem, decisão, cópia, sandbox e exportação; exclui a inicialização do interpretador da CLI. São arquivos já presentes no teste, usados como demonstração sem retreino.

| Método | Mediana do tempo completo (s) | Mediana da média dos picos RSS (MiB) | Maior pico (MiB) | Metas atendidas |
|---|---:|---:|---:|---:|
'''
for method in DEMO_METHODS:
    row=demo['summary'][method]
    text+=f"| {names[method]} | {row['median_end_to_end_seconds']:.4f} | {row['median_mean_peak_rss_mb']:.3f} | {row['max_peak_rss_mb']:.3f} | {row['targets_met']}/{row['jobs']} |\n"
auto=demo['summary']['auto']
text+='\nGanhos do auto atual nesse lote:\n\n'
for baseline in ('memory','blocks','heuristic'):
    row=demo['summary'][baseline]
    time_gain=100*(1-auto['median_end_to_end_seconds']/row['median_end_to_end_seconds'])
    rss_gain=100*(1-auto['median_mean_peak_rss_mb']/row['median_mean_peak_rss_mb'])
    text+=f"- Contra {names[baseline]}: {time_gain:.2f}% menos tempo e {rss_gain:.2f}% menor média de picos RSS.\n"
text+='''

### Seletor antigo removido

No lote de demonstração registrado antes da retirada, o seletor `auto-v1` levou 1,5539 s e teve RSS médio de 32,420 MiB; `auto` levou 0,4789 s e teve 11,619 MiB. O seletor antigo levou cerca de 3,2 vezes o tempo e 2,8 vezes o RSS médio nesse lote. São seis tarefas lógicas em CSVs sintéticos, numa máquina; o resultado justifica removê-lo da CLI para esse operador, sem afirmar desempenho universal.

## Justificativa e conclusão

Há uma justificativa operacional concreta: reduzir leitura, conversão e cálculo repetidos em agregações conhecidas, preservando os resultados e o isolamento. O ganho é medido em tempo e RAM efetivos. Para essa operação, não houve justificativa de produção para ML; a política usa a referência eficiente e evita custo estatístico desnecessário. O estudo supervisionado continua relevante como avaliação comparativa, inclusive por permitir essa conclusão negativa.

Não se deve afirmar inovação do algoritmo de fusão, necessidade universal de IA, otimização de código arbitrário ou economia de energia. O projeto agora oferece uma melhoria real para um operador delimitado, com atribuição correta da causa do ganho. Para justificar ML em outro operador, será necessária nova rodada e novas referências fortes; não bastará comparar com implementações deliberadamente inferiores.

Limitações: dados autorais sintéticos, uma máquina, cache de arquivos aquecido, três repetições e sem teste de significância. Tamanhos novos do mesmo operador não provam generalização a programas novos. O consumo é RSS por processo; não inclui PSS ou RAM total do host. As restrições de isolamento do protótipo permanecem descritas no guia de execução.

O resumo e o protocolo são versionados; os CSVs, replays e JSONs detalhados ficam locais. Guia: ../../docs/FUSAO_E_JUSTIFICATIVA.md.
'''
(BASE/'REPORT.md').write_text(text)
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.build/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
methods=DEMO_METHODS
labels=['Memória','Blocos','Heurística','Uma passagem','Auto atual']
colors=['#96a6b6','#c49642','#657fa3','#327b59','#137d89']
fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
for ax,key,title,unit in ((axes[0],'median_end_to_end_seconds','Lote completo','Segundos'),
                          (axes[1],'median_mean_peak_rss_mb','Média dos picos de RAM','MiB RSS por processo')):
    values=[demo['summary'][method][key] for method in methods]
    bars=ax.bar(labels,values,color=colors)
    ax.bar_label(bars,labels=[f'{v:.2f}' for v in values],padding=4)
    ax.set_ylim(0,max(values)*1.2)
    ax.set_ylabel(unit)
    ax.set_title(title)
    ax.spines[['top','right']].set_visible(False)
fig.suptitle('Mesmo resultado. Auto atual usa uma passagem; ML não foi promovido pela validação.',fontsize=10)
fig.savefig(BASE/'comparison.png',dpi=180)
plt.close(fig)
print(BASE/'REPORT.md')
