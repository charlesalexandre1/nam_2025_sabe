from django.db import models

class Escola(models.Model):
    id = models.IntegerField('ID Manual', primary_key=True)
    inep = models.CharField('Código INEP', max_length=10, unique=True)
    nome = models.CharField('Nome da Escola', max_length=255)
    endereco = models.CharField('Endereço', max_length=255)
    bairrodistrito = models.CharField('Bairro/Distrito', max_length=100)
    gestor = models.CharField('Gestor (Nome e Telefone)', max_length=255)

    localidade = models.ForeignKey(
        "Localidade",
        on_delete=models.CASCADE,
        verbose_name='Localidade'
    )

    latitude = models.DecimalField(
        'Latitude', max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    longitude = models.DecimalField(
        'Longitude', max_digits=9, decimal_places=6,
        null=True, blank=True
    )

    telefone_extraido = models.CharField('Telefone Extraído', max_length=20, blank=True, null=True)
    dados = models.JSONField('Dados Adicionais', null=True, blank=True)

    def __str__(self):
        return f"{self.nome} (ID: {self.id})"
    
    def google_maps_url(self):
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return None


class Localidade(models.Model):
    nome = models.CharField('Nome da Localidade', max_length=100)
    
    def __str__(self):
        return self.nome


# Modelo para disciplinas (Matemática, Português, etc.)
class Disciplina(models.Model):
    nome = models.CharField('Nome da Disciplina', max_length=100)
    codigo = models.CharField('Código', max_length=10, blank=True, null=True)
    
    def __str__(self):
        return self.nome


# Modelo para séries/anos escolares (5º ano, 9º ano, etc.)
class Serie(models.Model):
    nome = models.CharField('Série/Ano', max_length=50)
    nivel_ensino = models.CharField('Nível de Ensino', max_length=50, blank=True, null=True)
    
    def __str__(self):
        return self.nome


# Modelo principal para armazenar os resultados da Prova SABE
class DesempenhoEscola(models.Model):
    escola = models.ForeignKey(
        Escola, 
        on_delete=models.CASCADE, 
        related_name='desempenhos',
        verbose_name='Escola'
    )
    ano = models.IntegerField('Ano da Prova')
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        verbose_name='Disciplina'
    )
    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        verbose_name='Série/Ano'
    )
    
    # Dados de participação
    alunos_previstos = models.IntegerField('Alunos Previstos')
    alunos_avaliados = models.IntegerField('Alunos Avaliados')
    percentual_avaliados = models.DecimalField(
        'Avaliados (%)', 
        max_digits=5, 
        decimal_places=2,
        help_text='Percentual de alunos avaliados'
    )
    
    # Dados de desempenho
    proficiencia_media = models.DecimalField(
        'Proficiência Média', 
        max_digits=6, 
        decimal_places=2,
        help_text='Média de proficiência da escola'
    )
    
    # Distribuição por níveis de aprendizagem
    abaixo_basico = models.DecimalField(
        'Abaixo do Básico (%)', 
        max_digits=5, 
        decimal_places=2,
        default=0
    )
    basico = models.DecimalField(
        'Básico (%)', 
        max_digits=5, 
        decimal_places=2,
        default=0
    )
    adequado = models.DecimalField(
        'Adequado (%)', 
        max_digits=5, 
        decimal_places=2,
        default=0
    )
    avancado = models.DecimalField(
        'Avançado (%)', 
        max_digits=5, 
        decimal_places=2,
        default=0
    )
    
    # Campos calculados ou adicionais
    taxa_participacao = models.DecimalField(
        'Taxa de Participação (%)',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Taxa calculada: (avaliados/previstos)*100'
    )
    
    meta_estabelecida = models.DecimalField(
        'Meta Estabelecida',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Dados para comparação
    variacao_ano_anterior = models.DecimalField(
        'Variação vs Ano Anterior',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    posicao_municipio = models.IntegerField(
        'Posição no Município',
        null=True,
        blank=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Data de Atualização',
        auto_now=True
    )
    
    observacoes = models.TextField('Observações', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Desempenho da Escola'
        verbose_name_plural = 'Desempenhos das Escolas'
        unique_together = ['escola', 'ano', 'disciplina', 'serie']
        ordering = ['-ano', 'escola__nome', 'disciplina__nome']
    
    def __str__(self):
        return f"{self.escola.nome} - {self.ano} - {self.disciplina} - {self.serie}"
    
    def calcular_taxa_participacao(self):
        """Calcula a taxa de participação se houver alunos previstos"""
        if self.alunos_previstos > 0:
            return (self.alunos_avaliados / self.alunos_previstos) * 100
        return 0
    
    def save(self, *args, **kwargs):
        """Sobrescreve o save para calcular campos automáticos"""
        # Calcula taxa de participação se não fornecida
        if self.taxa_participacao is None:
            self.taxa_participacao = self.calcular_taxa_participacao()
        
        # Garante que a soma dos percentuais seja 100%
        total_percentuais = (
            (self.abaixo_basico or 0) + 
            (self.basico or 0) + 
            (self.adequado or 0) + 
            (self.avancado or 0)
        )
        
        # Se a soma não for 100%, ajusta proporcionalmente
        if total_percentuais != 100 and total_percentuais > 0:
            fator = 100 / total_percentuais
            self.abaixo_basico = round((self.abaixo_basico or 0) * fator, 2)
            self.basico = round((self.basico or 0) * fator, 2)
            self.adequado = round((self.adequado or 0) * fator, 2)
            self.avancado = round((self.avancado or 0) * fator, 2)
        
        super().save(*args, **kwargs)


# Modelo para armazenar metas municipais por ano/disciplina/série
class MetaMunicipal(models.Model):
    ano = models.IntegerField('Ano')
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        verbose_name='Disciplina'
    )
    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        verbose_name='Série/Ano'
    )
    
    proficiencia_meta = models.DecimalField(
        'Meta de Proficiência',
        max_digits=6,
        decimal_places=2
    )
    
    percentual_adequado_avancado_meta = models.DecimalField(
        'Meta % Adequado+Avançado',
        max_digits=5,
        decimal_places=2
    )
    
    descricao = models.TextField('Descrição da Meta', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Meta Municipal'
        verbose_name_plural = 'Metas Municipais'
        unique_together = ['ano', 'disciplina', 'serie']
    
    def __str__(self):
        return f"Meta {self.ano} - {self.disciplina} - {self.serie}"


# Modelo para histórico de evolução por escola
class EvolucaoEscola(models.Model):
    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name='evolucao',
        verbose_name='Escola'
    )
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        verbose_name='Disciplina'
    )
    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        verbose_name='Série/Ano'
    )
    
    ano_inicial = models.IntegerField('Ano Inicial')
    ano_final = models.IntegerField('Ano Final')
    
    crescimento_proficiencia = models.DecimalField(
        'Crescimento Proficiência',
        max_digits=6,
        decimal_places=2
    )
    
    crescimento_adequado_avancado = models.DecimalField(
        'Crescimento % Adequado+Avançado',
        max_digits=5,
        decimal_places=2
    )
    
    classificacao_evolucao = models.CharField(
        'Classificação da Evolução',
        max_length=50,
        choices=[
            ('alta', 'Alta Evolução'),
            ('moderada', 'Evolução Moderada'),
            ('estavel', 'Estabilidade'),
            ('regressao', 'Regressão'),
        ]
    )
    
    data_calculo = models.DateTimeField(
        'Data do Cálculo',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Evolução da Escola'
        verbose_name_plural = 'Evoluções das Escolas'
    
    def __str__(self):
        return f"Evolução {self.escola.nome} ({self.ano_inicial}-{self.ano_final})"

from django.core.validators import MinValueValidator, MaxValueValidator

class Esfera(models.Model):
    nome = models.CharField('Nome da Esfera', max_length=100)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = 'Esfera'
        verbose_name_plural = 'Esferas'


class DesempenhoEsfera(models.Model):  # Nome em CamelCase
    esfera = models.ForeignKey(
        Esfera, 
        on_delete=models.CASCADE, 
        related_name='desempenhos',
        verbose_name='Esfera'
    )
    ano = models.PositiveIntegerField('Ano da Prova')
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        related_name='desempenhos_esfera',  # Opcional
        verbose_name='Disciplina'
    )
    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        related_name='desempenhos_esfera',  # Opcional
        verbose_name='Série/Ano'
    )
    
    alunos_previstos = models.PositiveIntegerField('Alunos Previstos')
    alunos_avaliados = models.PositiveIntegerField('Alunos Avaliados')
    percentual_avaliados = models.DecimalField(
        'Avaliados (%)', 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Percentual de alunos avaliados (calculado automaticamente)'
    )
    
    proficiencia_media = models.DecimalField(
        'Proficiência Média', 
        max_digits=6, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Média de proficiência da esfera'
    )
    
    abaixo_basico = models.DecimalField(
        'Abaixo do Básico (%)', 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    basico = models.DecimalField(
        'Básico (%)', 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    adequado = models.DecimalField(
        'Adequado (%)', 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    avancado = models.DecimalField(
        'Avançado (%)', 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    
    # Campos opcionais
    meta_estabelecida = models.DecimalField(
        'Meta Estabelecida',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    variacao_ano_anterior = models.DecimalField(
        'Variação vs Ano Anterior',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    posicao_municipio = models.PositiveIntegerField(
        'Posição no Município',
        null=True,
        blank=True
    )
    observacoes = models.TextField('Observações', blank=True, null=True)
    
    data_atualizacao = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Desempenho da Esfera'
        verbose_name_plural = 'Desempenhos das Esferas'
        unique_together = ['esfera', 'ano', 'disciplina', 'serie']
        ordering = ['-ano', 'esfera__nome', 'disciplina__nome']
        indexes = [
            models.Index(fields=['esfera', 'ano', 'disciplina', 'serie']),
        ]
    
    def __str__(self):
        return f"{self.esfera.nome} - {self.ano} - {self.disciplina} - {self.serie}"
    
    def save(self, *args, **kwargs):
        # Calcula percentual_avaliados automaticamente
        if self.alunos_previstos:
            self.percentual_avaliados = (self.alunos_avaliados / self.alunos_previstos) * 100
        else:
            self.percentual_avaliados = 0
        
        # Ajusta soma dos níveis para 100% (opcional, igual ao DesempenhoEscola)
        total = self.abaixo_basico + self.basico + self.adequado + self.avancado
        if total != 100 and total > 0:
            fator = 100 / total
            self.abaixo_basico = round(self.abaixo_basico * fator, 2)
            self.basico = round(self.basico * fator, 2)
            self.adequado = round(self.adequado * fator, 2)
            self.avancado = round(self.avancado * fator, 2)
        
        super().save(*args, **kwargs)

        #tabela habilidade criação

        from django.core.validators import MinValueValidator, MaxValueValidator

class Habilidade(models.Model):
    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        verbose_name='Série/Ano'
    )
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        verbose_name='Disciplina'
    )
    cd_habilidade = models.CharField(
        'Código da Habilidade',
        max_length=20,
        help_text='Código identificador da habilidade (ex: EF05LP01)'
    )
    dc_habilidade = models.TextField(
        'Descrição da Habilidade',
        help_text='Descrição completa da habilidade'
    )

    class Meta:
        verbose_name = 'Habilidade'
        verbose_name_plural = 'Habilidades'
        unique_together = ['serie', 'disciplina', 'cd_habilidade']
        ordering = ['disciplina', 'serie', 'cd_habilidade']

    def __str__(self):
        return f"{self.cd_habilidade} - {self.dc_habilidade[:50]}"


class ResultadoHabilidade(models.Model):
    ano = models.IntegerField('Ano')
    esfera = models.ForeignKey(
        Esfera,
        on_delete=models.CASCADE,
        verbose_name='Esfera'
    )
    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        verbose_name='Série/Ano'
    )
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        verbose_name='Disciplina'
    )
    cd_habilidade = models.CharField(
        'Código da Habilidade',
        max_length=20
    )
    tx_acerto = models.DecimalField(
        'Taxa de Acerto (%)',
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Percentual de acerto para esta habilidade'
    )

    class Meta:
        verbose_name = 'Resultado de Habilidade'
        verbose_name_plural = 'Resultados de Habilidades'
        unique_together = ['ano', 'esfera', 'serie', 'disciplina', 'cd_habilidade']
        indexes = [
            models.Index(fields=['ano', 'esfera', 'serie', 'disciplina']),
        ]
        ordering = ['-ano', 'esfera', 'disciplina', 'serie', 'cd_habilidade']

    def __str__(self):
        return f"{self.ano} - {self.esfera} - {self.disciplina} - {self.serie} - {self.cd_habilidade}"
    
    from django.core.validators import MinValueValidator, MaxValueValidator

class Habilidade1(models.Model):
    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        verbose_name='Série/Ano'
    )
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        verbose_name='Disciplina'
    )
    cd_habilidade = models.CharField(
        'Código da Habilidade',
        max_length=20,
        help_text='Código identificador da habilidade (ex: EF05LP01)'
    )
    dc_habilidade = models.TextField(
        'Descrição da Habilidade',
        help_text='Descrição completa da habilidade'
    )

    class Meta:
        verbose_name = 'Habilidade'
        verbose_name_plural = 'Habilidades'
        unique_together = ['serie', 'disciplina', 'cd_habilidade']
        ordering = ['disciplina', 'serie', 'cd_habilidade']

    def __str__(self):
        return f"{self.cd_habilidade} - {self.dc_habilidade[:50]}"


