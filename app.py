"""
Aplicación Flask para Quinielas NFL - Versión con Peewee ORM
"""

import os
import hashlib
import requests
import urllib3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Configuración
from config import config
from quinielasapp.models import database
from quinielasapp.models.models import User, League, LeagueMembership, Pick, GameResult, SystemConfig, WinnersHistory
from quinielasapp.services.database_service import (
    get_current_week, set_current_week, get_system_config,
    generate_league_code, join_league_by_code, get_user_leagues,
    get_user_standings_by_league, check_picks_deadline
)
from shared_utils import get_espn_nfl_data, get_mock_nfl_data, hash_password

# Blueprints
from blueprints.admin_routes import admin_bp

# D        return render_template('games_status_with_picks.html',abilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración de la aplicación
app = Flask(__name__)

# Cargar configuración según el entorno
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

# Registrar blueprints
app.register_blueprint(admin_bp)

# Inicializar conexión a base de datos
def initialize_database():
    """Inicializar conexión a base de datos"""
    try:
        if database.is_closed():
            database.connect()
        print("✅ Conectado a PostgreSQL con Peewee")
    except Exception as e:
        print(f"❌ Error conectando a base de datos: {e}")

@app.before_request
def before_request():
    """Asegurar conexión antes de cada request"""
    if database.is_closed():
        database.connect()

@app.teardown_appcontext
def close_database_connection(exception):
    """Cerrar conexión a base de datos después de cada request"""
    if not database.is_closed():
        database.close()

# Inicializar la base de datos al importar el módulo
initialize_database()

# =============================================================================
# FUNCIONES HELPER MIGRADAS A shared_utils.py
# =============================================================================

