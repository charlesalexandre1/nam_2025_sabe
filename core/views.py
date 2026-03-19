from django.shortcuts import render, get_object_or_404
from django.db.models import Avg, Sum, Count
from django.http import JsonResponse, HttpResponse
from matplotlib.style import context
from urllib3 import request
from .models import *


def dashboard_principal(request):
    anos = DesempenhoEscola.objects.values_list('ano', flat=True).distinct().order_by('-ano')
    disciplinas = Disciplina.objects.all()
    series = Serie.objects.all()
    localidades = Localidade.objects.all()

    ano_selecionado = request.GET.get('ano')
    if not ano_selecionado and anos.exists():
        ano_selecionado = anos.first()

    return render(request, 'dashboard/principal.html', {
        'anos': anos,
        'disciplinas': disciplinas,
        'series': series,
        'localidades': localidades,
        'ano_selecionado': ano_selecionado
    })


def dados_graficos(request):

    ano = request.GET.get('ano')
    disciplina = request.GET.get('disciplina')
    serie = request.GET.get('serie')
    localidade = request.GET.get('localidade')

    queryset = DesempenhoEscola.objects.select_related(
        'escola', 'disciplina', 'serie', 'escola__localidade'
    )

    if ano:
        queryset = queryset.filter(ano=ano)
    if disciplina:
        queryset = queryset.filter(disciplina_id=disciplina)
    if serie:
        queryset = queryset.filter(serie_id=serie)
    if localidade:
        queryset = queryset.filter(escola__localidade_id=localidade)

    if not queryset.exists():
        return JsonResponse({
            'municipio': {'media_proficiencia': 0, 'media_participacao': 0, 'total_escolas': 0, 'total_alunos': 0},
            'evolucao': [],
            'top_escolas': [],
            'distribuicao': {'abaixo_basico': 0, 'basico': 0, 'adequado': 0, 'avancado': 0},
            'localidades': []
        })

    municipio = queryset.aggregate(
        media_proficiencia=Avg('proficiencia_media'),
        media_participacao=Avg('taxa_participacao'),
        total_escolas=Count('escola', distinct=True),
        total_alunos=Sum('alunos_avaliados')
    )

    anos = DesempenhoEscola.objects.values_list('ano', flat=True).distinct().order_by('-ano')[:5]
    anos = sorted(anos)

    evolucao = []
    for a in anos:
        dados_ano = queryset.filter(ano=a).aggregate(
            media=Avg('proficiencia_media'),
            alunos=Sum('alunos_avaliados')
        )
        evolucao.append({
            'ano': a,
            'proficiencia': float(dados_ano['media'] or 0),
            'alunos': dados_ano['alunos'] or 0
        })

    top_escolas = queryset.values(
        'escola__id', 'escola__nome', 'escola__localidade__nome'
    ).annotate(
        media=Avg('proficiencia_media'),
        alunos=Sum('alunos_avaliados')
    ).order_by('-media')[:10]

    distribuicao = queryset.aggregate(
        abaixo_basico=Avg('abaixo_basico'),
        basico=Avg('basico'),
        adequado=Avg('adequado'),
        avancado=Avg('avancado')
    )

    localidades = []
    if not localidade:
        locais = queryset.values(
            'escola__localidade__nome'
        ).annotate(
            media=Avg('proficiencia_media'),
            escolas=Count('escola', distinct=True)
        ).order_by('-media')[:10]

        localidades = [
            {
                'nome': l['escola__localidade__nome'],
                'media': float(l['media']),
                'escolas': l['escolas']
            }
            for l in locais
        ]

    return JsonResponse({
        'municipio': {
            'media_proficiencia': float(municipio['media_proficiencia'] or 0),
            'media_participacao': float(municipio['media_participacao'] or 0),
            'total_escolas': municipio['total_escolas'],
            'total_alunos': municipio['total_alunos'] or 0,
        },
        'evolucao': evolucao,
        'top_escolas': list(top_escolas),
        'distribuicao': {
            'abaixo_basico': float(distribuicao['abaixo_basico'] or 0),
            'basico': float(distribuicao['basico'] or 0),
            'adequado': float(distribuicao['adequado'] or 0),
            'avancado': float(distribuicao['avancado'] or 0),
        },
        'localidades': localidades
    })


def detalhes_escola(request, escola_id):

    escola = get_object_or_404(Escola, id=escola_id)

    desempenhos = DesempenhoEscola.objects.filter(
        escola=escola
    ).select_related('disciplina', 'serie')

    anos = desempenhos.values_list('ano', flat=True).distinct().order_by('ano')

    dados_por_ano = []
    for ano in anos:
        dados = desempenhos.filter(ano=ano).aggregate(
            prof=Avg('proficiencia_media'),
            part=Avg('taxa_participacao')
        )
        dados_por_ano.append({
            'ano': ano,
            'proficiencia_media': float(dados['prof'] or 0),
            'participacao_media': float(dados['part'] or 0)
        })

    return render(request, 'dashboard/detalhes_escola.html', {
        'escola': escola,
        'desempenhos': desempenhos,
        'dados_por_ano': dados_por_ano
    })

from django.db.models import Avg, Sum, Max

def comparacao_anos(request):

    anos = DesempenhoEscola.objects.values_list('ano', flat=True).distinct().order_by('-ano')

    ano1 = request.GET.get('ano1')
    ano2 = request.GET.get('ano2')

    if not ano1 and len(anos) > 0:
        ano1 = anos[0]

    if not ano2 and len(anos) > 1:
        ano2 = anos[1]

    def calcular_dados(ano):
        qs = DesempenhoEscola.objects.filter(ano=ano)

        media = qs.aggregate(media=Avg('proficiencia_media'))['media'] or 0

        # Conta alunos apenas 1 vez por série (usa MAX ao invés de SUM)
        alunos = qs.values(
            'escola_id', 'serie_id'
        ).annotate(
            total=Max('alunos_avaliados')
        ).aggregate(
            soma=Sum('total')
        )['soma'] or 0

        escolas = qs.values('escola_id').distinct().count()

        return {
            'media': media,
            'alunos': alunos,
            'escolas': escolas
        }

    dados_ano1 = dados_ano2 = variacao = None

    if ano1 and ano2:
        dados_ano1 = calcular_dados(ano1)
        dados_ano2 = calcular_dados(ano2)

        media1 = dados_ano1['media']
        media2 = dados_ano2['media']

        alunos1 = dados_ano1['alunos']
        alunos2 = dados_ano2['alunos']

        variacao = {
            'media': round(((media2 - media1) / media1 * 100), 2) if media1 else 0,
            'alunos': round(((alunos2 - alunos1) / alunos1 * 100), 2) if alunos1 else 0
        }

    return render(request, 'dashboard/comparacao_anos.html', {
        'anos_disponiveis': anos,
        'ano1': ano1,
        'ano2': ano2,
        'dados_ano1': dados_ano1,
        'dados_ano2': dados_ano2,
        'variacao': variacao
    })
