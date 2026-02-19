from django.shortcuts import render, get_object_or_404
from django.db.models import Avg, Sum, Count
from django.http import JsonResponse, HttpResponse
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


def relatorio_escolas_participantes(request):

    queryset = DesempenhoEscola.objects.select_related(
        'escola', 'escola__localidade', 'disciplina', 'serie'
    )

    localidade = request.GET.get('localidade')
    escola = request.GET.get('escola')
    ano_inicio = request.GET.get('ano_inicio')
    ano_fim = request.GET.get('ano_fim')

    if localidade:
        queryset = queryset.filter(escola__localidade_id=localidade)

    if escola:
        queryset = queryset.filter(escola_id=escola)

    if ano_inicio and ano_fim:
        queryset = queryset.filter(ano__range=[ano_inicio, ano_fim])

    dados = (
        queryset
        .values(
            'ano',
            'escola__id',
            'escola__nome',
            'escola__localidade__nome'
        )
        .annotate(
            total_avaliados=Sum('alunos_avaliados'),
            series=Count('serie_id', distinct=True),
            disciplinas=Count('disciplina_id', distinct=True),
        )
        .order_by('ano', 'escola__nome')
    )

    return render(request, 'dashboard/relatorio_escolas_participantes.html', {
        'dados': dados
    })