def get_user_standings():
    """
    Obtiene el ranking general de usuarios (para admin) usando Peewee.
    """
    try:
        from peewee import fn
        
        # Obtener todos los usuarios no-admin
        users = User.select().where(User.is_admin == False)
        standings_data = []
        
        for user in users:
            # Contar picks totales y correctos
            total_picks = Pick.select().where(Pick.user == user).count()
            
            if total_picks == 0:
                continue
                
            # Contar picks correctos manejando tanto strings como diccionarios
            correct_picks = 0
            user_picks = Pick.select(Pick, GameResult).join(
                GameResult, 
                on=((Pick.game_id == GameResult.game_id) & (Pick.week == GameResult.week)),
                join_type='INNER'
            ).where(Pick.user == user)
            
            for pick in user_picks:
                # Manejar pick.selection como string o diccionario
                if hasattr(pick, 'gameresult'):
                    try:
                        if isinstance(pick.selection, dict):
                            pick_value = pick.selection.get('abbreviation', pick.selection.get('name', ''))
                        else:
                            pick_value = str(pick.selection)
                        
                        if pick_value == pick.gameresult.winner:
                            correct_picks += 1
                    except Exception as pick_error:
                        print(f"Error processing pick for user {user.username}: {pick_error}")
                        continue
            
            percentage = (correct_picks / total_picks * 100) if total_picks > 0 else 0
            
            standings_data.append({
                'username': user.username,
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'total_score': correct_picks,
                'correct_picks': correct_picks,
                'total_picks': total_picks,
                'percentage': percentage,
                'score': correct_picks,  # Para compatibilidad con template
                'first_name': user.first_name,
                'last_name': user.last_name
            })
        
        # Ordenar por score descendente
        standings_data.sort(key=lambda x: x['total_score'], reverse=True)
        return standings_data
        
    except Exception as e:
        import traceback
        print(f"Error getting standings: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return []

# =============================================================================
# RUTAS DE LA APLICACIÓN (MIGRANDO GRADUALMENTE)
# =============================================================================

@app.route('/')
def home():
    """Página principal - mantiene la misma lógica"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obtener usuario usando Peewee
        user = User.get_by_id(session['user_id'])
        
        # Si es admin, redirigir directamente al panel de administración
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        
        # Obtener ligas del usuario
        user_leagues = get_user_leagues(session['user_id'])
        
        if not user_leagues:
            # Usuario sin ligas - redirigir a página para unirse
            return redirect(url_for('join_league_route'))
        
        # Seleccionar liga actual
        current_league_id = session.get('current_league_id')
        
        if current_league_id:
            try:
                current_league = League.get_by_id(current_league_id)
                if current_league not in user_leagues and not user.is_admin:
                    # Liga no válida para el usuario
                    current_league = user_leagues[0] if user_leagues else None
                    session['current_league_id'] = current_league.id if current_league else None
            except League.DoesNotExist:
                current_league = user_leagues[0] if user_leagues else None
                session['current_league_id'] = current_league.id if current_league else None
        else:
            current_league = user_leagues[0] if user_leagues else None
            session['current_league_id'] = current_league.id if current_league else None
        
        # Obtener datos de juegos
        current_week = get_current_week()
        games = get_espn_nfl_data(current_week)
        
        # Obtener picks del usuario para la semana actual
        user_picks = {}
        picks_stats = {'total': 0, 'correct': 0, 'incorrect': 0, 'pending': 0}
        
        if current_league:
            picks = Pick.select().where(
                (Pick.user == user) & 
                (Pick.league_id == current_league.id) & 
                (Pick.week == current_week)
            )
            user_picks = {pick.game_id: pick.selection for pick in picks}
            
            # Calcular estadísticas de picks
            results = GameResult.select().where(GameResult.week == current_week)
            results_dict = {result.game_id: result for result in results}
            
            for pick in picks:
                picks_stats['total'] += 1
                
                if pick.game_id in results_dict:
                    result = results_dict[pick.game_id]
                    
                    # Procesar pick.selection para manejar diferentes formatos
                    picked_team_data = None
                    if isinstance(pick.selection, dict):
                        picked_team_data = pick.selection
                    elif isinstance(pick.selection, str):
                        try:
                            import json
                            if pick.selection.startswith('{') and pick.selection.endswith('}'):
                                json_string = pick.selection.replace("'", '"')
                                picked_team_data = json.loads(json_string)
                            else:
                                picked_team_data = {'name': pick.selection, 'abbreviation': pick.selection}
                        except (json.JSONDecodeError, ValueError):
                            picked_team_data = {'name': pick.selection, 'abbreviation': pick.selection}
                    else:
                        selection_str = str(pick.selection)
                        picked_team_data = {'name': selection_str, 'abbreviation': selection_str}
                    
                    picked_team_abbr = picked_team_data.get('abbreviation', '')
                    picked_team_name = picked_team_data.get('name', '')
                    
                    if picked_team_abbr == result.winner or picked_team_name == result.winner:
                        picks_stats['correct'] += 1
                    else:
                        picks_stats['incorrect'] += 1
                else:
                    picks_stats['pending'] += 1
        
        # Obtener standings de la liga actual
        standings = []
        if current_league:
            standings = get_user_standings_by_league(current_league.id)
        
        # Obtener historial de ganadores (últimas 5 semanas)
        winners_history = []
        try:
            from quinielasapp.models.models import WinnersHistory
            if current_league:
                recent_winners = WinnersHistory.select().where(
                    WinnersHistory.league_id == current_league.id
                ).order_by(WinnersHistory.week.desc()).limit(5)
                
                winners_history = [{
                    'username': winner.winner_username,
                    'week': winner.week,
                    'score': winner.score,
                    'is_tie': winner.is_tie
                } for winner in recent_winners]
        except Exception as e:
            print(f"Error loading winners history: {e}")
            winners_history = []
        
        # Calcular número de participantes en la liga actual
        users_count = 0
        if current_league:
            from quinielasapp.models.models import LeagueMembership
            users_count = User.select().join(LeagueMembership).where(
                (LeagueMembership.league_id == current_league.id) & 
                (LeagueMembership.is_active == True)
            ).count()
        
        # Verificar si el usuario ya envió sus picks para la semana actual
        user_has_submitted_picks = False
        if current_league:
            total_games = len(games)
            user_picks_count = Pick.select().where(
                (Pick.user == user) & 
                (Pick.league_id == current_league.id) & 
                (Pick.week == current_week)
            ).count()
            user_has_submitted_picks = (user_picks_count >= total_games)
        
        # Verificar si los picks están bloqueados
        picks_locked = check_picks_deadline()
        
        return render_template('index.html',
                             games=games,
                             user_picks=user_picks,
                             current_week=current_week,
                             standings=standings[:10],  # Top 10
                             user_leagues=user_leagues,
                             current_league=current_league,
                             is_admin=user.is_admin,
                             picks_locked=picks_locked,
                             picks_stats=picks_stats,
                             winners_history=winners_history,
                             users_count=users_count,
                             user_has_submitted_picks=user_has_submitted_picks)
                             
    except User.DoesNotExist:
        # Usuario no existe, limpiar sesión
        session.clear()
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Error in home route: {e}")
        flash('Error interno del servidor', 'error')
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login de usuarios usando Peewee"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Todos los campos son requeridos', 'error')
            return render_template('login.html')
        
        try:
            # Buscar usuario con Peewee
            user = User.get(User.username == username)
            
            # Verificar contraseña
            if user.check_password(password):
                # Login exitoso
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                
                # Si es admin, no necesita liga
                if not user.is_admin:
                    # Obtener ligas del usuario para establecer la actual
                    user_leagues = get_user_leagues(user.id)
                    if user_leagues:
                        session['current_league_id'] = user_leagues[0].id
                
                flash(f'Bienvenido, {user.username}!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Credenciales incorrectas', 'error')
                
        except User.DoesNotExist:
            flash('Usuario no encontrado', 'error')
        except Exception as e:
            print(f"Error in login: {e}")
            flash('Error interno del servidor', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de nuevos usuarios usando Peewee"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        league_code = request.form.get('league_code', '').strip().upper()
        
        # Validaciones básicas
        if not username:
            flash('El nombre de usuario es requerido', 'error')
            return render_template('register.html')
        
        if len(username) < 3:
            flash('El nombre de usuario debe tener al menos 3 caracteres', 'error')
            return render_template('register.html')
        
        if not password:
            flash('La contraseña es requerida', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('register.html')
        
        if not league_code:
            flash('El código de liga es requerido', 'error')
            return render_template('register.html')
        
        try:
            # Verificar si el usuario ya existe
            if User.select().where(User.username == username).exists():
                flash('El nombre de usuario ya existe', 'error')
                return render_template('register.html')
            
            # Verificar que la liga existe
            try:
                league = League.get((League.code == league_code) & (League.is_active == True))
            except League.DoesNotExist:
                flash('Código de liga inválido o liga inactiva', 'error')
                return render_template('register.html')
            
            # Crear el usuario
            user = User(
                username=username,
                first_name=first_name if first_name else None,
                last_name=last_name if last_name else None,
                is_admin=False
            )
            user.set_password(password)
            
            # Guardar usuario y agregar a liga con transacción
            with database.atomic():
                user.save()
                # Agregar a la liga
                LeagueMembership.create(
                    user=user,
                    league=league,
                    joined_at=datetime.now(),
                    is_active=True
                )
            
            flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Error during registration: {e}")
            flash('Error interno del servidor', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout del usuario"""
    session.clear()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('login'))