from django.db.models import Avg
from .models import Escola, Serie, DesempenhoEscola


def comparacao_escolas(request):

    escolas = Escola.objects.all().order_by('nome')
    series = Serie.objects.all().order_by('nome')
    anos = DesempenhoEscola.objects.values_list('ano', flat=True).distinct().order_by('ano')

    escola1_id = request.GET.get('escola1')
    escola2_id = request.GET.get('escola2')
    serie_id = request.GET.get('serie')

    dados = []

    escola1 = Escola.objects.filter(id=escola1_id).first()
    escola2 = Escola.objects.filter(id=escola2_id).first()
    serie = Serie.objects.filter(id=serie_id).first()

    if escola1_id and escola2_id and serie_id:

        for ano in anos:
            d1 = DesempenhoEscola.objects.filter(
                escola_id=escola1_id,
                serie_id=serie_id,
                ano=ano
            ).aggregate(media=Avg('proficiencia_media'))['media'] or 0

            d2 = DesempenhoEscola.objects.filter(
                escola_id=escola2_id,
                serie_id=serie_id,
                ano=ano
            ).aggregate(media=Avg('proficiencia_media'))['media'] or 0

            dados.append({
                'ano': ano,
                'e1': round(d1, 2),
                'e2': round(d2, 2),
                'dif': round(d2 - d1, 2)
            })

    return render(request, 'dashboard/comparativo_escola.html', {
        'escolas': escolas,
        'series': series,
        'anos': anos,
        'dados': dados,
        'escola1': escola1,
        'escola2': escola2,
        'serie': serie,
        'escola1_id': escola1_id,
        'escola2_id': escola2_id,
        'serie_id': serie_id
    })


from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Avg, Sum, Count

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

from .models import Escola, Localidade, Serie, Disciplina, DesempenhoEscola


# ============================================================
# RANKING GERAL
# ============================================================

def ranking_geral(request):

    anos = DesempenhoEscola.objects.values_list('ano', flat=True).distinct().order_by('-ano')
    series = Serie.objects.all()
    disciplinas = Disciplina.objects.all()

    ano = request.GET.get('ano')
    serie = request.GET.get('serie')
    disciplina = request.GET.get('disciplina')

    queryset = DesempenhoEscola.objects.select_related(
        'escola', 'serie', 'disciplina', 'escola__localidade'
    )

    if ano:
        queryset = queryset.filter(ano=ano)
    if serie:
        queryset = queryset.filter(serie_id=serie)
    if disciplina:
        queryset = queryset.filter(disciplina_id=disciplina)

    ranking = queryset.values(
        'escola__id',
        'escola__nome',
        'escola__localidade__nome'
    ).annotate(
        media=Avg('proficiencia_media'),
        alunos=Sum('alunos_avaliados')
    ).order_by('-media')

    return render(request, 'dashboard/ranking_geral.html', {
        'anos': anos,
        'series': series,
        'disciplinas': disciplinas,
        'ranking': ranking,
        'ano': ano,
        'serie': serie,
        'disciplina': disciplina
    })


# ============================================================
# PAINEL POR LOCALIDADE
# ============================================================

def painel_localidade(request):

    anos = DesempenhoEscola.objects.values_list('ano', flat=True).distinct().order_by('-ano')
    series = Serie.objects.all()
    disciplinas = Disciplina.objects.all()

    ano = request.GET.get('ano')
    serie = request.GET.get('serie')
    disciplina = request.GET.get('disciplina')

    queryset = DesempenhoEscola.objects.select_related(
        'escola', 'serie', 'disciplina', 'escola__localidade'
    )

    if ano:
        queryset = queryset.filter(ano=ano)
    if serie:
        queryset = queryset.filter(serie_id=serie)
    if disciplina:
        queryset = queryset.filter(disciplina_id=disciplina)

    localidades = queryset.values(
        'escola__localidade__id',
        'escola__localidade__nome'
    ).annotate(
        media=Avg('proficiencia_media'),
        escolas=Count('escola', distinct=True),
        alunos=Sum('alunos_avaliados')
    ).order_by('-media')

    return render(request, 'dashboard/painel_localidade.html', {
        'anos': anos,
        'series': series,
        'disciplinas': disciplinas,
        'localidades': localidades,
        'ano': ano,
        'serie': serie,
        'disciplina': disciplina
    })


# ============================================================
# RELATÓRIO PDF
# ============================================================

def relatorio_pdf(request):

    queryset = DesempenhoEscola.objects.select_related(
        'escola', 'disciplina', 'serie', 'escola__localidade'
    )

    localidade = request.GET.get('localidade')
    escola = request.GET.get('escola')
    serie = request.GET.get('serie')
    ano_inicio = request.GET.get('ano_inicio')
    ano_fim = request.GET.get('ano_fim')

    if localidade:
        queryset = queryset.filter(escola__localidade_id=int(localidade))

    if escola:
        queryset = queryset.filter(escola_id=int(escola))

    if serie:
        queryset = queryset.filter(serie_id=int(serie))

    if ano_inicio and ano_fim:
        queryset = queryset.filter(ano__range=[int(ano_inicio), int(ano_fim)])

    dados = queryset.values(
        'ano',
        'escola__nome',
        'serie__nome',
        'disciplina__nome'
    ).annotate(
        media=Avg('proficiencia_media'),
        alunos=Sum('alunos_avaliados')
    ).order_by('ano', 'escola__nome', 'serie__nome', 'disciplina__nome')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_sabe.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm
    )

    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("Relatório de Desempenho SABE", styles['Title']))
    elementos.append(Spacer(1, 12))

    tabela = [["Ano", "Escola", "Série", "Disciplina", "Proficiência", "Alunos"]]

    for d in dados:
        tabela.append([
            str(d['ano']),
            d['escola__nome'],
            d['serie__nome'],
            d['disciplina__nome'],
            f"{float(d['media'] or 0):.2f}",
            str(d['alunos'] or 0)
        ])

    tabela_pdf = Table(
        tabela,
        colWidths=[1.5*cm, 6.5*cm, 3*cm, 4*cm, 3*cm, 2.5*cm],
        repeatRows=1
    )

    tabela_pdf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (-2, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
    ]))

    elementos.append(tabela_pdf)
    doc.build(elementos)

    return response


# ============================================================
# ROTA AUXILIAR
# ============================================================

def relatorios(request):
    return relatorio_pdf(request)




# nova pagina inicial

