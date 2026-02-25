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
    
    telefone_extraido = models.CharField('Telefone Extraído', max_length=20, blank=True, null=True)
    dados = models.JSONField('Dados Adicionais', null=True, blank=True)
    
    def __str__(self):
        return f"{self.nome} (ID: {self.id})"


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