@app.route('/switch_league', methods=['POST'])
def switch_league():
    """Cambiar liga actual del usuario"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No estás logueado'}), 401
    
    try:
        data = request.get_json()
        league_id = data.get('league_id')
        
        if not league_id:
            return jsonify({'success': False, 'message': 'Liga no especificada'}), 400
        
        user = User.get_by_id(session['user_id'])
        
        # Verificar si el usuario pertenece a esta liga o es admin
        if not user.is_admin:
            membership = LeagueMembership.select().where(
                (LeagueMembership.user == user) & 
                (LeagueMembership.league_id == league_id) & 
                (LeagueMembership.is_active == True)
            ).first()
            
            if not membership:
                return jsonify({'success': False, 'message': 'No perteneces a esta liga'}), 403
        
        # Cambiar liga actual en la sesión
        session['current_league_id'] = int(league_id)
        
        return jsonify({'success': True, 'message': 'Liga cambiada exitosamente'})
        
    except Exception as e:
        print(f"Error switching league: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500

@app.route('/picks', methods=['GET', 'POST'])
def picks_form():
    """Formulario para hacer picks usando Peewee"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user = User.get_by_id(session['user_id'])
        current_week = get_current_week()
        
        # Obtener liga actual
        current_league_id = session.get('current_league_id')
        if not current_league_id:
            user_leagues = get_user_leagues(user.id)
            if user_leagues:
                current_league_id = user_leagues[0].id
                session['current_league_id'] = current_league_id
            else:
                flash('Debes unirte a una liga primero', 'error')
                return redirect(url_for('home'))
        
        current_league = League.get_by_id(current_league_id)
        
        if request.method == 'POST':
            # Verificar si los picks están bloqueados
            if check_picks_deadline():
                flash('Los picks están bloqueados para esta semana', 'error')
                return redirect(url_for('picks_form'))
            
            # Procesar picks
            games_data = request.form
            picks_saved = 0
            
            for key, selection in games_data.items():
                if key.startswith('game_') and selection:
                    game_id = key.replace('game_', '')
                    
                    # Usar get_or_create para actualizar picks existentes con transacción
                    with database.atomic():
                        pick, created = Pick.get_or_create(
                            user=user,
                            league=current_league,
                            week=current_week,
                            game_id=game_id,
                            defaults={'selection': selection}
                        )
                        
                        if not created:
                            # Actualizar pick existente
                            pick.selection = selection
                            pick.save()
                    
                    picks_saved += 1
            
            flash(f'Se guardaron {picks_saved} picks para la semana {current_week}', 'success')
            return redirect(url_for('home'))
        
        # GET - Mostrar formulario
        games = get_espn_nfl_data(current_week)
        
        # Obtener picks actuales del usuario
        current_picks = Pick.select().where(
            (Pick.user == user) &
            (Pick.league_id == current_league.id) &
            (Pick.week == current_week)
        )
        user_picks = {pick.game_id: pick.selection for pick in current_picks}
        
        # Verificar si los picks están bloqueados
        picks_locked = check_picks_deadline()
        
        return render_template('picks_form.html',
                             games=games,
                             user_picks=user_picks,
                             current_week=current_week,
                             current_league=current_league,
                             picks_locked=picks_locked)
                             
    except Exception as e:
        print(f"Error in picks_form: {e}")
        flash('Error interno del servidor', 'error')
        return redirect(url_for('home'))