from django.shortcuts import render, get_object_or_404
from .models import Escola, DesempenhoEscola, MetaMunicipal
# Função para calcular o padrão
def calcular_padrao(serie, disciplina, proficiencia):
    if proficiencia is None:
        return "Sem dados"

    # Normaliza a entrada
    serie = str(serie).lower().replace("º", "").strip()  # '5º ano' -> '5 ano'
    disciplina = str(disciplina).upper().strip()  # 'LP', 'MT', etc.

    # Mapeamento de siglas para categorias
    if disciplina in ["LP", "PORT"]:
        disc_cat = "port"
    elif disciplina in ["MT", "MAT"]:
        disc_cat = "mat"
    else:
        return "-"

    # ---------- 2º ANO ----------
    if "2" in serie:
        if proficiencia < 700:
            return "Abaixo do Básico"
        elif proficiencia < 750:
            return "Básico"
        elif proficiencia < 800:
            return "Adequado"
        else:
            return "Avançado"

    # ---------- 5º ANO ----------
    elif "5" in serie:
        if disc_cat == "port":
            if proficiencia <= 150:
                return "Abaixo do Básico"
            elif proficiencia <= 200:
                return "Básico"
            elif proficiencia <= 250:
                return "Adequado"
            else:
                return "Avançado"

        elif disc_cat == "mat":
            if proficiencia <= 175:
                return "Abaixo do Básico"
            elif proficiencia <= 225:
                return "Básico"
            elif proficiencia <= 275:
                return "Adequado"
            else:
                return "Avançado"

    # ---------- 9º ANO ----------
    elif "9" in serie:
        if disc_cat == "port":
            if proficiencia <= 200:
                return "Abaixo do Básico"
            elif proficiencia <= 275:
                return "Básico"
            elif proficiencia <= 325:
                return "Adequado"
            else:
                return "Avançado"

        elif disc_cat == "mat":
            if proficiencia <= 225:
                return "Abaixo do Básico"
            elif proficiencia <= 300:
                return "Básico"
            elif proficiencia <= 350:
                return "Adequado"
            else:
                return "Avançado"

    return "-"

# Função para gerar boletim completo
def gerar_boletim(dados):
    """
    dados: lista de dicionários com as chaves:
        'Ano', 'Série', 'Disciplina', 'Proficiencia', 'Participacao'
    Retorna: lista de dicionários com a coluna 'Padrão' preenchida
    """
    boletim = []
    for linha in dados:
        padrao = calcular_padrao(linha['Série'], linha['Disciplina'], linha['Proficiencia'])
        nova_linha = linha.copy()
        nova_linha['Padrão'] = padrao
        boletim.append(nova_linha)
    return boletim

# --- Exemplo de uso ---
dados_exemplo = [
    {"Ano": 2023, "Série": "2º ano", "Disciplina": "LP", "Proficiencia": 586.0, "Participacao": 0.0},
    {"Ano": 2023, "Série": "2º ano", "Disciplina": "MT", "Proficiencia": 478.0, "Participacao": 0.0},
    {"Ano": 2023, "Série": "5º ano", "Disciplina": "LP", "Proficiencia": 227.0, "Participacao": 0.0},
    {"Ano": 2023, "Série": "5º ano", "Disciplina": "MT", "Proficiencia": 242.0, "Participacao": 0.0},
    {"Ano": 2023, "Série": "9º ano", "Disciplina": "LP", "Proficiencia": 263.0, "Participacao": 0.0},
    {"Ano": 2023, "Série": "9º ano", "Disciplina": "MT", "Proficiencia": 263.0, "Participacao": 0.0},
]

boletim_completo = gerar_boletim(dados_exemplo)

# Exibir resultado
for linha in boletim_completo:
    print(linha)



##########################################
from collections import defaultdict

from django.shortcuts import render, get_object_or_404
from .models import Escola, Serie, Disciplina, DesempenhoEscola

def boletim_escola(request, escola_id):
    escola = get_object_or_404(Escola, id=escola_id)

    series = Serie.objects.all().order_by('nome')
    disciplinas = Disciplina.objects.all().order_by('nome')

    # 🔁 Converte para lista para permitir indexação negativa (anos[-1])
    anos = list(
        DesempenhoEscola.objects
        .filter(escola=escola)
        .values_list('ano', flat=True)
        .distinct()
        .order_by('ano')
    )

    desempenhos = {}
    for d in DesempenhoEscola.objects.filter(escola=escola).select_related('serie', 'disciplina'):
        desempenhos[(d.serie.id, d.disciplina.id, d.ano)] = d

    boletim = []
    distribuicao = []

    for serie in series:
        for disciplina in disciplinas:

            linha = {
                'serie': serie.nome,
                'disciplina': disciplina.nome,
                'anos': []
            }

            linha_dist = {
                'serie': serie.nome,
                'disciplina': disciplina.nome,
                'anos': []
            }

            for ano in anos:
                d = desempenhos.get((serie.id, disciplina.id, ano))

                if d:
                    prof = float(d.proficiencia_media)
                    participacao = float(d.taxa_participacao or 0)

                    ab = float(d.abaixo_basico or 0)
                    ba = float(d.basico or 0)
                    ad = float(d.adequado or 0)
                    av = float(d.avancado or 0)

                    # 🔧 Correção automática apenas para 2023
                    if ano == 2023:
                        if participacao <= 1:
                            participacao *= 100

                        if ab <= 1: ab *= 100
                        if ba <= 1: ba *= 100
                        if ad <= 1: ad *= 100
                        if av <= 1: av *= 100

                    padrao = calcular_padrao(serie.nome, disciplina.nome, prof)

                else:
                    prof = participacao = padrao = None
                    ab = ba = ad = av = None

                linha['anos'].append({
                    'ano': ano,
                    'proficiencia': prof,
                    'participacao': participacao,
                    'padrao': padrao
                })

                linha_dist['anos'].append({
                    'ano': ano,
                    'abaixo_basico': ab,
                    'basico': ba,
                    'adequado': ad,
                    'avancado': av
                })

            boletim.append(linha)
            distribuicao.append(linha_dist)

    # --- GRÁFICO: agregação por disciplina no último ano ---
    ultimo_ano = anos[-1] if anos else None
    grafico_data = {}

    for item in distribuicao:
        disciplina = item['disciplina']
        dados_ano = next((d for d in item['anos'] if d['ano'] == ultimo_ano), None)
        if dados_ano and all(v is not None for v in [dados_ano['abaixo_basico'], dados_ano['basico'], dados_ano['adequado'], dados_ano['avancado']]):
            if disciplina not in grafico_data:
                grafico_data[disciplina] = {
                    'soma_ab': 0,
                    'soma_b': 0,
                    'soma_ad': 0,
                    'soma_av': 0,
                    'count': 0
                }
            grafico_data[disciplina]['soma_ab'] += dados_ano['abaixo_basico']
            grafico_data[disciplina]['soma_b'] += dados_ano['basico']
            grafico_data[disciplina]['soma_ad'] += dados_ano['adequado']
            grafico_data[disciplina]['soma_av'] += dados_ano['avancado']
            grafico_data[disciplina]['count'] += 1

    dados_grafico = []
    for disciplina, valores in grafico_data.items():
        count = valores['count']
        if count > 0:
            dados_grafico.append({
                'disciplina': disciplina,
                'abaixo_basico': round(valores['soma_ab'] / count, 2),
                'basico': round(valores['soma_b'] / count, 2),
                'adequado': round(valores['soma_ad'] / count, 2),
                'avancado': round(valores['soma_av'] / count, 2),
            })

    dados_grafico.sort(key=lambda x: x['disciplina'])
    # ---------------------------------------------------------

    return render(request, 'dashboard/boletim_escola.html', {
        'escola': escola,
        'boletim': boletim,
        'distribuicao': distribuicao,
        'anos': anos,
        'colspan': 2 + (len(anos) * 2),
        'colspan_dist': 2 + (len(anos) * 4),
        'dados_grafico': dados_grafico,
        'ultimo_ano': ultimo_ano,
    })