class ResultadoHabilidade1(models.Model):
    ano = models.IntegerField('Ano')
    esfera = models.ForeignKey(
        Esfera,
        on_delete=models.CASCADE,
        verbose_name='Esfera'
    )
    habilidade = models.ForeignKey(
        Habilidade1,
        on_delete=models.CASCADE,
        verbose_name='Habilidade',
        related_name='resultados'  # Opcional, para acessar os resultados de uma habilidade
    )
    tx_acerto = models.DecimalField(
        'Taxa de Acerto (%)',
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Percentual de acerto para esta habilidade'
    )

    class Meta:
        verbose_name = 'Resultado de Habilidade'
        verbose_name_plural = 'Resultados de Habilidades'
        unique_together = ['ano', 'esfera', 'habilidade']  # Garante unicidade por ano/esfera/habilidade
        indexes = [
            models.Index(fields=['ano', 'esfera', 'habilidade']),
        ]
        ordering = ['-ano', 'esfera', 'habilidade']

    def __str__(self):
        return f"{self.ano} - {self.esfera} - {self.habilidade.cd_habilidade}"
    

    #novas tentativas para tabela habilidade criação 02_03_2026

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Hab(models.Model):
    serie = models.ForeignKey(
        'Serie',  # ou import Serie diretamente
        on_delete=models.CASCADE,
        verbose_name='Série/Ano'
    )
    disciplina = models.ForeignKey(
        'Disciplina',  # ou import Disciplina diretamente
        on_delete=models.CASCADE,
        verbose_name='Disciplina'
    )
    cd_hab = models.CharField(
        'Código da Habilidade',
        max_length=20,
        help_text='Código identificador da habilidade (ex: EF05LP01)'
    )
    dc_hab = models.TextField(
        'Descrição da Habilidade',
        help_text='Descrição completa da habilidade'
    )

    class Meta:
        verbose_name = 'Habilidade'
        verbose_name_plural = 'Habilidades'
        unique_together = ['serie', 'disciplina', 'cd_hab']
        ordering = ['disciplina', 'serie', 'cd_hab']

    def __str__(self):
        return f"{self.cd_hab} - {self.dc_hab[:50]}"