@app.route('/standings')
def standings():
    """Página de standings usando Peewee"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user = User.get_by_id(session['user_id'])
        current_league_id = session.get('current_league_id')
        
        if not current_league_id and not user.is_admin:
            return render_template('standings_partial.html', standings=[])
        
        if user.is_admin:
            # Admin ve standings generales
            standings = get_user_standings()
        else:
            # Usuario ve standings de su liga
            standings = get_user_standings_by_league(current_league_id)
        
        return render_template('standings_partial.html', standings=standings)
        
    except Exception as e:
        print(f"Error in standings: {e}")
        return render_template('standings_partial.html', standings=[])

@app.route('/picks_grid')
def picks_grid():
    """Grid de picks de todos los usuarios"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user = User.get_by_id(session['user_id'])
        current_week = get_current_week()
        current_league_id = session.get('current_league_id')
        
        if not current_league_id and not user.is_admin:
            return render_template('picks_grid.html', users=[], games=[], picks_matrix={})
        
        # Obtener juegos de la semana
        games = get_espn_nfl_data(current_week)
        
        # Obtener usuarios y picks
        if user.is_admin and not current_league_id:
            # Admin sin liga específica - ver todos
            users = User.select().where(User.is_admin == False)
            picks = Pick.select().where(Pick.week == current_week)
        else:
            # Liga específica
            league = League.get_by_id(current_league_id)
            # Usar la consulta directamente en lugar de la propiedad
            users = User.select().join(LeagueMembership).where(
                (LeagueMembership.league_id == league.id) & 
                (LeagueMembership.is_active == True)
            )
            picks = Pick.select().where(
                (Pick.week == current_week) & 
                (Pick.league_id == league.id)
            )
        
        # Crear matriz de picks
        picks_matrix = {}
        for pick in picks:
            user_id = pick.user.id
            game_id = pick.game_id
            if user_id not in picks_matrix:
                picks_matrix[user_id] = {}
            
            # Procesar pick.selection para manejar diferentes formatos
            picked_team_data = None
            
            if isinstance(pick.selection, dict):
                picked_team_data = pick.selection
            elif isinstance(pick.selection, str):
                # Intentar parsear como JSON si parece un diccionario
                try:
                    import json
                    if pick.selection.startswith('{') and pick.selection.endswith('}'):
                        # Convertir comillas simples a dobles para JSON válido
                        json_string = pick.selection.replace("'", '"')
                        picked_team_data = json.loads(json_string)
                    else:
                        # Es solo un string simple (abreviatura o nombre)
                        picked_team_data = {'name': pick.selection, 'abbreviation': pick.selection}
                except (json.JSONDecodeError, ValueError):
                    # No es JSON válido, tratar como string simple
                    picked_team_data = {'name': pick.selection, 'abbreviation': pick.selection}
            else:
                # Otros tipos, convertir a string
                selection_str = str(pick.selection)
                picked_team_data = {'name': selection_str, 'abbreviation': selection_str}
            
            selection_name = picked_team_data.get('name', '')
            selection_abbr = picked_team_data.get('abbreviation', '')
            
            picks_matrix[user_id][game_id] = {
                'selection': {
                    'name': selection_name,
                    'abbreviation': selection_abbr
                },
                'is_correct': None  # Se calculará si hay resultados
            }
        
        # Obtener resultados de juegos para calcular is_correct
        results = GameResult.select().where(GameResult.week == current_week)
        results_dict = {result.game_id: result for result in results}
        
        # Calcular is_correct para cada pick
        for user_id in picks_matrix:
            for game_id in picks_matrix[user_id]:
                if game_id in results_dict:
                    result = results_dict[game_id]
                    pick_data = picks_matrix[user_id][game_id]
                    picked_team_abbr = pick_data['selection']['abbreviation']
                    picked_team_name = pick_data['selection']['name']
                    
                    # Comparar con el ganador del resultado
                    if picked_team_abbr == result.winner or picked_team_name == result.winner:
                        picks_matrix[user_id][game_id]['is_correct'] = True
                    else:
                        picks_matrix[user_id][game_id]['is_correct'] = False
        
        return render_template('picks_grid.html', 
                             users=users, 
                             games=games, 
                             picks_matrix=picks_matrix,
                             current_week=current_week)
                             
    except Exception as e:
        print(f"Error in picks_grid: {e}")
        return render_template('picks_grid.html', users=[], games=[], picks_matrix={})

