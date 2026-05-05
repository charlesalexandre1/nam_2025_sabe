from django.contrib import admin
from .models import (
    Localidade, Escola, Disciplina, Serie,
    DesempenhoEscola, MetaMunicipal, EvolucaoEscola,
    DesempenhoEsfera, Esfera,
    Hab, ResultHab, ResultadoHabEscola
)

# ---------------------------
# BÁSICOS
# ---------------------------

@admin.register(Localidade)
class LocalidadeAdmin(admin.ModelAdmin):
    search_fields = ('nome',)


@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'inep', 'localidade')
    search_fields = ('nome', 'inep')
    list_filter = ('localidade',)
    autocomplete_fields = ['localidade']
    list_per_page = 50


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    search_fields = ('nome', 'codigo')


@admin.register(Serie)
class SerieAdmin(admin.ModelAdmin):
    search_fields = ('nome',)


@admin.register(Esfera)
class EsferaAdmin(admin.ModelAdmin):
    search_fields = ('nome',)

# ---------------------------
# DESEMPENHO ESCOLA
# ---------------------------

@admin.register(DesempenhoEscola)
class DesempenhoEscolaAdmin(admin.ModelAdmin):
    list_display = ('escola', 'ano', 'disciplina', 'serie', 'proficiencia_media')
    list_filter = ('ano', 'disciplina', 'serie')
    search_fields = ('escola__nome',)
    autocomplete_fields = ['escola', 'disciplina', 'serie']
    list_select_related = ('escola', 'disciplina', 'serie')
    list_per_page = 50


@admin.register(MetaMunicipal)
class MetaMunicipalAdmin(admin.ModelAdmin):
    list_display = ('ano', 'disciplina', 'serie', 'proficiencia_meta')
    list_filter = ('ano', 'disciplina', 'serie')


@admin.register(EvolucaoEscola)
class EvolucaoEscolaAdmin(admin.ModelAdmin):
    list_display = ('escola', 'disciplina', 'serie', 'ano_inicial', 'ano_final')
    search_fields = ('escola__nome',)
    autocomplete_fields = ['escola', 'disciplina', 'serie']
    list_select_related = ('escola', 'disciplina', 'serie')


@admin.register(DesempenhoEsfera)
class DesempenhoEsferaAdmin(admin.ModelAdmin):
    list_display = ('esfera', 'ano', 'disciplina', 'serie', 'proficiencia_media')
    list_filter = ('ano', 'disciplina', 'serie')
    autocomplete_fields = ['esfera', 'disciplina', 'serie']
    list_select_related = ('esfera', 'disciplina', 'serie')

# ---------------------------
# HABILIDADES
# ---------------------------

@admin.register(Hab)
class HabAdmin(admin.ModelAdmin):
    list_display = ('cd_hab', 'dc_hab', 'serie', 'disciplina')
    search_fields = ('cd_hab',)
    list_filter = ('serie', 'disciplina')
    ordering = ('disciplina', 'serie', 'cd_hab')
    list_per_page = 50

# ---------------------------
# RESULTADO POR HABILIDADE (ESFERA)
# ---------------------------

@admin.register(ResultHab)
class ResultHabAdmin(admin.ModelAdmin):
    list_display = ('ano', 'esfera', 'get_cd_hab', 'tx_acerto')
    list_filter = ('ano', 'esfera')
    search_fields = ('hab__cd_hab',)
    autocomplete_fields = ['hab']
    list_select_related = ('hab', 'esfera')
    list_per_page = 50

    def get_cd_hab(self, obj):
        return obj.hab.cd_hab
    get_cd_hab.short_description = 'Código'

# ---------------------------
# RESULTADO POR HABILIDADE (ESCOLA)
# ---------------------------

@admin.register(ResultadoHabEscola)
class ResultadoHabEscolaAdmin(admin.ModelAdmin):
    list_display = (
        'ano',
        'escola',
        'get_cd_hab',
        'tx_acerto'
    )

    list_filter = (
        'ano',
        'disciplina',
    )

    search_fields = (
        'escola__nome',
        'hab__cd_hab',
    )

    autocomplete_fields = ['hab']  # escola removido (performance)

    list_select_related = ('escola', 'hab')

    list_per_page = 50

    def get_cd_hab(self, obj):
        return obj.hab.cd_hab
    get_cd_hab.short_description = 'Código'

from django.contrib import admin
from .models import ResultPreliminarSaeb_2025