def boletim_escola_old(request, escola_id): ###### anterior
    escola = get_object_or_404(Escola, id=escola_id)

    series = Serie.objects.all().order_by('nome')
    disciplinas = Disciplina.objects.all().order_by('nome')

    anos = (
        DesempenhoEscola.objects
        .filter(escola=escola)
        .values_list('ano', flat=True)
        .distinct()
        .order_by('ano')
    )

    desempenhos = {}
    for d in DesempenhoEscola.objects.filter(escola=escola).select_related('serie', 'disciplina'):
        desempenhos[(d.serie.id, d.disciplina.id, d.ano)] = d

    boletim = []
    distribuicao = []

    for serie in series:
        for disciplina in disciplinas:

            linha = {
                'serie': serie.nome,
                'disciplina': disciplina.nome,
                'anos': []
            }

            linha_dist = {
                'serie': serie.nome,
                'disciplina': disciplina.nome,
                'anos': []
            }

            for ano in anos:
                d = desempenhos.get((serie.id, disciplina.id, ano))

                if d:
                    prof = float(d.proficiencia_media)
                    participacao = float(d.taxa_participacao or 0)

                    ab = float(d.abaixo_basico or 0)
                    ba = float(d.basico or 0)
                    ad = float(d.adequado or 0)
                    av = float(d.avancado or 0)

                    # 🔧 Correção automática apenas para 2023
                    if ano == 2023:
                        if participacao <= 1:
                            participacao *= 100

                        if ab <= 1: ab *= 100
                        if ba <= 1: ba *= 100
                        if ad <= 1: ad *= 100
                        if av <= 1: av *= 100

                    padrao = calcular_padrao(serie.nome, disciplina.nome, prof)

                else:
                    prof = participacao = padrao = None
                    ab = ba = ad = av = None

                linha['anos'].append({
                    'ano': ano,
                    'proficiencia': prof,
                    'participacao': participacao,
                    'padrao': padrao
                })

                linha_dist['anos'].append({
                    'ano': ano,
                    'abaixo_basico': ab,
                    'basico': ba,
                    'adequado': ad,
                    'avancado': av
                })

            boletim.append(linha)
            distribuicao.append(linha_dist)

    return render(request, 'dashboard/boletim_escola.html', {
        'escola': escola,
        'boletim': boletim,
        'distribuicao': distribuicao,
        'anos': anos,
        'colspan': 2 + (len(anos) * 2),
        'colspan_dist': 2 + (len(anos) * 4),
    })


from django.shortcuts import render, get_object_or_404
from collections import defaultdict
from .models import Escola, DesempenhoEscola


def boletim_escola_sem(request, escola_id):

    escola = get_object_or_404(Escola, id=escola_id)

    resultados = (
        DesempenhoEscola.objects
        .filter(escola=escola)
        .select_related('disciplina', 'serie')
        .order_by('serie__nome', 'disciplina__nome', 'ano')
    )

    anos = list(
        resultados
        .values_list('ano', flat=True)
        .distinct()
        .order_by('ano')
    )

    # =====================================================
    # TABELA 1 — PROFICIÊNCIA + PADRÃO
    # =====================================================

    boletim_dict = defaultdict(lambda: {
        'serie': '',
        'disciplina': '',
        'anos': []
    })

    for r in resultados:
        chave = (r.serie.nome, r.disciplina.nome)

        boletim_dict[chave]['serie'] = r.serie.nome
        boletim_dict[chave]['disciplina'] = r.disciplina.nome

        boletim_dict[chave]['anos'].append({
            'ano': r.ano,
            'proficiencia': r.proficiencia_media,
            'padrao': (
                'Avançado' if r.avancado >= 50 else
                'Adequado' if r.adequado >= 50 else
                'Básico' if r.basico >= 50 else
                'Abaixo do Básico'
            )
        })

    boletim = list(boletim_dict.values())

    # =====================================================
    # TABELA 2 — DISTRIBUIÇÃO PERCENTUAL
    # =====================================================

    distribuicao_dict = defaultdict(lambda: {
        'serie': '',
        'disciplina': '',
        'anos': []
    })

    for r in resultados:
        chave = (r.serie.nome, r.disciplina.nome)

        distribuicao_dict[chave]['serie'] = r.serie.nome
        distribuicao_dict[chave]['disciplina'] = r.disciplina.nome

        distribuicao_dict[chave]['anos'].append({
            'ano': r.ano,
            'abaixo_basico': r.abaixo_basico,
            'basico': r.basico,
            'adequado': r.adequado,
            'avancado': r.avancado,
        })

    distribuicao = list(distribuicao_dict.values())

    colspan = 2 + (len(anos) * 2)
    colspan_dist = 2 + (len(anos) * 4)

    context = {
        'escola': escola,
        'anos': anos,
        'boletim': boletim,
        'distribuicao': distribuicao,
        'colspan': colspan,
        'colspan_dist': colspan_dist,
    }

    return render(request, 'boletim_escola.html', context)



from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .models import Escola, DesempenhoEscola



def boletim_escola_pdf(request, escola_id): #antiga fucnionando
    escola = get_object_or_404(Escola, id=escola_id)

    desempenhos = (
        DesempenhoEscola.objects
        .filter(escola_id=escola.id)
        .select_related('disciplina', 'serie')
        .order_by('ano', 'serie__nome', 'disciplina__nome')
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="boletim_{escola.id}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm
    )

    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("Boletim de Desempenho - SABE", styles['Title']))
    elementos.append(Paragraph(f"Escola: {escola.nome}", styles['Normal']))
    elementos.append(Paragraph(f"INEP: {escola.inep}", styles['Normal']))
    elementos.append(Paragraph(f"Localidade: {escola.localidade}", styles['Normal']))
    elementos.append(Spacer(1, 12))

    tabela = [[
        "Ano", "Série", "Disciplina",
        "Proficiência", "Participação (%)", "Padrão"
    ]]

    for d in desempenhos:
        padrao = classificar_padrao_desempenho(
            d.serie.nome,
            d.disciplina.nome,
            float(d.proficiencia_media)
        )

        tabela.append([
            str(d.ano),
            d.serie.nome,
            d.disciplina.nome,
            f"{float(d.proficiencia_media):.1f}",
            f"{float(d.taxa_participacao or 0):.1f}%",
            padrao
        ])

    tabela_pdf = Table(
        tabela,
        colWidths=[
            1.5*cm, 3*cm, 4.5*cm,
            3*cm, 3.5*cm, 4*cm
        ],
        repeatRows=1
    )

    tabela_pdf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (-3, 1), (-2, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
    ]))

    elementos.append(tabela_pdf)

    doc.build(elementos)

    return response

