"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from django.urls import path
from . import views

from django.urls import path
from django.views.generic import RedirectView
from . import views
# urls.py
from django.urls import path
from . import views


urlpatterns = [
     path('admin/', admin.site.urls),
    path('dashboard/', views.dashboard_principal, name='dashboard'),
    path('dashboard/dados-graficos/', views.dados_graficos, name='dados_graficos'),
    path('dashboard/escola/<int:escola_id>/', views.detalhes_escola, name='detalhes_escola'),
    path('dashboard/comparacao-anos/', views.comparacao_anos, name='comparacao_anos'),
    path('dashboard/escola-comparativo/', views.comparacao_escolas, name='comparacao_escolas'),
    path('dashboard/ranking-geral/', views.ranking_geral, name='ranking_geral'),
    path('dashboard/painel-localidade/', views.painel_localidade, name='painel_localidade'),
    path('dashboard/relatorios/', views.relatorios, name='relatorios'),
    path('dashboard/relatorios/pdf/', views.relatorio_pdf, name='relatorio_pdf'),
    path('dashboard/boletim-html/<int:escola_id>/', views.boletim_escola, name='boletim_escola_html'),
    path('boletim/<int:escola_id>/', views.boletim_escola, name='boletim_escola'),
    path('dashboard/boletim_escola/', views.selecionar_escola_boletim, name='selecionar_escola_boletim'),
    path('dashboard/boletim_escola/', views.selecionar_escola_boletim, name='selecionar_escola_boletim'),
    path('escolas-participantes/', views.relatorio_escolas_participantes, name='relatorio_escolas_participantes'),

]


