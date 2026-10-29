"""Gera o guia em PDF (PT-BR) do repositório e da automação mensal. Uso: python docs/pt-BR/build_guide.py"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from briefs.style import C, mono
OUT = os.path.dirname(os.path.abspath(__file__))

CSS = f"""
@page {{ size: A4; margin: 14mm 15mm 16mm; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; background: #FFFFFF; }}
body {{ font-family: 'IBM Plex Sans', Arial, sans-serif; color: {C['ink']}; font-size: 9.2pt; line-height: 1.55; -webkit-print-color-adjust: exact; }}
.cover {{ height: 265mm; display: flex; flex-direction: column; background: {C['forest900']}; color: {C['page']}; border-radius: 1.2mm; padding: 16mm 14mm; position: relative; overflow: hidden; page-break-after: always; }}
.cover .grid {{ position: absolute; inset: 0; background-image: linear-gradient(rgba(185,232,207,.06) 1px, transparent 1px), linear-gradient(90deg, rgba(185,232,207,.06) 1px, transparent 1px); background-size: 8mm 8mm; }}
.cover > * {{ position: relative; }}
.eyebrow {{ font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 7.5pt; letter-spacing: .08em; text-transform: uppercase; color: {C['sage300']}; display: flex; gap: 2mm; align-items: center; }}
.node {{ width: 1.8mm; height: 1.8mm; background: {C['signal']}; display: inline-block; }}
.cover h1 {{ font-size: 30pt; line-height: 1.12; font-weight: 500; letter-spacing: -.015em; margin: 8mm 0 5mm; max-width: 150mm; }}
.cover .sub {{ font-size: 11.5pt; line-height: 1.55; color: {C['sage300']}; max-width: 140mm; }}
.cover .meta {{ margin-top: auto; display: grid; grid-template-columns: repeat(3, 1fr); gap: 6mm; border-top: 1px solid {C['forest700']}; padding-top: 5mm; }}
.cover .meta b {{ display: block; font-size: 10.5pt; font-weight: 500; color: {C['page']}; margin-top: 1mm; }}
.cover .brand {{ display: flex; align-items: center; gap: 3mm; margin-top: 8mm; }}
.cover .wm {{ font-family: 'Newsreader', Georgia, serif; font-size: 15pt; }}
.cover .ss {{ font-family: 'IBM Plex Mono', monospace; font-size: 7pt; letter-spacing: .1em; color: {C['sage300']}; border-left: 1px solid {C['forest700']}; padding-left: 3mm; }}
h2 {{ font-size: 15pt; font-weight: 500; letter-spacing: -.01em; margin: 9mm 0 3mm; padding-top: 2.5mm; border-top: 1.5px solid {C['forest900']}; display: flex; gap: 3.5mm; align-items: baseline; page-break-after: avoid; }}
h2 .no {{ font-family: 'IBM Plex Mono', monospace; font-size: 8pt; letter-spacing: .08em; color: {C['ink3']}; }}
h2.first {{ margin-top: 0; }}
h3 {{ font-size: 10.5pt; font-weight: 500; margin: 5mm 0 1.5mm; page-break-after: avoid; }}
p {{ margin: 0 0 2.4mm; }}
ul, ol {{ margin: 0 0 2.6mm; padding-left: 5mm; }} li {{ margin-bottom: 1.1mm; }}
code, .mono {{ font-family: 'IBM Plex Mono', monospace; font-size: 8pt; background: {C['sunken']}; padding: .2mm 1mm; border-radius: .6mm; }}
pre {{ font-family: 'IBM Plex Mono', monospace; font-size: 7.6pt; line-height: 1.5; background: {C['forest900']}; color: {C['page']}; padding: 3.5mm 4mm; border-radius: 1.1mm; margin: 0 0 3mm; white-space: pre-wrap; page-break-inside: avoid; }}
pre .c {{ color: {C['sage500']}; }}
table {{ width: 100%; border-collapse: collapse; font-size: 8.2pt; margin: 0 0 3.5mm; page-break-inside: avoid; }}
th {{ font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 6.8pt; letter-spacing: .08em; text-transform: uppercase; color: {C['ink3']}; text-align: left; padding: 1.4mm 2mm; background: {C['sunken']}; border-bottom: 1px solid {C['border']}; }}
td {{ padding: 1.5mm 2mm; border-bottom: 1px solid {C['border_subtle']}; vertical-align: top; }}
.box {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 1.1mm; padding: 3.5mm 4mm; margin: 0 0 3.5mm; page-break-inside: avoid; }}
.box.acc {{ background: {C['accent']}; border-color: {C['sage300']}; }}
.box.warn {{ background: {C['warn_bg']}; border-color: #E6D2A8; }}
.box .t {{ font-family: 'IBM Plex Mono', monospace; font-size: 6.8pt; letter-spacing: .08em; text-transform: uppercase; color: {C['forest700']}; margin-bottom: 1.2mm; }}
.box.warn .t {{ color: {C['warn']}; }}
.flow {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 2mm; margin: 2mm 0 4mm; }}
.flow div {{ background: {C['card']}; border: 1px solid {C['border']}; border-top: 2px solid {C['forest700']}; border-radius: 1.1mm; padding: 2.4mm; font-size: 7.8pt; line-height: 1.4; }}
.flow b {{ display: block; font-family: 'IBM Plex Mono', monospace; font-size: 6.6pt; letter-spacing: .08em; color: {C['ink3']}; font-weight: 500; margin-bottom: .8mm; }}
.chk li {{ list-style: none; position: relative; padding-left: 1mm; }}
.chk li::before {{ content: ''; position: absolute; left: -4.5mm; top: 1.3mm; width: 2.6mm; height: 2.6mm; border: 1.2px solid {C['forest700']}; border-radius: .4mm; }}
.chk {{ padding-left: 5.5mm; }}
.pb {{ page-break-before: always; }}
.endnote {{ margin-top: 8mm; border-top: 1px solid {C['border']}; padding-top: 3mm; font-size: 7.6pt; color: {C['ink3']}; display: flex; gap: 4mm; align-items: center; }}
"""

def sec(n, t, first=False):
    return f'<h2 class="{"first pb" if first else ""}"><span class="no">{n:02d}</span>{t}</h2>'

body = f"""
<section class="cover"><div class="grid"></div>
<div class="eyebrow"><span class="node"></span>Guia de processo · Portfólio Stephany Alves</div>
<h1>Procurement Market Briefs: do repositório à edição mensal automática</h1>
<div class="sub">Como o repositório funciona, como os três one-pagers passaram a ser gerados em inglês e português a partir dos dados, como a base sintética avança sem reescrever o passado e como o GitHub Actions publica uma edição nova todo dia 16.</div>
<div class="meta">
<div><div class="eyebrow">Versão</div><b>29 out 2026</b></div>
<div><div class="eyebrow">Ferramentas</div><b>Python · Playwright · GitHub Actions</b></div>
<div><div class="eyebrow">Saídas por edição</div><b>3 briefs × EN e PT = 6 PDFs</b></div></div>
<div class="brand">{mono(30, C['page'])}<span class="wm">Stephany Alves</span><span class="ss">SIGNAL &amp; STRUCTURE</span></div>
</section>

{sec(1, "O que mudou em relação aos one-pagers manuais", True)}
<p>Os one-pagers da edição de 29/10 foram montados com textos escritos para aquele mês. Para rodar sozinho todo mês, cada parte da página precisou passar a depender só dos dados.</p>
<table><tr><th>Aspecto</th><th>Antes (edição manual)</th><th>Agora (repositório)</th></tr>
<tr><td>Textos</td><td>Manchete, destaques e ações escritos à mão</td><td>Gerados por regras: a frase muda quando o indicador muda de direção</td></tr>
<tr><td>Idiomas</td><td>Só inglês</td><td>Inglês e português, cada um com formatação própria de números e datas</td></tr>
<tr><td>Base sintética</td><td>Script de extensão feito para outubro</td><td>Extensão genérica para qualquer data de corte, sem alterar registros antigos</td></tr>
<tr><td>Câmbio</td><td>Evento de 26/10 descrito à mão</td><td>Detecção automática de movimento de 2% ou mais num pregão; o motivo só entra se for escrito em <code>config/context.json</code></td></tr>
<tr><td>Ajuste ao A4</td><td>Corte manual de texto</td><td>Quatro níveis de compactação aplicados até a página caber</td></tr>
<tr><td>Execução</td><td>No ambiente do Claude</td><td>GitHub Actions no dia 16 de cada mês, com commit da edição</td></tr></table>
<div class="box acc"><div class="t">Regras mantidas</div>
<ul style="margin:0"><li>Nenhum dado de empregador; dados sintéticos identificados na página e no rodapé.</li>
<li>Contexto político só como fato e data, e só quando escrito por você no <code>context.json</code>.</li>
<li>Textos sem travessões; números sempre calculados, nunca digitados.</li></ul></div>

<h3>Estrutura do repositório</h3>
<pre>procurement-market-briefs/
  run_edition.py              <span class="c"># orquestra coleta, base sintética e as 6 montagens</span>
  briefs/aerospace.py  procurement.py  ev.py
  briefs/common.py            <span class="c"># idiomas, formatação de números, países, evento cambial</span>
  briefs/style.py             <span class="c"># design system, renderização A4 e ajuste automático</span>
  pipeline/fetch_public.py    <span class="c"># BCB, BLS e Comex Stat</span>
  pipeline/synthetic.py       <span class="c"># estende a base sintética e exporta a visão do comprador</span>
  pipeline/init_truth.py      <span class="c"># reconstrução única da "verdade" da base (já executada)</span>
  data/public/  data/synthetic/  data/synthetic/_truth/
  config/context.json         <span class="c"># contexto opcional escrito por você para uma edição</span>
  editions/AAAA-MM-DD/en/  editions/AAAA-MM-DD/pt/
  .github/workflows/monthly-briefs.yml
  docs/pt-BR/                 <span class="c"># este guia</span></pre>

{sec(2, "Etapa 1: coleta dos dados públicos")}
<p><code>pipeline/fetch_public.py</code> baixa as três fontes e atualiza <code>data/public/</code>. Cada fonte falha de forma isolada: se uma API estiver fora do ar, o arquivo anterior é mantido, o problema entra nos avisos da edição e o resto continua.</p>
<table><tr><th>Fonte</th><th>O que baixa</th><th>Quando atualiza</th><th>Cuidados</th></tr>
<tr><td><b>Banco Central (SGS)</b></td><td>PTAX diária de venda do dólar (série 1) e do euro (21619), IPCA (433), de 2019 até a data da edição</td><td>Diariamente</td><td>Baixa ano a ano porque janelas longas dão erro</td></tr>
<tr><td><b>BLS (PPI dos EUA)</b></td><td>Aviônica, peças aeronáuticas, motores, aço e WPU102505, últimos três anos</td><td>Por volta da metade do mês seguinte</td><td>Sem chave, o limite diário é baixo e compartilhado. Cadastre a chave gratuita e salve como secret <code>BLS_API_KEY</code>. O BLS revisa os quatro últimos meses; o script aceita as revisões</td></tr>
<tr><td><b>Comex Stat (MDIC)</b></td><td>8807 e 8411 por país (quatro anos) e 8703, 8708 e 8507 por NCM e país (ano corrente)</td><td>No início do mês seguinte</td><td>Limite de requisições: pausa de 22 s e novas tentativas. O download leva de 10 a 30 minutos</td></tr></table>
<div class="box warn"><div class="t">Risco a acompanhar na primeira execução</div>Algumas APIs do governo brasileiro recusam acesso de servidores fora do país. Os servidores do GitHub ficam nos EUA. Não consegui testar isso daqui (confiança média de que funciona). Se o Comex Stat ou o BCB falharem no GitHub, a edição sai com os dados anteriores e um aviso. A solução é rodar a coleta no seu computador e enviar os arquivos (seção 8).</div>

{sec(3, "Etapa 2: a base sintética que avança sem reescrever o passado")}
<p>O relatório mensal usa uma compradora fictícia. O problema de estender uma base assim é que um pedido emitido hoje ainda não tem data de recebimento, e uma nota de qualidade aberta ainda não tem data de encerramento. O gerador sabe essas datas futuras, mas a planilha que um comprador vê não pode mostrá-las.</p>
<h3>Verdade e visão</h3>
<ul><li><b>Verdade</b> (<code>data/synthetic/_truth/</code>): todos os registros com as datas reais futuras (<code>receb_real</code>, <code>fech_real</code>).</li>
<li><b>Visão</b> (<code>data/synthetic/*.csv</code>): o que existe na data de corte. Pedido com recebimento real depois do corte aparece em aberto; nota com encerramento depois do corte aparece como Aberta.</li></ul>
<h3>Como foi montada</h3>
<ol><li><code>init_truth.py</code> rodou uma única vez: repetiu o gerador original (semente 42) e a extensão de outubro (semente 20261029) e recuperou as datas futuras.</li>
<li>Antes de gravar, conferiu linha a linha que a repetição reproduz as tabelas publicadas em 29/10. Resultado: 11.676 pedidos e 426 notas idênticos.</li>
<li>A visão gerada para 28/10 a partir da verdade também foi conferida contra os arquivos publicados: zero linhas diferentes.</li></ol>
<h3>Como avança todo mês</h3>
<ol><li><code>synthetic.extend(data)</code> gera apenas os dias depois do último gerado, mês a mês, com semente derivada das datas do trecho. Rodar de novo para a mesma data não muda nada.</li>
<li>Pedidos seguem as mesmas regras do gerador: preço indexado ao último PPI publicado da categoria, câmbio pela PTAX média do mês, prazo e atraso pelo perfil de cada fornecedor.</li>
<li>Notas de qualidade nascem dos recebimentos reais do trecho; RFQs seguem o ritmo médio original.</li>
<li>Metas do mês repetem a última meta cadastrada. Para mudar uma meta, edite <code>metas_mensais.csv</code>.</li>
<li><code>synthetic.export(data)</code> grava a visão em <code>data/synthetic/</code>.</li></ol>
<p>Por padrão, o relatório cobre o mês anterior fechado: a edição de 16/11 traz outubro completo. A edição de 29/10 foi um caso especial, parcial de 1 a 28/10.</p>

{sec(4, "Etapa 3: montagem das páginas em dois idiomas")}
<p>Cada brief é uma função <code>build(edição, idioma, pasta)</code>. Os números vêm dos dados e os textos são escolhidos por regras. <code>common.py</code> resolve o idioma: <code>T(lang, en, pt)</code> escolhe a frase, <code>num()</code> e <code>pct()</code> formatam 1,436.0 como 1.436,0 no português, e os nomes de meses e países são traduzidos.</p>
<h3>Regras de texto</h3>
<table><tr><th>Página</th><th>Elemento</th><th>Regra</th></tr>
<tr><td>Aeroespacial</td><td>Manchete</td><td>Sobe ou cai pela variação da 8807 e do PPI; a parte do câmbio depende de evento cambial, da distância para a média do ano anterior e do sentido do movimento</td></tr>
<tr><td>Aeroespacial</td><td>Implicações</td><td>Aviônica com PPI acima ou abaixo de 5%; câmbio com real mais fraco ou mais forte; base de fornecedores pelo líder e pelos dois países que mais ganharam participação; checagem da 8411 só se variar 40% ou mais</td></tr>
<tr><td>Mensal</td><td>Destaques</td><td>Savings no ano e no mês; OTD "piorando" só com queda em todos os meses da janela; PPM "piorou" quando cruza a meta; ciclo de RFQ só quando acima da meta</td></tr>
<tr><td>Mensal</td><td>Ações</td><td>Cobrança das linhas atrasadas, 8D com o fornecedor de maior PPM, pacote padrão de RFQ, revisão dos aumentos aceitos, cada uma só quando o gatilho existe</td></tr>
<tr><td>Veículos elétricos</td><td>Manchete e KPIs</td><td>Crescimento, participação da China e antecipação de maio e junho (só quando o ano já passou de junho); a frase de 2027 muda para "desde janeiro de 2027" a partir de 2027</td></tr></table>
<h3>Evento cambial e contexto</h3>
<p><code>fx_event()</code> procura o maior movimento da PTAX num único pregão nos últimos 30 dias. Se for de 2% ou mais, ele entra no texto e no gráfico com a data. O motivo do movimento nunca é inferido: só aparece se você escrever em <code>config/context.json</code>, com a data da edição como chave.</p>
<pre>&#123; "2026-10-29": &#123; "fx_event_pt": "primeiro dia útil após o segundo turno da eleição presidencial",
                  "footer_pt": "Contexto do câmbio: 26/10/2026 foi o primeiro dia útil após o segundo turno de 25/10.",
                  "fx_event_en": "...", "footer_en": "..." &#125; &#125;</pre>
<h3>Ajuste automático ao A4</h3>
<p><code>render_fit()</code> renderiza a página e mede a altura. Se passar de 1123 px, aplica o próximo de quatro níveis de compactação (espaços, tamanho do lead, cartões) e renderiza de novo. Se nem o último nível couber, a edição sai com aviso para encurtar o texto. O corpo de texto nunca fica abaixo de 7,4 pt.</p>
<h3>Saídas</h3>
<p>Cada edição gera, em <code>editions/AAAA-MM-DD/en</code> e <code>/pt</code>, o HTML, o PDF A4 e uma prévia PNG de cada página, mais <code>manifest.json</code> com manchetes, altura das páginas e avisos. O índice <code>editions/README.md</code> e as prévias do README principal são atualizados juntos.</p>

{sec(5, "Etapa 4: a automação no GitHub Actions")}
<p>O arquivo <code>.github/workflows/monthly-briefs.yml</code> roda no dia 16 de cada mês às 11:23 UTC (8:23 em Brasília). Nessa data o Comex Stat já publicou o mês anterior e o BLS já divulgou o PPI. O GitHub pode atrasar execuções agendadas em alguns minutos.</p>
<table><tr><th>Passo</th><th>O que faz</th></tr>
<tr><td>1. Checkout</td><td>Baixa o repositório no servidor do GitHub</td></tr>
<tr><td>2. Python e Chromium</td><td>Instala Python 3.12, os pacotes de <code>requirements.txt</code> e o navegador do Playwright</td></tr>
<tr><td>3. Fontes</td><td>Instala IBM Plex e Newsreader da pasta <code>fonts/</code>, para o PDF sair na tipografia do design system</td></tr>
<tr><td>4. Edição</td><td>Roda <code>run_edition.py</code> com a chave do BLS vinda do secret</td></tr>
<tr><td>5. Resumo</td><td>Escreve na página da execução as manchetes, a altura das páginas e os avisos</td></tr>
<tr><td>6. Artifact</td><td>Anexa a pasta da edição à execução, para baixar mesmo sem abrir o repositório</td></tr>
<tr><td>7. Commit</td><td>Grava a edição, os dados atualizados e as prévias com o usuário github-actions[bot]</td></tr></table>
<h3>Execução manual</h3>
<p>Na aba Actions, abra "Monthly briefs" e clique em "Run workflow". Os campos permitem escolher a data da edição, a data de corte do relatório mensal e pular a coleta (útil para testar ou refazer uma edição depois de ajustar o <code>context.json</code>).</p>
<div class="box warn"><div class="t">Agendamento pode ser desligado</div>Em repositórios públicos, o GitHub desliga workflows agendados depois de 60 dias sem atividade no repositório. Os commits mensais da própria automação devem contar como atividade (confiança média). Se receber o e-mail de aviso, basta reativar na aba Actions.</div>

{sec(6, "Publicar o repositório no GitHub")}
<p>Faça isso você mesma, depois de revisar o conteúdo. Nenhuma senha ou token precisa passar pelo Claude.</p>
<h3>1. Criar o repositório vazio</h3>
<ol><li>Em github.com, clique em New repository.</li>
<li>Nome: <code>procurement-market-briefs</code>. Visibilidade: Public. Não marque README, .gitignore nem licença (já estão no pacote).</li></ol>
<h3>2. Enviar os arquivos</h3>
<p><b>Opção A, recomendada: Git no computador.</b> Com o Git para Windows instalado, abra o terminal na pasta descompactada:</p>
<pre>git init
git add .
git commit -m "Procurement market briefs, edition 2026-10-29"
git branch -M main
git remote add origin https://github.com/stephanyalves-eng/procurement-market-briefs.git
git push -u origin main</pre>
<p>Na primeira vez, o Git abre a janela de login do GitHub no navegador. Use o login normal.</p>
<p><b>Opção B: pelo navegador.</b> Na página do repositório vazio, clique em "uploading an existing file" e arraste todo o conteúdo da pasta descompactada, incluindo a pasta <code>.github</code>. São cerca de 70 arquivos, abaixo do limite de 100 por envio. Confira depois se <code>.github/workflows/monthly-briefs.yml</code> apareceu; se não, crie esse arquivo pelo botão Add file e cole o conteúdo.</p>
<h3>3. Configurar a automação</h3>
<ol><li><b>Permissões:</b> Settings, Actions, General. Em "Workflow permissions", marque "Read and write permissions" e salve.</li>
<li><b>Chave do BLS:</b> cadastre-se em data.bls.gov/registrationEngine e receba a chave por e-mail. No GitHub: Settings, Secrets and variables, Actions, New repository secret. Nome <code>BLS_API_KEY</code>, valor a chave.</li>
<li><b>Teste:</b> Actions, Monthly briefs, Run workflow, com "skip fetch" marcado. Deve terminar em poucos minutos e mostrar as manchetes no resumo.</li>
<li><b>Teste completo:</b> rode de novo sem "skip fetch". Confira no resumo se aparecem avisos de coleta.</li>
<li><b>Perfil:</b> fixe o repositório no perfil (Customize your pins) e acrescente em "Selected work" no README do perfil.</li></ol>

{sec(7, "Rotina mensal depois que a edição sai")}
<ol><li>Você recebe a notificação da execução do GitHub. Abra o resumo e leia as manchetes e os avisos.</li>
<li>Abra os seis PDFs (pasta da edição ou artifact). Confira se cada frase faz sentido para o mês: as regras cobrem os casos comuns, mas um mês atípico pode pedir ajuste.</li>
<li>Se houve evento cambial forte, decida se o motivo deve aparecer. Se sim, escreva no <code>config/context.json</code> com a data da edição e rode de novo com "skip fetch".</li>
<li>Se uma página saiu com aviso de overflow, encurte a frase correspondente no módulo do brief.</li>
<li>Publique no LinkedIn usando o PDF do idioma do perfil.</li></ol>

{sec(8, "Problemas comuns")}
<table><tr><th>Sintoma</th><th>Causa provável</th><th>Solução</th></tr>
<tr><td>Aviso "fetch failed: comex"</td><td>Limite de requisições ou bloqueio a servidores fora do Brasil</td><td>Rodar <code>python pipeline/fetch_public.py comex</code> no seu computador, fazer commit de <code>data/public</code> e rodar o workflow com "skip fetch"</td></tr>
<tr><td>Aviso "fetch failed: bls"</td><td>Sem chave ou chave errada</td><td>Conferir o secret <code>BLS_API_KEY</code></td></tr>
<tr><td>PDF com fonte diferente</td><td>Fontes não instaladas</td><td>No computador, instalar as fontes da pasta <code>fonts/</code>; no GitHub, o passo 3 já faz isso</td></tr>
<tr><td>Commit falhou com erro 403</td><td>Workflow sem permissão de escrita</td><td>Settings, Actions, General, "Read and write permissions"</td></tr>
<tr><td>Página com aviso de overflow</td><td>Texto do mês mais longo que o espaço</td><td>Encurtar a frase no módulo do brief e rodar com "skip fetch"</td></tr>
<tr><td>Workflow agendado parou</td><td>60 dias sem atividade</td><td>Reativar na aba Actions</td></tr></table>

{sec(9, "Checklist antes de postar uma edição")}
<ul class="chk">
<li>Resumo da execução sem avisos de coleta, ou avisos entendidos e aceitáveis.</li>
<li>Rodapé de cada página com o mês certo de cada fonte.</li>
<li>Manchete coerente com os KPIs da mesma página.</li>
<li>Versões EN e PT com os mesmos números.</li>
<li>Nenhum motivo de evento sem estar no <code>context.json</code>; nenhum nome de candidato.</li>
<li>Relatório mensal com o selo de dados sintéticos visível.</li>
<li>Você consegue explicar de cabeça cada número que vai citar no post.</li></ul>
<div class="endnote">{mono(16)}<span>Stephany Alves · Procurement Market Briefs · guia do repositório e da automação, 29/10/2026.</span></div>
"""

html = f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Guia do repositório e da automação</title><style>{CSS}</style></head><body>{body}</body></html>'
open(os.path.join(OUT, "guia_repositorio_automacao.html"), "w").write(html)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.goto("file://" + os.path.join(OUT, "guia_repositorio_automacao.html")); pg.wait_for_timeout(400)
    pg.pdf(path=os.path.join(OUT, "Guia_Repositorio_e_Automacao_Procurement_Market_Briefs.pdf"), format="A4", print_background=True,
           display_header_footer=True, header_template="<span></span>",
           footer_template='<div style="width:100%;font-family:IBM Plex Mono,monospace;font-size:7px;letter-spacing:.08em;color:#5E6561;padding:0 15mm;display:flex;justify-content:space-between"><span>PROCUREMENT MARKET BRIEFS · GUIA DO REPOSITÓRIO E DA AUTOMAÇÃO</span><span><span class="pageNumber"></span>/<span class="totalPages"></span></span></div>',
           margin={"top": "14mm", "bottom": "16mm", "left": "15mm", "right": "15mm"})
    b.close()
os.remove(os.path.join(OUT, "guia_repositorio_automacao.html"))
print("ok")