def selecionar_escola_boletim(request):
    escolas = Escola.objects.all().order_by('nome')
    return render(request, 'dashboard/selecionar_escola_boletim.html', {
        'escolas': escolas
    })

#####$$$$$$$$$$$$$$$$$$$$$$$$$

def classificar_padrao_desempenho(serie, disciplina, proficiencia):
    """
    Classifica o padrão de desempenho conforme tabelas SABE/SAEB.
    """
    serie = serie.lower()
    disciplina = disciplina.lower()

    # ---------- 2º ANO ----------
    if "2" in serie:
        if proficiencia < 700:
            return "Abaixo do Básico"
        elif proficiencia < 750:
            return "Básico"
        elif proficiencia < 800:
            return "Adequado"
        else:
            return "Avançado"

    # ---------- 5º ANO ----------
    if "5" in serie:
        if "port" in disciplina:
            if proficiencia <= 150:
                return "Abaixo do Básico"
            elif proficiencia <= 200:
                return "Básico"
            elif proficiencia <= 250:
                return "Adequado"
            else:
                return "Avançado"

        if "mat" in disciplina:
            if proficiencia <= 175:
                return "Abaixo do Básico"
            elif proficiencia <= 225:
                return "Básico"
            elif proficiencia <= 275:
                return "Adequado"
            else:
                return "Avançado"

    # ---------- 9º ANO ----------
    if "9" in serie:
        if "port" in disciplina:
            if proficiencia <= 200:
                return "Abaixo do Básico"
            elif proficiencia <= 275:
                return "Básico"
            elif proficiencia <= 325:
                return "Adequado"
            else:
                return "Avançado"

        if "mat" in disciplina:
            if proficiencia <= 225:
                return "Abaixo do Básico"
            elif proficiencia <= 300:
                return "Básico"
            elif proficiencia <= 350:
                return "Adequado"
            else:
                return "Avançado"

    return "Não classificado"


##########################################

from django.shortcuts import render
from django.db.models import Sum, Count, Max
from .models import DesempenhoEscola

from django.db.models import Sum, Count
from itertools import groupby
from collections import defaultdict

from django.db.models import Sum, Max
from collections import defaultdict
from django.db.models import Sum, Max
from collections import defaultdict
from django.shortcuts import render
from .models import DesempenhoEscola, Localidade # Certifique-se de que Localidade está importado



def relatorio_escolas_participantes(request):

    queryset = DesempenhoEscola.objects.select_related(
        'escola', 'escola__localidade', 'serie'
    )

    localidade_id = request.GET.get('localidade')
    escola_filtro = request.GET.get('escola')
    ano_inicio = request.GET.get('ano_inicio')
    ano_fim = request.GET.get('ano_fim')

    # ================= FILTROS =================
    if localidade_id:
        try:
            localidade_id = int(localidade_id)
            queryset = queryset.filter(escola__localidade_id=localidade_id)
        except ValueError:
            pass

    if escola_filtro:
        queryset = queryset.filter(escola_id=escola_filtro)

    if ano_inicio and ano_fim:
        queryset = queryset.filter(ano__range=[ano_inicio, ano_fim])
    elif ano_inicio:
        queryset = queryset.filter(ano__gte=ano_inicio)
    elif ano_fim:
        queryset = queryset.filter(ano__lte=ano_fim)

    # ================= AGRUPAMENTO =================
    dados_series = (
        queryset
        .values(
            'ano',
            'escola__id',
            'escola__nome',
            'escola__localidade__nome',
            'serie__id',
            'serie__nome',
        )
        .annotate(
            alunos_serie=Max('alunos_avaliados'),
            previstos_serie=Max('alunos_previstos'),
        )
        .order_by('ano', 'escola__nome', 'serie__nome')
    )

    # ================= ESTRUTURA =================
    escolas_dict = defaultdict(lambda: {
        'ano': '',
        'nome': '',
        'localidade': '',
        'series': [],
        'total_avaliados': 0,
        'total_previstos': 0,
        'percentual_total': 0,  # NOVO
    })

    for d in dados_series:
        chave = (d['ano'], d['escola__id'])

        avaliados = d['alunos_serie'] or 0
        previstos = d['previstos_serie'] or 0

        # ===== Percentual por série =====
        percentual = 0
        if previstos > 0:
            percentual = (avaliados / previstos) * 100

        escolas_dict[chave]['ano'] = d['ano']
        escolas_dict[chave]['nome'] = d['escola__nome']
        escolas_dict[chave]['localidade'] = d['escola__localidade__nome']

        escolas_dict[chave]['series'].append({
            'nome': d['serie__nome'],
            'avaliados': avaliados,
            'previstos': previstos,
            'percentual': percentual,
        })

        escolas_dict[chave]['total_avaliados'] += avaliados
        escolas_dict[chave]['total_previstos'] += previstos

    # ================= TOTAL POR ESCOLA =================
    for escola in escolas_dict.values():
        if escola['total_previstos'] > 0:
            escola['percentual_total'] = (
                escola['total_avaliados'] / escola['total_previstos']
            ) * 100
        else:
            escola['percentual_total'] = 0

    # ================= LISTA FINAL =================
    dados_agrupados = sorted(
        escolas_dict.values(),
        key=lambda x: (x['ano'], x['nome'])
    )

    # ================= FILTROS =================
    localidades = Localidade.objects.all().order_by('nome')

    anos_disponiveis = (
        DesempenhoEscola.objects
        .values_list('ano', flat=True)
        .distinct()
        .order_by('ano')
    )

    # ================= TOTAIS GERAIS =================
    grand_total_avaliados = sum(e['total_avaliados'] for e in dados_agrupados)
    grand_total_previstos = sum(e['total_previstos'] for e in dados_agrupados)
    total_series_count = sum(len(escola['series']) for escola in dados_agrupados)

    # Percentual geral
    percentual_geral = 0
    if grand_total_previstos > 0:
        percentual_geral = (grand_total_avaliados / grand_total_previstos) * 100

    # ================= CONTEXT =================
    return render(request, 'dashboard/relatorio_escolas_participantes.html', {
        'dados': dados_agrupados,
        'localidades': localidades,
        'anos_disponiveis': anos_disponiveis,
        'filtro_localidade': str(localidade_id) if localidade_id else '',
        'filtro_ano_inicio': ano_inicio or '',
        'filtro_ano_fim': ano_fim or '',
        'grand_total_avaliados': grand_total_avaliados,
        'grand_total_previstos': grand_total_previstos,
        'percentual_geral': percentual_geral,  # NOVO
        'total_series_count': total_series_count,
    })