class ResultHab(models.Model):
    ano = models.IntegerField('Ano')
    esfera = models.ForeignKey(
        'Esfera',  # ou import Esfera diretamente
        on_delete=models.CASCADE,
        verbose_name='Esfera'
    )
    hab = models.ForeignKey(
        Hab,
        on_delete=models.CASCADE,
        verbose_name='Habilidade',
        related_name='resultados_hab'  # Opcional: para acessar resultados de uma habilidade
    )
    tx_acerto = models.DecimalField(
        'Taxa de Acerto (%)',
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Percentual de acerto para esta habilidade'
    )

    class Meta:
        verbose_name = 'Resultado de Habilidade'
        verbose_name_plural = 'Resultados de Habilidades'
        unique_together = ['ano', 'esfera', 'hab']  # Garante unicidade por ano/esfera/habilidade
        indexes = [
            models.Index(fields=['ano', 'esfera', 'hab']),
        ]
        ordering = ['-ano', 'esfera', 'hab']

    def __str__(self):
        return f"{self.ano} - {self.esfera} - {self.hab.cd_hab}"


# habilidade por escolas 20_03_2026

class ResultadoHabEscola(models.Model):
    ano = models.IntegerField('Ano')

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        verbose_name='Escola'
    )

    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        verbose_name='Série/Ano'
    )

    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        verbose_name='Disciplina'
    )

    hab = models.ForeignKey(
        Hab,
        on_delete=models.CASCADE,
        verbose_name='Habilidade'
    )

    tx_acerto = models.DecimalField(
        'Taxa de Acerto (%)',
        max_digits=5,
        decimal_places=2
    )

    class Meta:
        unique_together = ['ano', 'escola', 'serie', 'disciplina', 'hab']
        indexes = [
            models.Index(fields=['ano', 'escola', 'serie', 'disciplina']),
        ]

    def __str__(self):
        return f"{self.ano} - {self.escola.nome} - {self.disciplina} - {self.serie} - {self.hab.cd_hab}"
    


    #SAEB  resultadoo
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class ResultPreliminarSaeb(models.Model):
    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name='resultados_preliminares',
        verbose_name='Escola'
    )

    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        verbose_name='Série/Ano'
    )

    ano = models.PositiveIntegerField('Ano')

    alunos_previstos = models.PositiveIntegerField(
        'Alunos Previstos',
        validators=[MinValueValidator(0)]
    )

    alunos_avaliados = models.PositiveIntegerField(
        'Alunos Avaliados',
        validators=[MinValueValidator(0)]
    )

    taxa_participacao = models.DecimalField(
        'Taxa de Participação (%)',
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )

    media_lp = models.DecimalField(
        'Média Língua Portuguesa',
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )

    media_mt = models.DecimalField(
        'Média Matemática',
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )

    # Campo útil para análise rápida (opcional)
    media_geral = models.DecimalField(
        'Média Geral',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    data_atualizacao = models.DateTimeField(auto_now=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Resultado Preliminar SAEB'
        verbose_name_plural = 'Resultados Preliminares SAEB'

        unique_together = ['escola', 'serie', 'ano']

        ordering = ['-ano', 'escola__nome']

        indexes = [
            models.Index(fields=['ano']),
            models.Index(fields=['escola', 'ano']),
            models.Index(fields=['ano', 'serie']),
        ]

    def __str__(self):
        return f"{self.escola.nome} - {self.serie} - {self.ano}"

    # ----------------------------
    # 🔢 Cálculos
    # ----------------------------
    def calcular_taxa_participacao(self):
        if self.alunos_previstos > 0:
            return round((self.alunos_avaliados / self.alunos_previstos) * 100, 2)
        return 0

    def calcular_media_geral(self):
        if self.media_lp is not None and self.media_mt is not None:
            return round((self.media_lp + self.media_mt) / 2, 2)
        return None

    # ----------------------------
    # 🛑 Validações fortes
    # ----------------------------
    def clean(self):
        erros = {}

        if self.alunos_avaliados > self.alunos_previstos:
            erros['alunos_avaliados'] = 'Não pode ser maior que alunos previstos.'

        if self.ano < 2000 or self.ano > 2100:
            erros['ano'] = 'Ano inválido.'

        if erros:
            raise ValidationError(erros)

    # ----------------------------
    # 💾 Save inteligente
    # ----------------------------
    def save(self, *args, **kwargs):

        # Validação completa antes de salvar
        self.full_clean()

        # Calcula taxa automaticamente
        self.taxa_participacao = self.calcular_taxa_participacao()

        # Calcula média geral
        self.media_geral = self.calcular_media_geral()

        super().save(*args, **kwargs)


from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal


class ResultPreliminarSaeb_2025(models.Model):
    escola = models.ForeignKey(
        'Escola',
        on_delete=models.CASCADE,
        related_name='resultados_preliminares_2025'
    )

    serie = models.ForeignKey(
        'Serie',
        on_delete=models.CASCADE
    )

    ano = models.PositiveIntegerField()

    alunos_previstos = models.PositiveIntegerField(
        validators=[MinValueValidator(0)]
    )

    alunos_avaliados = models.PositiveIntegerField(
        validators=[MinValueValidator(0)]
    )

    taxa_participacao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    taxa_aprovacao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    media_lp = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    media_mt = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    media_geral = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    ideb_estimado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['escola', 'serie', 'ano']
        ordering = ['-ano']

    def __str__(self):
        return f"{self.escola} - {self.ano}"

    # ----------------------------
    # 📊 LIMITES SAEB
    # ----------------------------
    LIMITES_SAEB = {
        "5": {
            "mt": (Decimal('60'), Decimal('322')),
            "lp": (Decimal('49'), Decimal('324')),
        },
        "9": {
            "mt": (Decimal('100'), Decimal('400')),
            "lp": (Decimal('100'), Decimal('400')),
        }
    }

    # ----------------------------
    # 🔢 CÁLCULOS
    # ----------------------------
    def calcular_taxa_participacao(self):
        if self.alunos_previstos and self.alunos_previstos > 0:
            return round(
                (Decimal(self.alunos_avaliados) / Decimal(self.alunos_previstos)) * 100,
                2
            )
        return Decimal('0.00')

    def calcular_nota_padronizada(self, proficiencia, limite_inferior, limite_superior):
        if proficiencia is None:
            return None

        if limite_superior == limite_inferior:
            return None

        return (
            (Decimal(proficiencia) - limite_inferior) /
            (limite_superior - limite_inferior)
        ) * Decimal('10')

    def obter_limites(self):
        nome_serie = str(self.serie).lower()

        if "5" in nome_serie:
            return self.LIMITES_SAEB["5"]

        if "9" in nome_serie:
            return self.LIMITES_SAEB["9"]

        return None

    def calcular_media_padronizada(self):
        if self.media_lp is None or self.media_mt is None:
            return None

        limites = self.obter_limites()
        if not limites:
            return None

        mt_inf, mt_sup = limites["mt"]
        lp_inf, lp_sup = limites["lp"]

        nota_mt = self.calcular_nota_padronizada(self.media_mt, mt_inf, mt_sup)
        nota_lp = self.calcular_nota_padronizada(self.media_lp, lp_inf, lp_sup)

        if nota_mt is None or nota_lp is None:
            return None

        return (nota_mt + nota_lp) / Decimal('2')

    def calcular_indicador_rendimento(self):
        """
        Aceita:
        - 50   → 0.50
        - 0.50 → 0.50
        """
        if self.taxa_aprovacao is None:
            return None

        taxa = Decimal(self.taxa_aprovacao)

        if taxa <= 1:
            return taxa  # já está em proporção

        return taxa / Decimal('100')

    def calcular_ideb(self):
        N = self.calcular_media_padronizada()
        P = self.calcular_indicador_rendimento()

        if N is not None and P is not None:
            return round(N * P, 2)

        return None

    # ----------------------------
    # 🛑 VALIDAÇÃO
    # ----------------------------
    def clean(self):
        if self.alunos_previstos is not None and self.alunos_avaliados is not None:
            if self.alunos_avaliados > self.alunos_previstos:
                raise ValidationError("Avaliados não pode ser maior que previstos.")

    # ----------------------------
    # 💾 SAVE
    # ----------------------------
    def save(self, *args, **kwargs):
        self.full_clean()

        self.taxa_participacao = self.calcular_taxa_participacao()
        self.media_geral = self.calcular_media_padronizada()
        self.ideb_estimado = self.calcular_ideb()

        super().save(*args, **kwargs)


# tabela Alfabetômetro



class Alfabetometro(models.Model):
    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name='alfabetometro_data', # Nome para acessar do lado da Escola
        verbose_name='Escola'
    )
    ano_referencia = models.IntegerField('Ano de Referência')
    periodo = models.CharField('Período', max_length=50, blank=True, null=True,
                              help_text='Ex: 1º Semestre, 2023/2024, etc.')

    qtd_alunos_ano = models.IntegerField('Total de Alunos no Ano', default=0)
    qtd_pre_silabico = models.IntegerField('Alunos Pré-Silábicos', default=0)
    qtd_silabico = models.IntegerField('Alunos Silábicos', default=0)
    qtd_silabico_alfabetico = models.IntegerField('Alunos Silábico-Alfabéticos', default=0)
    qtd_alfabetico = models.IntegerField('Alunos Alfabéticos', default=0)

    data_registro = models.DateTimeField('Data de Registro', auto_now_add=True)

    class Meta:
        verbose_name = 'Dados do Alfabetômetro'
        verbose_name_plural = 'Dados do Alfabetômetro'
        # Garante que não haja dois registros do alfabetômetro para a mesma escola no mesmo ano/período
        unique_together = ('escola', 'ano_referencia', 'periodo')

    def __str__(self):
        periodo_str = f" ({self.periodo})" if self.periodo else ""
        return f"Alfabetômetro de {self.escola.nome} - {self.ano_referencia}{periodo_str}"

# estudantes led

# Tabela: Nível de Escrita
class NivelEscrita(models.Model):
    nome = models.CharField('Nome do Nível de Escrita', max_length=100)

    class Meta:
        verbose_name = 'Nível de Escrita'
        verbose_name_plural = 'Níveis de Escrita'
        ordering = ['nome']

    def __str__(self):
        return self.nome


# Tabela: Estudantes
class Estudante(models.Model):
    nome = models.CharField('Nome do Estudante', max_length=255)
    endereco = models.CharField('Endereço', max_length=255, blank=True, null=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True, null=True)

    escola = models.ForeignKey(
        Escola,
        on_delete=models.CASCADE,
        related_name='estudantes',
        verbose_name='Escola'
    )
    serie = models.ForeignKey(
        Serie,
        on_delete=models.CASCADE,
        related_name='estudantes',
        verbose_name='Série/Ano'
    )
    nivel_escrita = models.ForeignKey(
        NivelEscrita,
        on_delete=models.SET_NULL,
        related_name='estudantes',
        verbose_name='Nível de Escrita',
        null=True,
        blank=True
    )

    periodo = models.CharField(
        'Período',
        max_length=50,
        blank=True,
        null=True,
        help_text='Ex: Manhã, Tarde, Noite'
    )
    ano = models.PositiveIntegerField('Ano de Referência')

    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Estudante'
        verbose_name_plural = 'Estudantes'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['escola', 'serie', 'ano']),
            models.Index(fields=['nivel_escrita']),
        ]

    def __str__(self):
        return f"{self.nome} - {self.escola.nome} ({self.serie})"