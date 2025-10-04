"""
Utilidades compartidas para la aplicación
Funciones que necesitan ser accesibles desde múltiples módulos
"""

import hashlib
import requests
from datetime import datetime
from quinielasapp.services.database_service import get_current_week


def hash_password(password):
    """Hashea una contraseña usando SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_espn_nfl_data(week=None):
    """
    Obtiene los datos de la NFL desde la API de ESPN.
    Mantiene la misma lógica que antes pero con mejores tipos.
    """
    if week is None:
        week = get_current_week()
    
    current_year = datetime.now().year
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={current_year}&seasontype=2&week={week}"
    
    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        if 'events' in data:
            for event in data['events']:
                if len(event.get('competitions', [])) > 0:
                    competition = event['competitions'][0]
                    competitors = competition.get('competitors', [])
                    
                    if len(competitors) >= 2:
                        # Extraer información de los equipos
                        home_team = None
                        away_team = None
                        
                        for competitor in competitors:
                            team_info = competitor.get('team', {})
                            team_name = team_info.get('displayName', 'Unknown')
                            team_abbr = team_info.get('abbreviation', team_name[:3].upper())
                            
                            if competitor.get('homeAway') == 'home':
                                home_team = {
                                    'name': team_name,
                                    'abbreviation': team_abbr,
                                    'logo': team_info.get('logo', ''),
                                    'score': competitor.get('score', '0')
                                }
                            else:
                                away_team = {
                                    'name': team_name,
                                    'abbreviation': team_abbr,
                                    'logo': team_info.get('logo', ''),
                                    'score': competitor.get('score', '0')
                                }
                        
                        # Extraer fecha y hora del juego
                        game_date = event.get('date', '')
                        start_time = 'TBD'
                        if game_date:
                            try:
                                # Convertir fecha ISO a formato legible con zona horaria de Ciudad de México
                                dt = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                                
                                # Convertir a zona horaria de Ciudad de México
                                from zoneinfo import ZoneInfo
                                cdmx_tz = ZoneInfo("America/Mexico_City")
                                local_dt = dt.astimezone(cdmx_tz)
                                
                                # Días de la semana en español
                                days_spanish = {
                                    'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                                    'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
                                }
                                
                                day_name = days_spanish.get(local_dt.strftime('%A'), local_dt.strftime('%A'))
                                start_time = f"{day_name} {local_dt.day}/{local_dt.month} {local_dt.strftime('%H:%M')}"
                            except:
                                start_time = 'TBD'
                        
                        # Información del juego con formato compatible con templates
                        game_info = {
                            'id': event.get('id', ''),
                            'name': event.get('name', ''),
                            'date': game_date,
                            'start_time': start_time,
                            'status': competition.get('status', {}).get('type', {}).get('description', 'Scheduled'),
                            'clock': competition.get('status', {}).get('displayClock', ''),
                            'period': competition.get('status', {}).get('period', 0),
                            'completed': competition.get('status', {}).get('type', {}).get('completed', False),
                            'week': week,
                            # Datos del equipo home - Formato híbrido para compatibilidad
                            'home_team': {
                                'name': home_team['name'] if home_team else 'Unknown',
                                'abbreviation': home_team['abbreviation'] if home_team else 'UNK'
                            },
                            'home_logo': home_team['logo'] if home_team else '',
                            'home_score': int(home_team['score']) if home_team and home_team['score'].isdigit() else 0,
                            # Datos del equipo away - Formato híbrido para compatibilidad
                            'away_team': {
                                'name': away_team['name'] if away_team else 'Unknown',
                                'abbreviation': away_team['abbreviation'] if away_team else 'UNK'
                            },
                            'away_logo': away_team['logo'] if away_team else '',
                            'away_score': int(away_team['score']) if away_team and away_team['score'].isdigit() else 0
                        }
                        
                        games.append(game_info)
        
        return games
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching NFL data: {e}")
        return get_mock_nfl_data()
    except Exception as e:
        print(f"Unexpected error: {e}")
        return get_mock_nfl_data()


def get_mock_nfl_data():
    """
    Datos de prueba para cuando la API de ESPN no esté disponible.
    Con formato compatible con templates.
    """
    return [
        {
            'id': 'mock_game_1',
            'name': 'Kansas City Chiefs at Buffalo Bills',
            'date': '2024-01-21T23:30:00Z',
            'start_time': '6:30 PM',
            'status': 'Scheduled',
            'clock': '',
            'period': 0,
            'completed': False,
            'week': get_current_week(),
            # Equipo local - Formato consistente
            'home_team': {
                'name': 'Buffalo Bills',
                'abbreviation': 'BUF'
            },
            'home_logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/buf.png',
            'home_score': 0,
            # Equipo visitante - Formato consistente
            'away_team': {
                'name': 'Kansas City Chiefs',
                'abbreviation': 'KC'
            },
            'away_logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png',
            'away_score': 0
        },
        {
            'id': 'mock_game_2',
            'name': 'San Francisco 49ers at Philadelphia Eagles',
            'date': '2024-01-22T02:00:00Z',
            'start_time': '9:00 PM',
            'status': 'Scheduled',
            'clock': '',
            'period': 0,
            'completed': False,
            'week': get_current_week(),
            # Equipo local - Formato consistente
            'home_team': {
                'name': 'Philadelphia Eagles',
                'abbreviation': 'PHI'
            },
            'home_logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/phi.png',
            'home_score': 0,
            # Equipo visitante - Formato consistente
            'away_team': {
                'name': 'San Francisco 49ers',
                'abbreviation': 'SF'
            },
            'away_logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/sf.png',
            'away_score': 0
        }
    ]