#Panel esfera ( estadual regional municipal) - ranking por localidade
from django.shortcuts import render
from django.db.models import Avg, Sum
from .models import Esfera, Disciplina, Serie, DesempenhoEsfera


# -------------------------------------------------------------------
# Padrões de Desempenho SAEB 2024
# Estrutura: { (nome_disciplina, nome_serie): [ (nivel, li, ls), ... ] }
# li = limite inferior (None = sem limite inferior)
# ls = limite superior (None = sem limite superior)
# -------------------------------------------------------------------
PADROES_SAEB_2024 = {
    # ATENÇÃO: As chaves foram ajustadas para 'LP' e 'MT' e as séries para '2º ano', '5º ano', '9º ano', '3ª série'
    # conforme o debug que você forneceu.

    # Escala 750,50 - 2º ano (LP e MT iguais)
    ('LP', '2º ano'): [ # <-- AJUSTADO AQUI
        ('Abaixo do Básico', None,  699.99),
        ('Básico',           700,   749.99),
        ('Adequado',         750,   799.99),
        ('Avançado',         800,   None),
    ],
    ('MT', '2º ano'): [ # <-- AJUSTADO AQUI
        ('Abaixo do Básico', None,  699.99),
        ('Básico',           700,   749.99),
        ('Adequado',         750,   799.99),
        ('Avançado',         800,   None),
    ],

    # Escala 250,50 - Língua Portuguesa
    ('LP', '5º ano'): [ # <-- AJUSTADO AQUI
        ('Abaixo do Básico', None,  150),
        ('Básico',           151,   200),
        ('Adequado',         201,   250),
        ('Avançado',         251,   None),
    ],
    ('LP', '9º ano'): [ # <-- AJUSTADO AQUI
        ('Abaixo do Básico', None,  200),
        ('Básico',           201,   275),
        ('Adequado',         276,   325),
        ('Avançado',         326,   None),
    ],
    ('LP', '3ª série'): [ # <-- AJUSTADO AQUI
        ('Abaixo do Básico', None,  250),
        ('Básico',           251,   300),
        ('Adequado',         301,   375),
        ('Avançado',         376,   None),
    ],

    # Escala 250,50 - Matemática
    ('MT', '5º ano'): [ # <-- AJUSTADO AQUI
        ('Abaixo do Básico', None,  175),
        ('Básico',           176,   225),
        ('Adequado',         226,   275),
        ('Avançado',         276,   None),
    ],
    ('MT', '9º ano'): [ # <-- AJUSTADO AQUI
        ('Abaixo do Básico', None,  225),
        ('Básico',           226,   300),
        ('Adequado',         301,   350),
        ('Avançado',         351,   None),
    ],
    ('MT', '3ª série'): [ # <-- AJUSTADO AQUI
        ('Abaixo do Básico', None,  275),
        ('Básico',           276,   350),
        ('Adequado',         351,   400),
        ('Avançado',         401,   None),
    ],
}

# Cores associadas a cada nível (útil no template via badge)
CORES_NIVEL = {
    'Abaixo do Básico': 'danger',
    'Básico':           'warning',
    'Adequado':         'info',
    'Avançado':         'success',
}


def classificar_nivel(disciplina_nome, serie_nome, proficiencia):
    """
    Retorna um dict com 'nivel' e 'cor' para o valor de proficiência
    informado, com base nos padrões SAEB 2024.
    Retorna None se não houver padrão cadastrado para a combinação.
    """
    # Os prints de debug podem ser removidos depois que tudo estiver funcionando
    # print(f"\n--- DEBUG CLASSIFICAR NÍVEL ---")
    # print(f"Recebido: Disciplina='{disciplina_nome}', Série='{serie_nome}', Proficiência={proficiencia}")

    if proficiencia is None:
        # print(f"DEBUG: Proficiência é None, retornando None.")
        return None

    # Usaremos os nomes EXATOS que vêm do banco para a busca no dicionário
    # (Removendo .strip() e .title() para usar os nomes brutos do banco, que agora batem com o dicionário)
    disciplina_chave = disciplina_nome.strip()
    serie_chave = serie_nome.strip()

    # print(f"DEBUG: Tentando buscar padrão para a chave: ('{disciplina_chave}', '{serie_chave}')")

    faixas = PADROES_SAEB_2024.get((disciplina_chave, serie_chave))

    if not faixas:
        # print(f"DEBUG: Padrão NÃO encontrado no dicionário para a chave: ('{disciplina_chave}', '{serie_chave}')")
        # print(f"DEBUG: Chaves disponíveis no dicionário PADROES_SAEB_2024: {PADROES_SAEB_2024.keys()}")
        return None

    # print(f"DEBUG: Padrão ENCONTRADO para a chave: ('{disciplina_chave}', '{serie_chave}')")
    # print(f"DEBUG: Faixas para esta combinação: {faixas}")

    for nivel, li, ls in faixas:
        # Verifica se a proficiência está dentro da faixa
        if li is None and ls is not None: # Menor ou igual a LS
            if proficiencia <= ls:
                # print(f"DEBUG: Proficiência {proficiencia} está em '{nivel}' (<= {ls})")
                return {'nivel': nivel, 'cor': CORES_NIVEL.get(nivel, 'secondary')}
        elif li is not None and ls is None: # Maior ou igual a LI
            if proficiencia >= li:
                # print(f"DEBUG: Proficiência {proficiencia} está em '{nivel}' (>= {li})")
                return {'nivel': nivel, 'cor': CORES_NIVEL.get(nivel, 'secondary')}
        elif li is not None and ls is not None: # Entre LI e LS (inclusive)
            if li <= proficiencia <= ls:
                # print(f"DEBUG: Proficiência {proficiencia} está em '{nivel}' ({li} <= x <= {ls})")
                return {'nivel': nivel, 'cor': CORES_NIVEL.get(nivel, 'secondary')}

    # Se a proficiência não se encaixar em nenhuma faixa (ex: fora dos limites definidos)
    # print(f"DEBUG: Proficiência {proficiencia} NÃO se encaixou em NENHUMA faixa para Disciplina='{disciplina_chave}', Série='{serie_chave}'")
    return None


