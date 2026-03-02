from traceback import format_tb

from django.contrib import admin
from .models import Localidade, Escola, Disciplina, Serie, DesempenhoEscola, MetaMunicipal, EvolucaoEscola, DesempenhoEsfera, Esfera, Habilidade1, ResultadoHabilidade1


admin.site.register(Localidade)
admin.site.register(Escola)
admin.site.register(Disciplina)
admin.site.register(Serie)
admin.site.register(DesempenhoEscola)
admin.site.register(MetaMunicipal)
admin.site.register(EvolucaoEscola)
admin.site.register(DesempenhoEsfera)
admin.site.register(Esfera)



# Prime

from django.contrib import admin
from .models import Hab, ResultHab

@admin.register(Hab)
class HabAdmin(admin.ModelAdmin):
    list_display = ('cd_hab', 'dc_hab', 'serie', 'disciplina')
    search_fields = ('cd_hab', 'dc_hab')
    list_filter = ('serie', 'disciplina')
    ordering = ('disciplina', 'serie', 'cd_hab')

@admin.register(ResultHab)
class ResultHabAdmin(admin.ModelAdmin):
    list_display = ('ano', 'esfera', 'get_serie', 'get_cd_hab', 'get_dc_hab', 'tx_acerto')
    list_filter = ('ano', 'esfera', 'hab__serie', 'hab__disciplina')
    search_fields = ('hab__cd_hab', 'hab__dc_hab')
    autocomplete_fields = ['hab']
    
    # Métodos para exibir dados da habilidade na listagem
    def get_serie(self, obj):
        return obj.hab.serie
    get_serie.short_description = 'Série'
    get_serie.admin_order_field = 'hab__serie'
    
    def get_cd_hab(self, obj):
        return obj.hab.cd_hab
    get_cd_hab.short_description = 'Código'
    get_cd_hab.admin_order_field = 'hab__cd_hab'
    
    def get_dc_hab(self, obj):
        return obj.hab.dc_hab[:50]
    get_dc_hab.short_description = 'Descrição'