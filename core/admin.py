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