def painel_esferas(request):
    disciplina_id = request.GET.get('disciplina')
    serie_id = request.GET.get('serie')

    disciplina = None
    serie = None
    if disciplina_id:
        try:
            disciplina = Disciplina.objects.get(pk=disciplina_id)
        except Disciplina.DoesNotExist:
            pass
    if serie_id:
        try:
            serie = Serie.objects.get(pk=serie_id)
        except Serie.DoesNotExist:
            pass

    if not disciplina:
        disciplina = Disciplina.objects.first()
    if not serie:
        serie = Serie.objects.first()

    # Garante que temos disciplina e série para continuar
    if not disciplina or not serie:
        context = {
            'todas_disciplinas': Disciplina.objects.all(),
            'todas_series': Serie.objects.all(),
            'disciplina': None,
            'serie': None,
            'anos': [], 'esferas': [], 'matriz': {},
            'total_esferas': 0, 'total_desempenhos': 0,
            'ultimo_ano': None, 'ranking': [], 'evolucao': [],
        }
        return render(request, 'dashboard/painel_esferas.html', context)


    desempenhos = DesempenhoEsfera.objects.filter(
        disciplina=disciplina,
        serie=serie
    ).select_related('esfera').order_by('ano', 'esfera__nome')

    anos = sorted(set(d.ano for d in desempenhos))
    esferas = Esfera.objects.all().order_by('nome')

    # Matriz: [esfera][ano] = desempenho ou None
    # Já enriquecemos cada desempenho com o padrão SAEB
    matriz = {}
    for esfera in esferas:
        matriz[esfera.id] = {ano: None for ano in anos}

    for d in desempenhos:
        d.padrao_saeb = classificar_nivel(
            disciplina.nome,
            serie.nome,
            d.proficiencia_media
        )
        matriz[d.esfera_id][d.ano] = d

    total_esferas = Esfera.objects.count()
    total_desempenhos = DesempenhoEsfera.objects.count()
    anos_disponiveis = (
        DesempenhoEsfera.objects
        .values_list('ano', flat=True)
        .distinct()
        .order_by('-ano')
    )
    ultimo_ano = anos_disponiveis.first() if anos_disponiveis else None

    ranking = []
    if ultimo_ano:
        desempenhos_ranking = DesempenhoEsfera.objects.filter(
            ano=ultimo_ano,
            disciplina=disciplina,
            serie=serie
        ).select_related('esfera').order_by('-proficiencia_media')[:10]

        for item in desempenhos_ranking:
            item.soma_ab = item.abaixo_basico + item.basico
            item.soma_aa = item.adequado + item.avancado
            item.padrao_saeb = classificar_nivel(
                disciplina.nome,
                serie.nome,
                item.proficiencia_media
            )
            ranking.append(item)

    evolucao = DesempenhoEsfera.objects.filter(
        disciplina=disciplina,
        serie=serie
    ).values('ano').annotate(
        media_proficiencia=Avg('proficiencia_media'),
        total_avaliados=Sum('alunos_avaliados')
    ).order_by('ano')

    # Classifica também cada ponto da evolução
    evolucao_com_padrao = []
    for ponto in evolucao:
        ponto['padrao_saeb'] = classificar_nivel(
            disciplina.nome,
            serie.nome,
            ponto['media_proficiencia']
        )
        evolucao_com_padrao.append(ponto)

    todas_disciplinas = Disciplina.objects.all()
    todas_series = Serie.objects.all()

    context = {
        'disciplina': disciplina,
        'serie': serie,
        'todas_disciplinas': todas_disciplinas,
        'todas_series': todas_series,
        'anos': anos,
        'esferas': esferas,
        'matriz': matriz,
        'total_esferas': total_esferas,
        'total_desempenhos': total_desempenhos,
        'ultimo_ano': ultimo_ano,
        'ranking': ranking,
        'evolucao': evolucao_com_padrao,
    }
    return render(request, 'dashboard/painel_esferas.html', context)



# pagina com resultado de todos as series e disciplinas do municipio 18_03_2026

from django.shortcuts import render
from django.db.models import Avg, Sum
from .models import Esfera, Disciplina, Serie, DesempenhoEsfera


def painel_comparativo_geral(request, municipio_id=None):

    municipio_selecionado = None
    if municipio_id:
        try:
            municipio_selecionado = Esfera.objects.get(pk=municipio_id)
        except Esfera.DoesNotExist:
            pass

    # -----------------------------
    # BASE DE DADOS
    # -----------------------------
    desempenhos_base_query = DesempenhoEsfera.objects.all()

    if municipio_selecionado:
        desempenhos_base_query = desempenhos_base_query.filter(
            municipio=municipio_selecionado
        )

    # 🔧 CORREÇÃO AQUI (related_name correto)
    todas_disciplinas = Disciplina.objects.filter(
        desempenhos_esfera__in=desempenhos_base_query
    ).distinct().order_by('nome')

    todas_series = Serie.objects.filter(
        desempenhos_esfera__in=desempenhos_base_query
    ).distinct().order_by('nome')

    todos_anos = desempenhos_base_query.values_list(
        'ano', flat=True
    ).distinct().order_by('ano')

    # -----------------------------
    # ESTRUTURA COMPARATIVA
    # -----------------------------
    dados_comparativos = {}

    for disc in todas_disciplinas:
        dados_comparativos[disc.id] = {
            'nome': disc.nome,
            'series': {}
        }

        for serie_obj in todas_series:
            dados_comparativos[disc.id]['series'][serie_obj.id] = {
                'nome': serie_obj.nome,
                'anos_data': {}
            }

            desempenhos_por_serie_disc = desempenhos_base_query.filter(
                disciplina=disc,
                serie=serie_obj
            ).select_related('esfera').order_by('ano', 'esfera__nome')

            for ano in todos_anos:
                dados_comparativos[disc.id]['series'][serie_obj.id]['anos_data'][ano] = {}

                desempenhos_no_ano = [
                    d for d in desempenhos_por_serie_disc if d.ano == ano
                ]

                for d in desempenhos_no_ano:
                    d.padrao_saeb = classificar_nivel(
                        disc.nome,
                        serie_obj.nome,
                        d.proficiencia_media
                    )

                    dados_comparativos[disc.id]['series'][serie_obj.id]['anos_data'][ano][d.esfera_id] = d

    # -----------------------------
    # ESFERAS
    # -----------------------------
    todas_esferas = Esfera.objects.all().order_by('nome')

    # =========================================================
    # 🔴 BLOCO MUNICIPAL
    # =========================================================
    resumo_municipal = []
    evolucao_municipal = []
    ganho_municipal = None

    esfera_municipal = Esfera.objects.filter(
        nome__icontains="MUNICIPAL"
    ).first()

    if esfera_municipal:
        dados_municipais = desempenhos_base_query.filter(
            esfera=esfera_municipal
        ).order_by('ano')

        # TABELA MUNICIPAL
        for d in dados_municipais:
            d.padrao_saeb = classificar_nivel(
                d.disciplina.nome,
                d.serie.nome,
                d.proficiencia_media
            )
            resumo_municipal.append(d)

        # EVOLUÇÃO
        evolucao = dados_municipais.values('ano').annotate(
            media=Avg('proficiencia_media')
        ).order_by('ano')

        evolucao_municipal = list(evolucao)

        for e in evolucao_municipal:
            e['padrao_saeb'] = classificar_nivel(
                dados_municipais.first().disciplina.nome if dados_municipais.exists() else "",
                dados_municipais.first().serie.nome if dados_municipais.exists() else "",
                e['media']
            )

        # GANHO
        if len(evolucao_municipal) >= 2:
            inicio = evolucao_municipal[0]['media']
            fim = evolucao_municipal[-1]['media']
            if inicio and fim:
                ganho_municipal = round(fim - inicio, 1)

    # -----------------------------
    # CONTEXTO
    # -----------------------------
    context = {
        'municipio_selecionado': municipio_selecionado,
        'todas_disciplinas': todas_disciplinas,
        'todas_series': todas_series,
        'todos_anos': todos_anos,
        'todas_esferas': todas_esferas,
        'dados_comparativos': dados_comparativos,

        # 🔴 MUNICIPAL
        'resumo_municipal': resumo_municipal,
        'evolucao_municipal': evolucao_municipal,
        'ganho_municipal': ganho_municipal,
    }

    return render(request, 'dashboard/painel_comparativo_geral.html', context)
    # analise das habilidades por esfera - 04_03_2026

