"""
Servicios de base de datos para la aplicación.
Migra las funciones helper que estaban en app.py usando raw SQL.
"""

from datetime import datetime
import hashlib
from quinielasapp.models.models import *
from peewee import fn
import string
import random

def create_default_admin():
    """Crea el usuario administrador por defecto si no existe"""
    try:
        admin = User.get(User.is_admin == True)
        return admin
    except User.DoesNotExist:
        admin = User(
            username='admin',
            is_admin=True
        )
        admin.set_password('QuinielasNFL2024!')  # CAMBIAR EN PRODUCCIÓN
        admin.save()
        return admin

def initialize_system_config():
    """Inicializa la configuración del sistema"""
    # Configuración de semana actual
    SystemConfig.set_config('current_week', '4')
    SystemConfig.set_config('picks_locked', '0')

def get_current_week():
    """Obtiene la semana actual desde la configuración"""
    return int(SystemConfig.get_config('current_week', 1))

def set_current_week(week):
    """Actualiza la semana actual"""
    SystemConfig.set_config('current_week', str(week))

def get_system_config():
    """Obtiene toda la configuración del sistema como dict"""
    configs = {}
    for config in SystemConfig.select():
        configs[config.config_key] = config.config_value
    return configs

def generate_league_code():
    """Genera un código único para una liga"""
    letters = string.ascii_uppercase
    while True:
        code = ''.join(random.choices(letters, k=6))
        # Verificar que no existe
        if not League.select().where(League.code == code).exists():
            return code

def join_league_by_code(user_id, league_code):
    """Permite a un usuario unirse a una liga usando un código"""
    try:
        # Verificar que la liga existe y está activa
        league = League.get((League.code == league_code) & (League.is_active == True))
        
        # Verificar que el usuario existe
        user = User.get_by_id(user_id)
        
        # Verificar si ya está en la liga
        existing = LeagueMembership.select().where(
            (LeagueMembership.user == user) & 
            (LeagueMembership.league == league)
        ).first()
        
        if existing:
            if existing.is_active:
                return {'success': False, 'error': 'Ya eres miembro de esta liga'}
            else:
                # Reactivar membresía
                existing.is_active = True
                existing.joined_at = datetime.now()
                existing.save()
                return {'success': True, 'league_name': league.name}
        
        # Verificar límite de miembros
        if league.member_count >= league.max_members:
            return {'success': False, 'error': 'La liga ha alcanzado el límite de miembros'}
        
        # Crear nueva membresía
        LeagueMembership.create(
            user=user,
            league=league,
            joined_at=datetime.now()
        )
        
        return {'success': True, 'league_name': league.name}
        
    except League.DoesNotExist:
        return {'success': False, 'error': 'Liga no encontrada o inactiva'}
    except User.DoesNotExist:
        return {'success': False, 'error': 'Usuario no encontrado'}
    except Exception as e:
        return {'success': False, 'error': f'Error interno: {str(e)}'}

def get_user_leagues(user_id):
    """
    Obtiene todas las ligas de un usuario. 
    Si es admin, obtiene todas las ligas.
    """
    try:
        user = User.get_by_id(user_id)
        
        if user.is_admin:
            # Admin ve todas las ligas
            leagues = League.select().order_by(League.created_at.desc())
        else:
            # Usuario normal ve solo sus ligas
            leagues = (League.select()
                      .join(LeagueMembership)
                      .where((LeagueMembership.user == user) & 
                             (LeagueMembership.is_active == True))
                      .order_by(LeagueMembership.joined_at.desc()))
        
        return list(leagues)
        
    except User.DoesNotExist:
        return []

def get_user_standings_by_league(league_id):
    """Obtiene el ranking de usuarios en una liga específica para la semana actual"""
    try:
        from quinielasapp.models.models import LeagueMembership
        from shared_utils import get_current_week
        
        # Obtener la semana actual
        current_week = get_current_week()
        
        # Obtener usuarios de la liga
        users = User.select().join(LeagueMembership).where(
            (LeagueMembership.league_id == league_id) & 
            (LeagueMembership.is_active == True)
        )
        
        standings_data = []
        
        for user in users:
            # Contar picks totales del usuario en esta liga y semana actual
            total_picks = Pick.select().where(
                (Pick.user == user) & 
                (Pick.league_id == league_id) &
                (Pick.week == current_week)
            ).count()
            
            if total_picks == 0:
                continue
                
            # Obtener resultados de juegos de la semana actual
            results = GameResult.select().where(GameResult.week == current_week)
            results_dict = {result.game_id: result for result in results}
            
            # Contar picks correctos de la semana actual
            correct_picks = 0
            user_picks = Pick.select().where(
                (Pick.user == user) & 
                (Pick.league_id == league_id) &
                (Pick.week == current_week)
            )
            
            for pick in user_picks:
                try:
                    if pick.game_id in results_dict:
                        result = results_dict[pick.game_id]
                        
                        # Manejar diferentes formatos de pick.selection
                        if isinstance(pick.selection, dict):
                            pick_value = pick.selection.get('abbreviation', pick.selection.get('name', ''))
                        elif isinstance(pick.selection, str):
                            # Intentar parsear JSON si parece un diccionario
                            import json
                            if pick.selection.startswith('{') and pick.selection.endswith('}'):
                                json_string = pick.selection.replace("'", '"')
                                picked_team_data = json.loads(json_string)
                                pick_value = picked_team_data.get('abbreviation', picked_team_data.get('name', ''))
                            else:
                                pick_value = pick.selection
                        else:
                            pick_value = str(pick.selection)
                        
                        if pick_value == result.winner:
                            correct_picks += 1
                except Exception as pick_error:
                    print(f"Error processing pick for user {user.username}: {pick_error}")
                    continue
            
            percentage = (correct_picks / total_picks * 100) if total_picks > 0 else 0
            
            standings_data.append({
                'username': user.username,
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'first_name': user.first_name,  # Para compatibilidad con template
                'last_name': user.last_name,    # Para compatibilidad con template
                'correct_picks': correct_picks,
                'total_picks': total_picks,
                'percentage': percentage,
                'total_score': correct_picks,  # Para admin modal
                'score': correct_picks  # Para template standings_partial.html
            })
        
        # Ordenar por total_score descendente
        standings_data.sort(key=lambda x: x['total_score'], reverse=True)
        return standings_data
        
    except Exception as e:
        import traceback
        print(f"Error getting standings: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return []

def check_picks_deadline():
    """Verifica si los picks están bloqueados"""
    return SystemConfig.get_config('picks_locked', '0') == '1'