from datetime import datetime
import hashlib
from peewee import *
from quinielasapp.models import BaseModel

class League(BaseModel):
    name = CharField(max_length=100)
    code = CharField(unique=True, max_length=10)
    description = TextField(null=True)
    created_by = IntegerField()  # Foreign key manual por ahora
    is_active = BooleanField(default=True)
    max_members = IntegerField(default=50)
    created_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'leagues'

class User(BaseModel):
    username = CharField(unique=True, max_length=80)
    password = CharField(max_length=255)  # Para hash SHA-256
    first_name = CharField(max_length=50, null=True)
    last_name = CharField(max_length=50, null=True)
    is_admin = BooleanField(default=False)
    current_league_id = IntegerField(null=True)  # Foreign key manual
    created_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'users'
    
    def set_password(self, password):
        """Hashea y guarda la contraseña"""
        self.password = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password):
        """Verifica si la contraseña es correcta"""
        return self.password == hashlib.sha256(password.encode()).hexdigest()
    
    @property
    def full_name(self):
        """Retorna el nombre completo"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    @property 
    def leagues(self):
        """Obtiene todas las ligas activas del usuario"""
        return [m.league for m in self.memberships.where(LeagueMembership.is_active == True)]
    
    @property
    def member_count(self):
        """Cuenta miembros activos de la liga"""
        return self.memberships.where(LeagueMembership.is_active == True).count()
    
    @property
    def active_members(self):
        """Obtiene usuarios activos de la liga"""
        return User.select().join(LeagueMembership).where(
            (LeagueMembership.league == self) & 
            (LeagueMembership.is_active == True)
        )

class LeagueMembership(BaseModel):
    user = ForeignKeyField(User, backref='memberships')
    league = ForeignKeyField(League, backref='memberships')
    joined_at = DateTimeField(default=datetime.now)
    is_active = BooleanField(default=True)
    
    class Meta:
        table_name = 'league_memberships'
        indexes = ((('user', 'league'), True),)  # Índice único

class Pick(BaseModel):
    user = ForeignKeyField(User, backref='picks')
    league = ForeignKeyField(League, backref='picks')
    week = IntegerField()
    game_id = CharField(max_length=50)
    selection = CharField(max_length=100)
    created_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'picks'
        indexes = ((('user', 'league', 'week', 'game_id'), True),)  # Índice único

class GameResult(BaseModel):
    week = IntegerField()
    game_id = CharField(max_length=50)
    winner = CharField(max_length=100)
    home_team = CharField(max_length=100, null=True)
    away_team = CharField(max_length=100, null=True)
    home_score = IntegerField(null=True)
    away_score = IntegerField(null=True)
    updated_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'game_results'

class WinnersHistory(BaseModel):
    user_id = IntegerField()  # ID del usuario ganador
    league_id = IntegerField()  # ID de la liga
    week = IntegerField()
    winner_username = CharField(max_length=80)  # Username del ganador
    score = IntegerField()  # Puntuación obtenida
    is_tie = BooleanField(default=False)  # Indica si fue empate
    declared_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'winners_history'
        indexes = ((('league_id', 'week'), False),)  # Índice para buscar por liga y semana

class SystemConfig(BaseModel):
    config_key = CharField(unique=True, max_length=50)
    config_value = TextField()
    updated_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'system_config'
    
    @classmethod
    def get_config(cls, key, default=None):
        """Helper para obtener configuración"""
        try:
            return cls.get(cls.config_key == key).config_value
        except cls.DoesNotExist:
            return default
    
    @classmethod 
    def set_config(cls, key, value):
        """Helper para guardar configuración"""
        config, created = cls.get_or_create(
            config_key=key,
            defaults={'config_value': str(value)}
        )
        if not created:
            config.config_value = str(value)
            config.updated_at = datetime.now()
            config.save()
        return config