from django.shortcuts import render, get_object_or_404
from django.db.models import Avg
from .models import ResultHab, Hab, Esfera, Serie, Disciplina

from django.shortcuts import render, get_object_or_404
from .models import ResultHab, Hab, Esfera
from django.db.models import Prefetch
def comparativo_habilidades(request):
    # Filtros
    esfera_id = request.GET.get('esfera')
    serie_id = request.GET.get('serie')
    disciplina_id = request.GET.get('disciplina')
    
    # Buscar esfera selecionada (se houver)
    esfera = None
    if esfera_id:
        esfera = get_object_or_404(Esfera, id=esfera_id)
    
    # Base queryset para resultados
    resultados_base = ResultHab.objects.all()
    if esfera:
        resultados_base = resultados_base.filter(esfera=esfera)
    
    # Lista de anos disponíveis (baseada nos filtros aplicados)
    anos = []
    if resultados_base.exists():
        anos = (
            resultados_base
            .values_list('ano', flat=True)
            .distinct()
            .order_by('ano')
        )
    
    # Base queryset para habilidades
    habilidades_base = Hab.objects.all()
    
    # Aplicar filtros de série e disciplina se fornecidos
    if serie_id:
        habilidades_base = habilidades_base.filter(serie_id=serie_id)
    if disciplina_id:
        habilidades_base = habilidades_base.filter(disciplina_id=disciplina_id)
    
    # Filtrar habilidades que têm resultados na esfera selecionada (se houver esfera)
    if esfera:
        habilidades_base = habilidades_base.filter(resultados_hab__esfera=esfera)
    
    # Habilidades finais
    habilidades = (
        habilidades_base
        .select_related('serie', 'disciplina')
        .distinct()
        .order_by('serie__nome', 'disciplina__nome', 'cd_hab')
    )
    
    # Listas para os selects do filtro
    esferas = Esfera.objects.all().order_by('nome')
    
    # Séries disponíveis (baseado na esfera selecionada)
    series = Serie.objects.all()
    if esfera:
        series = series.filter(
            hab__resultados_hab__esfera=esfera
        ).distinct()
    series = series.order_by('nome')
    
    # Disciplinas disponíveis (baseado na esfera e série selecionadas)
    disciplinas = Disciplina.objects.all()
    if esfera:
        disciplinas = disciplinas.filter(
            hab__resultados_hab__esfera=esfera
        )
    if serie_id:
        disciplinas = disciplinas.filter(
            hab__serie_id=serie_id
        )
    disciplinas = disciplinas.distinct().order_by('nome')
    
    # Construir tabela apenas se houver esfera selecionada
    tabela = []
    dados_grafico = []
    
    if esfera and anos:
        for hab in habilidades:
            linha = {
                'serie': hab.serie.nome,
                'disciplina': hab.disciplina.nome,
                'codigo': hab.cd_hab,
                'descricao': hab.dc_hab,
                'anos': []
            }
            
            for ano in anos:
                resultado = ResultHab.objects.filter(
                    esfera=esfera,
                    hab=hab,
                    ano=ano
                ).first()
                
                tx_acerto = float(resultado.tx_acerto) if resultado and resultado.tx_acerto is not None else None
                
                linha['anos'].append({
                    'ano': ano,
                    'tx_acerto': tx_acerto
                })
            
            tabela.append(linha)
            
            # Dados para gráfico
            linha_grafico = {
                'codigo': hab.cd_hab,
                'disciplina': hab.disciplina.nome,
                'serie': hab.serie.nome,
                'anos': linha['anos']
            }
            dados_grafico.append(linha_grafico)
    
    # Converter anos para lista
    anos_list = list(anos)
    
    context = {
        'esferas': esferas,
        'series': series,
        'disciplinas': disciplinas,
        'esfera_selecionada': esfera,
        'serie_selecionada': int(serie_id) if serie_id else None,
        'disciplina_selecionada': int(disciplina_id) if disciplina_id else None,
        'anos': anos_list,
        'tabela': tabela,
        'dados_grafico': dados_grafico
    }
    
    return render(request, 'dashboard/comparativo_habilidades.html', context)


#desempenho _habilidades

from django.shortcuts import render
from django.db.models import Avg
from .models import DesempenhoEscola, Serie, Disciplina

import json
from django.db.models import Avg
from django.shortcuts import render
from .models import DesempenhoEscola, Serie, Disciplina


def dashboard_desempenho(request):

    ano = request.GET.get("ano")
    serie = request.GET.get("serie")
    disciplina = request.GET.get("disciplina")

    dados = DesempenhoEscola.objects.all()

    if ano:
        dados = dados.filter(ano=ano)

    if serie:
        dados = dados.filter(serie_id=serie)

    if disciplina:
        dados = dados.filter(disciplina_id=disciplina)

    # indicadores
    media = dados.aggregate(
        m=Avg("proficiencia_media")
    )["m"] or 0

    total_escolas = dados.values("escola").distinct().count()

    total_alunos = dados.aggregate(
        t=Avg("alunos_avaliados")
    )["t"] or 0


    # gráfico por série
    labels = []
    valores = []

    for s in Serie.objects.all():

        valor = dados.filter(
            serie=s
        ).aggregate(
            v=Avg("proficiencia_media")
        )["v"]

        if valor is not None:

            labels.append(s.nome)

            valores.append(float(valor))   # ← CORREÇÃO


    # tabela
    tabela = []

    for i in range(len(labels)):

        tabela.append({
            "serie": labels[i],
            "valor": round(valores[i],1)
        })


    context = {

        "labels": json.dumps(labels),
        "valores": json.dumps(valores),

        "tabela": tabela,

        "anos": DesempenhoEscola.objects.values_list(
            "ano",
            flat=True
        ).distinct(),

        "series": Serie.objects.all(),
        "disciplinas": Disciplina.objects.all(),

        "media": round(float(media),1),
        "total_escolas": total_escolas,
        "total_alunos": int(total_alunos),

        "filtro_ano": ano,
        "filtro_serie": serie,
        "filtro_disciplina": disciplina

    }

    return render(
        request,
        "dashboard/desempenho.html",
        context
    )