@app.route('/picks_grid_partial')
def picks_grid_partial():
    """Versión parcial del grid para HTMX"""
    if 'user_id' not in session:
        return render_template('picks_grid_partial.html', users=[], games=[], picks_matrix={})
    
    try:
        user = User.get_by_id(session['user_id'])
        current_week = get_current_week()
        current_league_id = session.get('current_league_id')
        
        if not current_league_id and not user.is_admin:
            return render_template('picks_grid_partial.html', users=[], games=[], picks_matrix={})
        
        games = get_espn_nfl_data(current_week)
        
        if user.is_admin and not current_league_id:
            users = User.select().where(User.is_admin == False)
            picks = Pick.select().where(Pick.week == current_week)
        else:
            league = League.get_by_id(current_league_id)
            # Usar la consulta directamente en lugar de la propiedad
            users = User.select().join(LeagueMembership).where(
                (LeagueMembership.league_id == league.id) & 
                (LeagueMembership.is_active == True)
            )
        picks = Pick.select().where(
            (Pick.week == current_week) & 
            (Pick.league_id == league.id)
        )
        
        picks_matrix = {}
        for pick in picks:
            user_id = pick.user.id
            game_id = pick.game_id
            if user_id not in picks_matrix:
                picks_matrix[user_id] = {}
            
            # Procesar pick.selection para manejar diferentes formatos
            picked_team_data = None
            
            if isinstance(pick.selection, dict):
                picked_team_data = pick.selection
            elif isinstance(pick.selection, str):
                # Intentar parsear como JSON si parece un diccionario
                try:
                    import json
                    if pick.selection.startswith('{') and pick.selection.endswith('}'):
                        # Convertir comillas simples a dobles para JSON válido
                        json_string = pick.selection.replace("'", '"')
                        picked_team_data = json.loads(json_string)
                    else:
                        # Es solo un string simple (abreviatura o nombre)
                        picked_team_data = {'name': pick.selection, 'abbreviation': pick.selection}
                except (json.JSONDecodeError, ValueError):
                    # No es JSON válido, tratar como string simple
                    picked_team_data = {'name': pick.selection, 'abbreviation': pick.selection}
            else:
                # Otros tipos, convertir a string
                selection_str = str(pick.selection)
                picked_team_data = {'name': selection_str, 'abbreviation': selection_str}
            
            selection_name = picked_team_data.get('name', '')
            selection_abbr = picked_team_data.get('abbreviation', '')
            
            picks_matrix[user_id][game_id] = {
                'selection': {
                    'name': selection_name,
                    'abbreviation': selection_abbr
                },
                'is_correct': None  # Se calculará si hay resultados
            }
        
        # Obtener resultados de juegos para calcular is_correct
        results = GameResult.select().where(GameResult.week == current_week)
        results_dict = {result.game_id: result for result in results}
        
        # Calcular is_correct para cada pick
        for user_id in picks_matrix:
            for game_id in picks_matrix[user_id]:
                if game_id in results_dict:
                    result = results_dict[game_id]
                    pick_data = picks_matrix[user_id][game_id]
                    picked_team_abbr = pick_data['selection']['abbreviation']
                    picked_team_name = pick_data['selection']['name']
                    
                    # Comparar con el ganador del resultado
                    if picked_team_abbr == result.winner or picked_team_name == result.winner:
                        picks_matrix[user_id][game_id]['is_correct'] = True
                    else:
                        picks_matrix[user_id][game_id]['is_correct'] = False
        
        return render_template('picks_grid_partial.html', 
                             users=users, 
                             games=games, 
                             picks_matrix=picks_matrix)
                             
    except Exception as e:
        print(f"Error in picks_grid_partial: {e}")
        return render_template('picks_grid_partial.html', users=[], games=[], picks_matrix={})

