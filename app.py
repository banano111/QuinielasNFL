import sqlite3
import hashlib
import os
import requests
import urllib3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Inicializa la aplicación Flask
app = Flask(__name__)
# Genera una clave secreta aleatoria para la sesión, esencial para la seguridad
app.secret_key = os.urandom(24)

# Define el nombre del archivo de la base de datos
DATABASE = 'quiniela.db'


# --- Lógica de la Base de Datos ---

def get_db():
    """
    Función de ayuda para conectar a la base de datos.
    Cada llamada a esta función abre una nueva conexión.
    """
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row  # Esto permite acceder a las columnas por nombre
    return db


def create_tables():
    """
    Crea las tablas de la base de datos si no existen.
    Esto se ejecuta una sola vez al iniciar la aplicación.
    """
    db = get_db()
    with db:
        # Tabla de usuarios: guarda username, password hasheada y un flag de administrador
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Tabla de selecciones (picks) de los usuarios para cada partido
        db.execute('''
            CREATE TABLE IF NOT EXISTS picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                week INTEGER NOT NULL,
                game_id TEXT NOT NULL,
                selection TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, week, game_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')

        # Tabla para los resultados finales de cada partido
        db.execute('''
            CREATE TABLE IF NOT EXISTS game_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week INTEGER NOT NULL,
                game_id TEXT NOT NULL,
                winner TEXT NOT NULL,
                home_team TEXT,
                away_team TEXT,
                home_score INTEGER,
                away_score INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Tabla para el historial de ganadores semanales
        db.execute('''
            CREATE TABLE IF NOT EXISTS winners_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week INTEGER NOT NULL,
                username TEXT NOT NULL,
                score INTEGER NOT NULL
            );
        ''')
        
        # Tabla para configuración del sistema
        db.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

    # Inserta un usuario administrador por defecto si no existe
    cursor = db.execute('SELECT * FROM users WHERE is_admin = 1;')
    if not cursor.fetchone():
        # IMPORTANTE: Cambiar esta contraseña por una segura en producción
        hashed_password = hashlib.sha256('QuinielasNFL2024!'.encode()).hexdigest()
        db.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                   ('admin', hashed_password, 1))
        
    # Inserta configuración por defecto si no existe
    cursor = db.execute('SELECT * FROM system_config WHERE config_key = ?;', ('current_week',))
    if not cursor.fetchone():
        db.execute('INSERT INTO system_config (config_key, config_value) VALUES (?, ?)', ('current_week', '4'))
        db.execute('INSERT INTO system_config (config_key, config_value) VALUES (?, ?)', ('picks_locked', '0'))
    
    # Migración: Agregar columnas home_team y away_team a game_results si no existen
    try:
        db.execute('ALTER TABLE game_results ADD COLUMN home_team TEXT;')
        db.execute('ALTER TABLE game_results ADD COLUMN away_team TEXT;')
        print("Columnas home_team y away_team agregadas a game_results")
    except Exception:
        # Las columnas ya existen, no hay problema
        pass
    
    # Migración: Actualizar la semana actual si está en 1 o 2 (para instalaciones existentes)
    try:
        current_config = db.execute('SELECT config_value FROM system_config WHERE config_key = ?', ('current_week',)).fetchone()
        if current_config and int(current_config['config_value']) <= 2:
            db.execute('UPDATE system_config SET config_value = ? WHERE config_key = ?', ('4', 'current_week'))
            print(f"Semana actualizada de {current_config['config_value']} a 4")
    except Exception as e:
        print(f"Error actualizando semana: {e}")
        
    db.commit()
    db.close()


def init_db():
    """
    Inicializa la base de datos creando todas las tablas necesarias.
    Esta función es llamada automáticamente cuando se importa el módulo.
    """
    create_tables()


# --- Funciones de Ayuda ---