@admin.register(ResultPreliminarSaeb_2025)
class ResultPreliminarSaeb2025Admin(admin.ModelAdmin):

    # 🔹 Colunas exibidas na lista
    list_display = (
        'escola',
        'serie',
        'ano',
        'media_lp',
        'media_mt',
        'media_geral',
        'taxa_aprovacao',
        'taxa_participacao',
        'ideb_estimado',
    )

    # 🔹 Filtros laterais
    list_filter = (
        'ano',
        'serie',
        'escola',
    )

    # 🔹 Campo de busca
    search_fields = (
        'escola__nome',
        'escola__inep',
    )

    # 🔹 Ordenação padrão
    ordering = ('-ano', 'escola__nome')

    # 🔹 Campos somente leitura
    readonly_fields = (
        'taxa_participacao',
        'media_geral',
        'ideb_estimado',
        'data_atualizacao',
    )

    # 🔹 Organização do formulário
    fieldsets = (
        ('📌 Identificação', {
            'fields': ('escola', 'serie', 'ano')
        }),

        ('👥 Participação', {
            'fields': (
                'alunos_previstos',
                'alunos_avaliados',
                'taxa_participacao',
            )
        }),

        ('📊 Desempenho', {
            'fields': (
                'media_lp',
                'media_mt',
                'media_geral',
            )
        }),

        ('🎯 Indicadores', {
            'fields': (
                'taxa_aprovacao',
                'ideb_estimado',
            )
        }),

        ('⚙️ Sistema', {
            'fields': ('data_atualizacao',),
        }),
    )

    # 🔹 Otimização de carregamento
    list_select_related = ('escola', 'serie')

    # 🔹 Paginação
    list_per_page = 25

from django.contrib import admin
from .models import Escola, Alfabetometro




@admin.register(Alfabetometro)
class AlfabetometroAdmin(admin.ModelAdmin):
    list_display = (
        'escola',
        'ano_referencia',
        'periodo',
        'qtd_alunos_ano',
        'qtd_alfabetico',
        'qtd_pre_silabico',
        'data_registro'
    )

    list_filter = (
        'ano_referencia',
        'periodo',
        'escola',
    )

    search_fields = (
        'escola__nome',
    )

    ordering = (
        '-ano_referencia',
        'escola',
    )

    list_per_page = 20

    # 🔥 extra: deixa mais organizado
    fieldsets = (
        ('Informações Gerais', {
            'fields': ('escola', 'ano_referencia', 'periodo')
        }),
        ('Dados de Alfabetização', {
            'fields': (
                'qtd_alunos_ano',
                'qtd_pre_silabico',
                'qtd_silabico',
                'qtd_silabico_alfabetico',
                'qtd_alfabetico'
            )
        }),
    )

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    NivelEscrita,
    Estudante,
)


@admin.register(NivelEscrita)
class NivelEscritaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'total_estudantes')
    search_fields = ('nome',)
    ordering = ('nome',)

    def total_estudantes(self, obj):
        count = obj.estudantes.count()
        return format_html(
            '<span style="font-weight:bold; color:#2e7d32;">{}</span>',
            count
        )
    total_estudantes.short_description = 'Total de Estudantes'


class EstudanteInline(admin.TabularInline):
    model = Estudante
    extra = 0
    fields = ('nome', 'serie', 'nivel_escrita', 'periodo', 'ano')
    readonly_fields = ('data_cadastro',)
    show_change_link = True


@admin.register(Estudante)
class EstudanteAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'escola',
        'serie',
        'nivel_escrita',
        'periodo',
        'ano',
        'bairro',
        'data_cadastro',
    )

    list_filter = (
        'ano',
        'serie',
        'nivel_escrita',
        'periodo',
        'escola__localidade',
    )

    search_fields = (
        'nome',
        'escola__nome',
        'bairro',
        'endereco',
    )

    ordering = ('nome',)

    readonly_fields = ('data_cadastro', 'data_atualizacao')

    fieldsets = (
        ('Dados Pessoais', {
            'fields': (
                'nome',
                'endereco',
                'bairro',
            )
        }),
        ('Vínculo Escolar', {
            'fields': (
                'escola',
                'serie',
                'nivel_escrita',
                'periodo',
                'ano',
            )
        }),
        ('Auditoria', {
            'classes': ('collapse',),
            'fields': (
                'data_cadastro',
                'data_atualizacao',
            )
        }),
    )

    autocomplete_fields = ('escola', 'serie', 'nivel_escrita')

    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'escola',
            'serie',
            'nivel_escrita',
            'escola__localidade',
        )