@app.route('/user_picks_status')
def user_picks_status():
    """Estado de picks del usuario"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user = User.get_by_id(session['user_id'])
        current_week = get_current_week()
        
        user_leagues = get_user_leagues(user.id)
        leagues_status = []
        
        for league in user_leagues:
            # Contar picks del usuario en esta liga para la semana actual
            picks_count = Pick.select().where(
                (Pick.user == user) & 
                (Pick.league_id == league.id) & 
                (Pick.week == current_week)
            ).count()
            
            # Contar total de juegos disponibles
            games = get_espn_nfl_data(current_week)
            total_games = len(games)
            
            leagues_status.append({
                'league': league,
                'picks_made': picks_count,
                'total_games': total_games,
                'completed': picks_count == total_games
            })
        
        return render_template('user_picks_status.html',
                             leagues_status=leagues_status,
                             current_week=current_week)
                             
    except Exception as e:
        print(f"Error in user_picks_status: {e}")
        return render_template('user_picks_status.html', leagues_status=[], current_week=0)

@app.route('/join_league', methods=['GET', 'POST'])
def join_league_route():
    """Permite al usuario unirse a una liga con código"""
    if 'user_id' not in session:
        flash('Debes iniciar sesión', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('join_league_modal.html')
    
    # POST - Unirse a liga
    league_code = request.form.get('code', '').strip().upper()
    
    if not league_code:
        return render_template('toast_partial.html', 
                             category='error', 
                             message='El código de liga es requerido')
    
    result = join_league_by_code(session['user_id'], league_code)
    
    if result['success']:
        return render_template('toast_partial.html', 
                             category='success', 
                             message=f'Te has unido exitosamente a "{result["league_name"]}"')
    else:
        return render_template('toast_partial.html', 
                             category='error', 
                             message=result['error'])

@app.route('/games_status')
def games_status():
    """Estado de juegos con picks"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user = User.get_by_id(session['user_id'])
        current_week = get_current_week()
        games = get_espn_nfl_data(current_week)
        
        # Obtener resultados si existen
        results = GameResult.select().where(GameResult.week == current_week)
        results_dict = {result.game_id: result for result in results}
        
        # Obtener picks del usuario para esta semana
        user_picks_by_game = {}
        
        # Solo obtener picks si el usuario no es admin
        if not user.is_admin:
            current_league_id = session.get('current_league_id')
            if current_league_id:
                current_league = League.get_by_id(current_league_id)
                picks = Pick.select().where(
                    (Pick.user == user) & 
                    (Pick.league_id == current_league.id) & 
                    (Pick.week == current_week)
                )
                
                for pick in picks:
                    game_id = pick.game_id
                    
                    # Procesar pick.selection para manejar diferentes formatos
                    picked_team_data = None
                    
                    if isinstance(pick.selection, dict):
                        picked_team_data = pick.selection
                    elif isinstance(pick.selection, str):
                        # Intentar parsear como JSON si parece un diccionario
                        try:
                            import json
                            if pick.selection.startswith('{') and pick.selection.endswith('}'):
                                # Convertir comillas simples a dobles para JSON válido
                                json_string = pick.selection.replace("'", '"')
                                picked_team_data = json.loads(json_string)
                            else:
                                # Es solo un string simple (abreviatura o nombre)
                                picked_team_data = {'name': pick.selection, 'abbreviation': pick.selection}
                        except (json.JSONDecodeError, ValueError):
                            # No es JSON válido, tratar como string simple
                            picked_team_data = {'name': pick.selection, 'abbreviation': pick.selection}
                    else:
                        # Otros tipos, convertir a string
                        selection_str = str(pick.selection)
                        picked_team_data = {'name': selection_str, 'abbreviation': selection_str}
                    
                    picked_team_name = picked_team_data.get('name', '')
                    picked_team_abbr = picked_team_data.get('abbreviation', '')
                    picked_team_for_comparison = picked_team_abbr or picked_team_name
                    
                    user_picks_by_game[game_id] = {
                        'picked_team': {
                            'name': picked_team_name,
                            'abbreviation': picked_team_abbr
                        },
                        'result': None  # Se calculará si hay resultado
                    }
                    
                    # Si hay resultado, determinar si el pick fue correcto
                    if game_id in results_dict:
                        result = results_dict[game_id]
                        if picked_team_for_comparison == result.winner:
                            user_picks_by_game[game_id]['result'] = 'correct'
                        else:
                            user_picks_by_game[game_id]['result'] = 'incorrect'
        
        # Agregar resultados a los juegos
        for game in games:
            game_id = game['id']
            if game_id in results_dict:
                result = results_dict[game_id]
                game['result'] = {
                    'winner': result.winner,
                    'home_score': result.home_score,
                    'away_score': result.away_score
                }
        
        # Obtener última actualización
        from datetime import datetime, timezone, timedelta
        try:
            from zoneinfo import ZoneInfo
            cdmx_tz = ZoneInfo('America/Mexico_City')
        except ImportError:
            # Fallback para sistemas sin zoneinfo
            from datetime import timezone
            cdmx_tz = timezone(timedelta(hours=-6))  # CDMX es UTC-6
        
        # Convertir horarios a CDMX y generar timestamp de última actualización
        utc_now = datetime.now(timezone.utc)
        last_update_mex = utc_now.astimezone(cdmx_tz).strftime('%d/%m/%Y %I:%M %p CDMX')
        
        # Convertir horarios de juegos a CDMX
        for game in games:
            if game.get('date'):
                try:
                    # Parsear fecha ISO
                    game_date = datetime.fromisoformat(game['date'].replace('Z', '+00:00'))
                    # Convertir a CDMX
                    game_date_mex = game_date.astimezone(cdmx_tz)
                    
                    # Obtener día de la semana en español
                    dias_semana = {
                        0: 'Lun', 1: 'Mar', 2: 'Mié', 3: 'Jue', 
                        4: 'Vie', 5: 'Sáb', 6: 'Dom'
                    }
                    dia_semana = dias_semana[game_date_mex.weekday()]
                    
                    # Formatear con día, fecha y hora
                    game['start_time'] = f"{dia_semana} {game_date_mex.strftime('%d/%m')} {game_date_mex.strftime('%I:%M %p')}"
                except Exception as time_error:
                    print(f"Error converting time for game {game.get('id', '')}: {time_error}")
                    # Mantener el valor original si falla la conversión
                    pass
        
        # Debug: imprimir user_picks_by_game para verificar formato
        return render_template('games_status_with_picks.html',
                             games=games,
                             current_week=current_week,
                             user_picks_by_game=user_picks_by_game,
                             last_update_mex=last_update_mex)
                             
    except Exception as e:
        print(f"Error in games_status: {e}")
        return render_template('games_status_with_picks.html', 
                             games=[], 
                             current_week=0,
                             user_picks_by_game={})

# =============================================================================
# LEGACY ADMIN ROUTES MOVED TO BLUEPRINTS
# =============================================================================
# All admin routes have been moved to blueprints/admin_routes.py
# The admin blueprint is registered above and handles all /admin/* routes

if __name__ == '__main__':
    # Configuración según entorno - desarrollo vs producción
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Reloader habilitado por defecto en desarrollo, deshabilitado en producción
    default_reloader = 'True' if debug_mode else 'False'
    use_reloader = os.environ.get('FLASK_USE_RELOADER', default_reloader).lower() == 'true'
    
    port = int(os.environ.get('FLASK_PORT', 8000))
    
    # Información del modo de ejecución
    if debug_mode:
        if use_reloader:
            print("🔄 Modo desarrollo - Hot-reload activado")
        else:
            print("⚡ Modo desarrollo - Hot-reload deshabilitado")
    else:
        print("🚀 Modo producción - Optimizado para rendimiento")
    
    app.run(debug=debug_mode, port=port, use_reloader=use_reloader)