def hash_password(password):
    """Función de ayuda para hashear contraseñas usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_current_week():
    """
    Obtiene la semana actual desde la base de datos.
    """
    db = get_db()
    config = db.execute('SELECT config_value FROM system_config WHERE config_key = ?', ('current_week',)).fetchone()
    db.close()
    return int(config['config_value']) if config else 1


def set_current_week(week):
    """
    Actualiza la semana actual en la base de datos.
    """
    db = get_db()
    db.execute('UPDATE system_config SET config_value = ? WHERE config_key = ?', (str(week), 'current_week'))
    db.commit()
    db.close()

def get_system_config():
    """
    Obtiene la configuración del sistema.
    """
    db = get_db()
    configs = {}
    rows = db.execute('SELECT config_key, config_value FROM system_config').fetchall()
    for row in rows:
        configs[row['config_key']] = row['config_value']
    db.close()
    return configs


def get_espn_nfl_data(week=None):
    """
    Obtiene datos reales de la NFL desde la API de ESPN.
    Retorna los logos de equipos y los partidos de la semana especificada.
    """
    try:
        # Si no se especifica semana, usar la semana actual del sistema
        if week is None:
            week = get_current_week()
        
        # Año actual de la temporada NFL (2024)
        season = 2024
        
        # Llamada a la API de ESPN para una semana específica (con SSL deshabilitado)
        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}&year={season}'
        response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status()
        data = response.json()

        # Procesar los datos de la API
        games = []
        teams = {}
        for event in data.get('events', []):
            game_id = event.get('id')
            competitions = event.get('competitions', [])

            if competitions:
                competition = competitions[0]
                competitors = competition.get('competitors', [])
                if len(competitors) >= 2:
                    home_team, away_team = None, None
                    home_logo, away_logo = None, None
                    for competitor in competitors:
                        team_info = competitor.get('team', {})
                        team_name = team_info.get('displayName', '')
                        team_logo = team_info.get('logo', '')
                        if competitor.get('homeAway') == 'home':
                            home_team, home_logo = team_name, team_logo
                        else:
                            away_team, away_logo = team_name, team_logo
                        teams[team_name] = team_logo
                    start_time = event.get('date', '')
                    formatted_time = start_time
                    if start_time:
                        try:
                            # Convertir de UTC a CDMX (UTC-6)
                            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            # Restar 6 horas para convertir a CDMX
                            cdmx_dt = dt - timedelta(hours=6)
                            formatted_time = cdmx_dt.strftime('%d/%m %H:%M')
                        except:
                            formatted_time = 'TBD'
                    # Obtener información de score y estado del juego
                    status = competition.get('status', {})
                    status_type = status.get('type', {}).get('name', '')
                    home_score = None
                    away_score = None
                    
                    # Si el juego está completado o en progreso, obtener los scores
                    if status_type in ['STATUS_FINAL', 'STATUS_IN_PROGRESS', 'Final', 'Completed']:
                        for competitor in competitors:
                            score = competitor.get('score', 0)
                            if competitor.get('homeAway') == 'home':
                                home_score = int(score) if score else 0
                            else:
                                away_score = int(score) if score else 0
                    
                    if home_team and away_team:
                        game_data = {
                            'id': game_id,
                            'home_team': home_team,
                            'away_team': away_team,
                            'start_time': formatted_time,
                            'home_logo': home_logo,
                            'away_logo': away_logo,
                            'status': status_type
                        }
                        
                        # Agregar scores si están disponibles
                        if home_score is not None and away_score is not None:
                            game_data['home_score'] = home_score
                            game_data['away_score'] = away_score
                            
                        games.append(game_data)
        return teams, games

    except Exception as e:
        print(f"Error al obtener datos de ESPN: {e}")
        import traceback
        print(f"Detalles del error: {traceback.format_exc()}")
        # Fallback a datos mock si la API falla
        return get_mock_nfl_data()


def get_mock_nfl_data():
    """
    Datos de fallback en caso de que la API de ESPN no esté disponible.
    """
    mock_teams = {
        'Arizona Cardinals': 'https://a.espncdn.com/i/teamlogos/nfl/500/ari.png',
        'Atlanta Falcons': 'https://a.espncdn.com/i/teamlogos/nfl/500/atl.png',
        'Baltimore Ravens': 'https://a.espncdn.com/i/teamlogos/nfl/500/bal.png',
        'Buffalo Bills': 'https://a.espncdn.com/i/teamlogos/nfl/500/buf.png',
        'Carolina Panthers': 'https://a.espncdn.com/i/teamlogos/nfl/500/car.png',
        'Chicago Bears': 'https://a.espncdn.com/i/teamlogos/nfl/500/chi.png',
        'Cincinnati Bengals': 'https://a.espncdn.com/i/teamlogos/nfl/500/cin.png',
        'Cleveland Browns': 'https://a.espncdn.com/i/teamlogos/nfl/500/cle.png',
        'Dallas Cowboys': 'https://a.espncdn.com/i/teamlogos/nfl/500/dal.png',
        'Denver Broncos': 'https://a.espncdn.com/i/teamlogos/nfl/500/den.png',
        'Detroit Lions': 'https://a.espncdn.com/i/teamlogos/nfl/500/det.png',
        'Green Bay Packers': 'https://a.espncdn.com/i/teamlogos/nfl/500/gb.png',
        'Houston Texans': 'https://a.espncdn.com/i/teamlogos/nfl/500/hou.png',
        'Indianapolis Colts': 'https://a.espncdn.com/i/teamlogos/nfl/500/ind.png',
        'Jacksonville Jaguars': 'https://a.espncdn.com/i/teamlogos/nfl/500/jac.png',
        'Kansas City Chiefs': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png',
        'Las Vegas Raiders': 'https://a.espncdn.com/i/teamlogos/nfl/500/lv.png',
        'Los Angeles Chargers': 'https://a.espncdn.com/i/teamlogos/nfl/500/lac.png',
        'Los Angeles Rams': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png',
        'Miami Dolphins': 'https://a.espncdn.com/i/teamlogos/nfl/500/mia.png',
        'Minnesota Vikings': 'https://a.espncdn.com/i/teamlogos/nfl/500/min.png',
        'New England Patriots': 'https://a.espncdn.com/i/teamlogos/nfl/500/ne.png',
        'New Orleans Saints': 'https://a.espncdn.com/i/teamlogos/nfl/500/no.png',
        'New York Giants': 'https://a.espncdn.com/i/teamlogos/nfl/500/nyg.png',
        'New York Jets': 'https://a.espncdn.com/i/teamlogos/nfl/500/nyj.png',
        'Philadelphia Eagles': 'https://a.espncdn.com/i/teamlogos/nfl/500/phi.png',
        'Pittsburgh Steelers': 'https://a.espncdn.com/i/teamlogos/nfl/500/pit.png',
        'San Francisco 49ers': 'https://a.espncdn.com/i/teamlogos/nfl/500/sf.png',
        'Seattle Seahawks': 'https://a.espncdn.com/i/teamlogos/nfl/500/sea.png',
        'Tampa Bay Buccaneers': 'https://a.espncdn.com/i/teamlogos/nfl/500/tb.png',
        'Tennessee Titans': 'https://a.espncdn.com/i/teamlogos/nfl/500/ten.png',
        'Washington Commanders': 'https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png'
    }
    mock_games = [
        {'id': '1', 'home_team': 'Green Bay Packers', 'away_team': 'Chicago Bears', 'start_time': 'Dom 12:00',
         'home_logo': mock_teams['Green Bay Packers'], 'away_logo': mock_teams['Chicago Bears']},
        {'id': '2', 'home_team': 'Baltimore Ravens', 'away_team': 'Miami Dolphins', 'start_time': 'Dom 12:00',
         'home_logo': mock_teams['Baltimore Ravens'], 'away_logo': mock_teams['Miami Dolphins']},
        {'id': '3', 'home_team': 'Cincinnati Bengals', 'away_team': 'Cleveland Browns', 'start_time': 'Dom 15:05',
         'home_logo': mock_teams['Cincinnati Bengals'], 'away_logo': mock_teams['Cleveland Browns']},
        {'id': '4', 'home_team': 'Las Vegas Raiders', 'away_team': 'Denver Broncos', 'start_time': 'Dom 15:25',
         'home_logo': mock_teams['Las Vegas Raiders'], 'away_logo': mock_teams['Denver Broncos']},
        {'id': '5', 'home_team': 'Kansas City Chiefs', 'away_team': 'Buffalo Bills', 'start_time': 'Lun 20:15',
         'home_logo': mock_teams['Kansas City Chiefs'], 'away_logo': mock_teams['Buffalo Bills']}
    ]
    return mock_teams, mock_games


def check_picks_deadline():
    """
    Verifica si aún se pueden enviar picks.
    Retorna True si está dentro del tiempo límite, False si ya expiró.
    """
    config = get_system_config()
    picks_locked = config.get('picks_locked', '0') == '1'
    return not picks_locked


def get_user_standings():
    """
    Calcula la clasificación de la semana actual solamente.
    Retorna una lista ordenada por puntuación descendente.
    """
    db = get_db()
    
    # Obtener semana actual
    config = get_system_config()
    current_week = config['current_week'] if config else 1
    
    users = db.execute('SELECT id, username FROM users WHERE is_admin = 0').fetchall()
    
    standings = []
    for user in users:
        # Contar aciertos de la semana actual solamente
        correct_picks = db.execute('''
            SELECT COUNT(*) as count FROM picks p
            JOIN game_results gr ON p.game_id = gr.game_id AND p.week = gr.week
            WHERE p.user_id = ? AND p.week = ? AND p.selection = gr.winner
        ''', (user['id'], current_week)).fetchone()
        
        # Contar total de picks de la semana actual
        total_picks = db.execute('''
            SELECT COUNT(*) as count FROM picks p
            WHERE p.user_id = ? AND p.week = ?
        ''', (user['id'], current_week)).fetchone()
        
        score = correct_picks['count'] if correct_picks else 0
        total = total_picks['count'] if total_picks else 0
        percentage = (score / total * 100) if total > 0 else 0
        
        # Solo incluir usuarios que hicieron picks esta semana
        if total > 0:
            standings.append({
                'username': user['username'],
                'score': score,
                'user_id': user['id'],
                'percentage': percentage,
                'total_picks': total,
                'week': current_week
            })
    
    standings.sort(key=lambda x: x['score'], reverse=True)
    db.close()
    return standings


# --- Rutas de la Aplicación ---

@app.route('/')
def home():
    """
    Ruta principal del dashboard.
    Muestra la página de inicio o redirige al login si no hay sesión activa.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Si es admin, redirigir al panel de administración
    if session.get('is_admin'):
        return redirect(url_for('admin_panel'))
    
    db = get_db()
    current_week = get_current_week()

    # Obtener estadísticas para el dashboard (solo usuarios no admin)
    users_count = db.execute('SELECT COUNT(*) as count FROM users WHERE is_admin = 0').fetchone()['count']
    
    # Verificar si el usuario actual ha enviado picks
    user_picks = db.execute('''
        SELECT * FROM picks WHERE user_id = ? AND week = ?
    ''', (session['user_id'], current_week)).fetchall()
    user_has_submitted_picks = len(user_picks) > 0
    
    # Obtener clasificación actual (top 10)
    standings = get_user_standings()[:10]
    
    # Obtener historial de ganadores (últimas 5 semanas)
    winners_history = db.execute('''
        SELECT * FROM winners_history ORDER BY week DESC LIMIT 5
    ''').fetchall()
    
    db.close()
    
    return render_template('index.html',
                           current_week=current_week,
                           users_count=users_count,
                           user_has_submitted_picks=user_has_submitted_picks,
                           standings=standings,
                           winners_history=winners_history,
                           last_updated=datetime.now().strftime('%d/%m/%Y %H:%M'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Maneja el login de usuarios."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, hashed_password)
        ).fetchone()
        db.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash('Login exitoso', 'success')
            return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Maneja el registro de nuevos usuarios."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validación básica
        if len(username) < 3:
            flash('El nombre de usuario debe tener al menos 3 caracteres', 'error')
            return render_template('register.html')
            
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('register.html')
        
        hashed_password = hash_password(password)
        
        db = get_db()
        try:
            # Verificar si el usuario ya existe
            existing_user = db.execute(
                'SELECT id FROM users WHERE username = ?', (username,)
            ).fetchone()
            
            if existing_user:
                flash('El nombre de usuario ya existe', 'error')
                return render_template('register.html')
                
            # Insertar el nuevo usuario
            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, hashed_password)
            )
            db.commit()
            flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        
        except sqlite3.Error:
            flash('Error al crear la cuenta. Inténtalo de nuevo.', 'error')
        finally:
            db.close()
            
    return render_template('register.html')


@app.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('login'))


@app.route('/picks', methods=['GET', 'POST'])
def picks_form():
    """Formulario para que los usuarios hagan sus picks."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_week = get_current_week()
    
    # Verificar deadline
    if not check_picks_deadline():
        flash('El tiempo para enviar picks ha expirado', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        db = get_db()
        
        # Eliminar picks anteriores del usuario para esta semana
        db.execute('DELETE FROM picks WHERE user_id = ? AND week = ?',
                   (session['user_id'], current_week))
        
        # Insertar nuevos picks
        for key, value in request.form.items():
            if key.startswith('game_'):
                game_id = key.replace('game_', '')
                db.execute(
                    'INSERT INTO picks (user_id, week, game_id, selection) VALUES (?, ?, ?, ?)',
                    (session['user_id'], current_week, game_id, value)
                )
        
        db.commit()
        db.close()
        
        flash('Picks enviados exitosamente', 'success')
        return redirect(url_for('home'))
        
    # GET request - mostrar el formulario
    teams, games = get_espn_nfl_data()
    
    # Obtener picks existentes del usuario
    db = get_db()
    existing_picks = db.execute('''
        SELECT game_id, selection FROM picks
        WHERE user_id = ? AND week = ?
    ''', (session['user_id'], current_week)).fetchall()
    db.close()
    
    # Convertir a diccionario para fácil acceso
    user_picks = {str(pick['game_id']): pick['selection'] for pick in existing_picks}
    
    return render_template('picks_form.html',
                           games=games,
                           teams=teams,
                           current_week=current_week,
                           user_picks=user_picks)


# --- Rutas administrativas ---

@app.route('/admin')
def admin_panel():
    """Panel de administración (solo para admins)."""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Acceso denegado', 'error')
        return redirect(url_for('home'))
    
    db = get_db()
    current_week = get_current_week()
    config = get_system_config()

    # Obtener estadísticas para el panel admin
    total_users = db.execute('SELECT COUNT(*) as count FROM users WHERE is_admin = 0').fetchone()['count']
    
    picks_submitted = db.execute('''
        SELECT COUNT(DISTINCT p.user_id) as count 
        FROM picks p 
        JOIN users u ON p.user_id = u.id 
        WHERE p.week = ? AND u.is_admin = 0
    ''', (current_week,)).fetchone()['count']
    
    processed_results = db.execute('SELECT COUNT(*) as count FROM game_results WHERE week = ?',
                                   (current_week,)).fetchone()['count']
    
    # Obtener lista de usuarios con información adicional
    users = db.execute('''
        SELECT u.id, u.username, u.is_admin,
               CASE WHEN p.user_id IS NOT NULL THEN 1 ELSE 0 END as has_picks,
               COALESCE(SUM(CASE WHEN gr.winner = p.selection THEN 1 ELSE 0 END), 0) as total_score
        FROM users u
        LEFT JOIN picks p ON u.id = p.user_id AND p.week = ?
        LEFT JOIN game_results gr ON p.game_id = gr.game_id AND p.week = gr.week
        WHERE u.is_admin = 0
        GROUP BY u.id, u.username, u.is_admin, (CASE WHEN p.user_id IS NOT NULL THEN 1 ELSE 0 END)
    ''', (current_week,)).fetchall()
    
    db.close()
    
    return render_template('admin.html',
                           current_week=current_week,
                           total_users=total_users,
                           picks_submitted=picks_submitted,
                           processed_results=processed_results,
                           users=users,
                           config=config,
                           last_updated=datetime.now().strftime('%d/%m/%Y %H:%M'))
@app.route('/standings')
def standings():
    """Retorna la clasificación actual (para HTMX)."""
    standings = get_user_standings()
    return render_template('standings_partial.html', standings=standings)


@app.route('/picks_grid')
def picks_grid():
    """Vista de cuadrícula de picks por partido."""
    config = get_system_config()
    current_week = config['current_week'] if config else 1
    
    db = get_db()
    
    # Obtener juegos de la semana actual con información de ESPN
    teams, games_data = get_espn_nfl_data(current_week)
    
    # Obtener todos los usuarios (no admins)
    users = db.execute('SELECT id, username FROM users WHERE is_admin = 0 ORDER BY username').fetchall()
    
    # Obtener todos los picks para esta semana
    picks = db.execute('''
        SELECT p.user_id, p.game_id, p.selection, u.username,
               gr.winner, gr.home_team, gr.away_team
        FROM picks p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN game_results gr ON p.game_id = gr.game_id AND p.week = gr.week
        WHERE p.week = ? AND u.is_admin = 0
        ORDER BY u.username, p.game_id
    ''', (current_week,)).fetchall()
    
    # Organizar picks por usuario y juego
    picks_matrix = {}
    for pick in picks:
        user_id = pick['user_id']
        game_id = pick['game_id']
        if user_id not in picks_matrix:
            picks_matrix[user_id] = {}
        picks_matrix[user_id][game_id] = {
            'selection': pick['selection'],
            'winner': pick['winner'],
            'is_correct': pick['winner'] == pick['selection'] if pick['winner'] else None
        }
    
    db.close()
    
    return render_template('picks_grid.html', 
                         games=games_data, 
                         users=users, 
                         picks_matrix=picks_matrix,
                         current_week=current_week)


@app.route('/picks_grid_partial')
def picks_grid_partial():
    """Cuadrícula de picks como partial para el dashboard."""
    config = get_system_config()
    current_week = config['current_week'] if config else 1
    
    db = get_db()
    
    # Obtener juegos de la semana actual con información de ESPN
    teams, games_data = get_espn_nfl_data(current_week)
    
    # Obtener todos los usuarios (no admins)
    users = db.execute('SELECT id, username FROM users WHERE is_admin = 0 ORDER BY username').fetchall()
    
    # Obtener todos los picks para esta semana
    picks = db.execute('''
        SELECT p.user_id, p.game_id, p.selection, u.username,
               gr.winner, gr.home_team, gr.away_team
        FROM picks p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN game_results gr ON p.game_id = gr.game_id AND p.week = gr.week
        WHERE p.week = ? AND u.is_admin = 0
        ORDER BY u.username, p.game_id
    ''', (current_week,)).fetchall()
    
    # Organizar picks por usuario y juego
    picks_matrix = {}
    for pick in picks:
        user_id = pick['user_id']
        game_id = pick['game_id']
        if user_id not in picks_matrix:
            picks_matrix[user_id] = {}
        picks_matrix[user_id][game_id] = {
            'selection': pick['selection'],
            'winner': pick['winner'],
            'is_correct': pick['winner'] == pick['selection'] if pick['winner'] else None
        }
    
    db.close()
    
    return render_template('picks_grid_partial.html', 
                         games=games_data, 
                         users=users, 
                         picks_matrix=picks_matrix,
                         current_week=current_week)


@app.route('/user_picks_status')
def user_picks_status():
    """Estado de picks del usuario actual (para HTMX)."""
    if 'user_id' not in session:
        return ''

    db = get_db()
    current_week = get_current_week()
    
    # Obtener picks del usuario para la semana actual
    user_picks = db.execute('''
        SELECT p.*, gr.winner,
               CASE WHEN p.selection = gr.winner THEN 'correct'
                    WHEN gr.winner IS NOT NULL THEN 'incorrect'
                    ELSE 'pending' END as result
        FROM picks p
        LEFT JOIN game_results gr ON p.game_id = gr.game_id AND p.week = gr.week
        WHERE p.user_id = ? AND p.week = ?
    ''', (session['user_id'], current_week)).fetchall()
    
    # Calcular puntuación de la semana
    user_score = sum(1 for pick in user_picks if pick['result'] == 'correct')
    
    # Obtener puntuación total
    total_score = db.execute('''
        SELECT COUNT(*) as count FROM picks p
        JOIN game_results gr ON p.game_id = gr.game_id AND p.week = gr.week
        WHERE p.user_id = ? AND p.selection = gr.winner
    ''', (session['user_id'],)).fetchone()['count']
    
    db.close()
    
    # Obtener datos de juegos para mostrar nombres de equipos
    teams, games = get_espn_nfl_data()
    games_dict = {str(game['id']): game for game in games}

    # Enriquecer picks con información de equipos y logos
    enriched_picks = []
    for pick in user_picks:
        game = games_dict.get(str(pick['game_id']), {})
        enriched_picks.append({
            **dict(pick),
            'home_team': game.get('home_team', 'Unknown'),
            'away_team': game.get('away_team', 'Unknown'),
            'home_logo': game.get('home_logo', ''),
            'away_logo': game.get('away_logo', ''),
            'picked_team': pick['selection']
        })
    
    return render_template('user_picks_status.html',
                           user_picks=enriched_picks,
                           user_score=user_score,
                           total_score=total_score,
                           current_week=current_week,
                           deadline_passed=not check_picks_deadline())


@app.route('/admin/debug_api/<int:week>')
def debug_api(week):
    """Función de debug para ver la respuesta cruda de ESPN API."""
    if 'user_id' not in session or not session.get('is_admin'):
        return 'Access denied'
    
    try:
        # Probar con ambos años
        for year in [2024, 2025]:
            url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}&year={year}'
            response = requests.get(url, timeout=10, verify=False)
            data = response.json()
            
            print(f"\n=== DEBUG API YEAR {year} WEEK {week} ===")
            print(f"URL: {url}")
            print(f"Events found: {len(data.get('events', []))}")
            
            if data.get('events'):
                for event in data.get('events', [])[:2]:  # Solo los primeros 2 eventos
                    competition = event.get('competitions', [{}])[0]
                    status = competition.get('status', {})
                    print(f"Game ID: {event.get('id')}")
                    print(f"Status object: {status}")
                    print(f"Status type: {status.get('type', {})}")
                    print(f"Status name: {status.get('type', {}).get('name', '')}")
                    print("---")
        
        return f"Check terminal for debug info for week {week}"
        
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/admin/view_week_games')
def admin_view_week_games():
    """Ver partidos de una semana específica para el administrador."""
    if 'user_id' not in session or not session.get('is_admin'):
        return '<div class="text-red-600">Acceso denegado</div>'
    
    week = request.args.get('week', type=int)
    if not week:
        return '<div class="text-red-600">Semana inválida</div>'
    
    try:
        # Obtener datos de la semana específica
        teams, games = get_espn_nfl_data(week)
        
        if not games:
            return f'<div class="text-yellow-600 p-4 bg-yellow-50 rounded-lg">No se encontraron partidos para la semana {week}</div>'
        
        # Contar juegos completados y en progreso
        completed_games = sum(1 for game in games if game.get('status') in ['STATUS_FINAL', 'Final', 'Completed', 'final'])
        in_progress_games = sum(1 for game in games if game.get('status') == 'STATUS_IN_PROGRESS')
        
        return render_template('admin_week_games_partial.html', 
                             games=games, 
                             week=week,
                             completed_games=completed_games,
                             in_progress_games=in_progress_games,
                             total_games=len(games))
    
    except Exception as e:
        return f'<div class="text-red-600 p-4 bg-red-50 rounded-lg">Error: {str(e)}</div>'


@app.route('/update_week', methods=['POST'])
def update_week():
    """Actualiza la semana actual del sistema."""
    if 'user_id' not in session or not session.get('is_admin'):
        return render_template('toast_partial.html',
                               category='error',
                               message='Acceso denegado')
    
    new_week = request.form.get('new_week', type=int)
    if not new_week or new_week < 1 or new_week > 18:
        return render_template('toast_partial.html',
                               category='error',
                               message='Semana inválida (debe ser entre 1 y 18)')
    
    try:
        set_current_week(new_week)
        return render_template('toast_partial.html',
                               category='success',
                               message=f'Semana actual actualizada a: Semana {new_week}')
    except Exception as e:
        return render_template('toast_partial.html',
                               category='error',
                               message=f'Error al actualizar semana: {str(e)}')


@app.route('/process_results', methods=['POST'])
def process_results():
    """Procesa los resultados de una semana específica desde la API de ESPN."""
    if 'user_id' not in session or not session.get('is_admin'):
        return render_template('toast_partial.html',
                               category='error',
                               message='Acceso denegado')
    
    week = request.form.get('week', type=int)
    if not week:
        return render_template('toast_partial.html',
                               category='error',
                               message='Semana inválida')
    
    try:
        # Obtener datos reales de la API de ESPN para la semana especificada
        teams, games = get_espn_nfl_data(week)
        
        if not games:
            return render_template('toast_partial.html',
                                   category='error',
                                   message=f'No se pudieron obtener los juegos de la semana {week}')
        
        db = get_db()
        results_processed = 0
        
        # Procesar cada juego para encontrar ganadores
        for game in games:
            game_id = game.get('id')
            status = game.get('status', '')
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            home_score = game.get('home_score', 0)
            away_score = game.get('away_score', 0)
            
            # Solo procesar juegos completados
            if status in ['STATUS_FINAL', 'Final', 'Completed', 'final'] and home_score != away_score:
                # Determinar el ganador
                if home_score > away_score:
                    winner = home_team
                else:
                    winner = away_team
                
                # Insertar o actualizar resultado
                db.execute('''
                    INSERT OR REPLACE INTO game_results (week, game_id, winner, home_team, away_team, home_score, away_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (week, game_id, winner, home_team, away_team, home_score, away_score))
                
                results_processed += 1
        
        db.commit()
        db.close()
        
        if results_processed > 0:
            return render_template('toast_partial.html',
                                   category='success',
                                   message=f'Procesados {results_processed} resultados para la semana {week}')
        else:
            return render_template('toast_partial.html',
                                   category='warning',
                                   message=f'No se encontraron juegos completados en la semana {week}')
    
    except Exception as e:
        print(f"Error procesando resultados: {e}")
        return render_template('toast_partial.html',
                               category='error',
                               message=f'Error al procesar resultados: {str(e)}')


@app.route('/declare_winner', methods=['POST'])
def declare_winner():
    """Declara el ganador de una semana específica."""
    if 'user_id' not in session or not session.get('is_admin'):
        return render_template('toast_partial.html',
                               category='error',
                               message='Acceso denegado')
    
    week = request.form.get('week', type=int)
    if not week:
        return render_template('toast_partial.html',
                               category='error',
                               message='Semana inválida')
    
    try:
        db = get_db()
        
        # Calcular ganador de la semana
        winner = db.execute('''
            SELECT u.username, COUNT(*) as score
            FROM users u
            JOIN picks p ON u.id = p.user_id
            JOIN game_results gr ON p.game_id = gr.game_id AND p.week = gr.week
            WHERE p.week = ? AND p.selection = gr.winner AND u.is_admin = 0
            GROUP BY u.id, u.username
            ORDER BY score DESC
            LIMIT 1
        ''', (week,)).fetchone()
        
        if winner:
            # Insertar en historial de ganadores
            db.execute('''
                INSERT OR REPLACE INTO winners_history (week, username, score)
                VALUES (?, ?, ?)
            ''', (week, winner['username'], winner['score']))
            
            db.commit()
            db.close()
            
            return render_template('toast_partial.html',
                                   category='success',
                                   message=f'Ganador declarado: {winner["username"]} ({winner["score"]} puntos)')
        else:
            db.close()
            return render_template('toast_partial.html',
                                   category='error',
                                   message='No se pudo determinar un ganador')
    
    except Exception as e:
        return render_template('toast_partial.html',
                               category='error',
                               message='Error al declarar ganador')

@app.route('/admin/update_week', methods=['POST'])
def update_current_week():
    """Actualiza la semana actual."""
    if 'user_id' not in session or not session.get('is_admin'):
        return render_template('toast_partial.html', 
                             category='error', 
                             message='Acceso denegado')
    
    new_week = request.form.get('week', type=int)
    if not new_week or new_week < 1 or new_week > 18:
        return render_template('toast_partial.html', 
                             category='error', 
                             message='Semana inválida (1-18)')
    
    try:
        db = get_db()
        db.execute('UPDATE system_config SET current_week = ?, updated_at = CURRENT_TIMESTAMP', (new_week,))
        db.commit()
        db.close()
        
        return render_template('toast_partial.html', 
                             category='success', 
                             message=f'Semana actualizada a {new_week}')
    
    except Exception:
        return render_template('toast_partial.html', 
                             category='error', 
                             message='Error al actualizar semana')

@app.route('/admin/toggle_picks', methods=['POST'])
def toggle_picks_lock():
    """Alterna el estado de bloqueo de picks."""
    if 'user_id' not in session or not session.get('is_admin'):
        return render_template('toast_partial.html', 
                             category='error', 
                             message='Acceso denegado')
    
    try:
        db = get_db()
        config = db.execute('SELECT config_value FROM system_config WHERE config_key = ?', ('picks_locked',)).fetchone()
        current_state = int(config['config_value']) if config else 0
        new_state = 0 if current_state else 1
        
        db.execute('UPDATE system_config SET config_value = ? WHERE config_key = ?', (str(new_state), 'picks_locked'))
        db.commit()
        db.close()
        
        status_text = 'bloqueados' if new_state else 'desbloqueados'
        return render_template('toast_partial.html', 
                             category='success', 
                             message=f'Picks {status_text}')
    
    except Exception:
        return render_template('toast_partial.html', 
                             category='error', 
                             message='Error al cambiar estado de picks')

@app.route('/games_status')
def games_status():
    """Retorna el estado de los partidos de la semana actual."""
    current_week = get_current_week()
    teams, games = get_espn_nfl_data(current_week)
    
    # Agregar timestamp de última actualización
    from datetime import datetime, timedelta
    now_cdmx = datetime.now() - timedelta(hours=6)  # Convertir a CDMX
    last_update_mex = now_cdmx.strftime('%d/%m %H:%M')
    
    return render_template('games_status_partial.html', 
                         games=games, 
                         teams=teams, 
                         current_week=current_week,
                         last_update_mex=last_update_mex)


# --- Inicio de la Aplicación ---

# Inicializar la base de datos automáticamente cuando se importa el módulo
# Esto garantiza que funcione tanto en desarrollo como en producción (PythonAnywhere)
init_db()

if __name__ == '__main__':
    import os
    # Para desarrollo local
    if os.environ.get('ENVIRONMENT') == 'development':
        app.run(debug=True)
    else:
        # Para producción (Render, PythonAnywhere, etc.)
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)