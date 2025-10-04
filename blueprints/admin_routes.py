"""
Blueprint para rutas de administración
Organiza todas las funcionalidades del panel admin
"""
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from quinielasapp.models.models import User, League, LeagueMembership, Pick, GameResult, SystemConfig
from quinielasapp.services.database_service import (
    get_current_week, set_current_week, get_system_config,
    generate_league_code, get_user_leagues,
    get_user_standings_by_league, check_picks_deadline
)
from shared_utils import get_espn_nfl_data

# Crear el blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorador para verificar permisos de admin
def admin_required(f):
    """Decorador que requiere permisos de administrador"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Acceso denegado - Se requieren permisos de administrador', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# =============================================================================
# RUTAS PRINCIPALES DEL ADMIN
# =============================================================================

@admin_bp.route('/')
@admin_required
def dashboard():
    """Panel de administración principal"""
    try:
        # Obtener estadísticas básicas (excluyendo admins)
        total_users = User.select().where(User.is_admin == False).count()
        current_week = get_current_week()
        picks_locked = check_picks_deadline()
        
        # Usuarios únicos que han hecho picks esta semana (solo usuarios no-admin)
        from peewee import fn
        picks_submitted = (Pick.select(Pick.user)
                          .join(User)
                          .where(
                              (Pick.week == current_week) & 
                              (User.is_admin == False)
                          )
                          .distinct()
                          .count())
        
        # Obtener todos los usuarios (excluyendo admins) con información adicional
        users = []
        for user in User.select().where(User.is_admin == False):
            has_picks = Pick.select().where(
                (Pick.user == user) & 
                (Pick.week == current_week)
            ).exists()
            
            user_data = {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin,
                'has_picks': has_picks,
                'total_score': 0  # TODO: Implementar cálculo de puntuación
            }
            users.append(user_data)
        
        # Obtener todas las ligas
        leagues = []
        for league in League.select():
            member_count = LeagueMembership.select().where(
                LeagueMembership.league == league
            ).count()
            
            league_data = {
                'id': league.id,
                'name': league.name,
                'code': league.code,
                'description': league.description,
                'is_active': league.is_active,
                'member_count': member_count
            }
            leagues.append(league_data)
        
        return render_template('admin.html',
                             total_users=total_users,
                             picks_submitted=picks_submitted,
                             current_week=current_week,
                             picks_locked=picks_locked,
                             users=users,
                             leagues=leagues)
                             
    except Exception as e:
        print(f"Error in admin dashboard: {e}")
        flash('Error al cargar el panel de administración', 'error')
        return redirect(url_for('login'))

# =============================================================================
# GESTIÓN DE SEMANAS Y CONFIGURACIÓN
# =============================================================================

@admin_bp.route('/update_week', methods=['POST'])
@admin_required
def update_week():
    """Actualizar la semana actual del sistema"""
    try:
        week = int(request.form.get('week', 1))
        if 1 <= week <= 18:
            set_current_week(week)
            
            # Obtener estadísticas actualizadas para la nueva semana
            picks_submitted = Pick.select().where(Pick.week == week).count()
            
            return f'''
            <div class="rounded-md p-4 bg-green-50 border border-green-200 text-green-800 mb-4">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm font-medium">✅ Semana actualizada a {week}</p>
                    </div>
                </div>
            </div>
            <script>
                // Actualizar las tarjetas de estadísticas
                const currentWeekEl = document.querySelector('[data-stat="current-week"]');
                const picksWeekEl = document.querySelector('[data-stat="picks-week"]');
                const picksSubmittedEl = document.querySelector('[data-stat="picks-submitted"]');
                const totalUsersEl = document.querySelector('[data-stat="total-users"]');
                const winnerButtonEl = document.querySelector('[data-stat="winner-button-text"]');
                const weekInputEl = document.querySelector('input[name="week"]');
                
                if (currentWeekEl) currentWeekEl.textContent = '{week}';
                if (picksWeekEl) picksWeekEl.textContent = '{week}';
                if (picksSubmittedEl && totalUsersEl) {{
                    picksSubmittedEl.textContent = '{picks_submitted} / ' + totalUsersEl.textContent;
                }}
                if (weekInputEl) weekInputEl.value = '{week}';
                if (winnerButtonEl) winnerButtonEl.textContent = 'Declarar Ganador S{week}';
                
                // Actualizar el selector de semana en procesar resultados
                const processResultsSelect = document.querySelector('select[name="week"]');
                if (processResultsSelect) {{
                    processResultsSelect.value = '{week}';
                }}
                
                // Actualizar el input hidden del form de declarar ganador
                const winnerWeekInput = document.querySelector('input[name="week"][type="hidden"]');
                if (winnerWeekInput) {{
                    winnerWeekInput.value = '{week}';
                }}
                
                // Actualizar el botón de ver juegos de la semana
                const weekGamesButton = document.querySelector('[data-week-games-button]');
                if (weekGamesButton) {{
                    const currentUrl = weekGamesButton.getAttribute('hx-get');
                    const newUrl = currentUrl.replace(/week=\d+/, 'week={week}');
                    weekGamesButton.setAttribute('hx-get', newUrl);
                }}
            </script>
            '''
        else:
            return '''
            <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm font-medium">❌ La semana debe estar entre 1 y 18</p>
                    </div>
                </div>
            </div>
            '''
    except ValueError:
        return '''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Valor de semana inválido</p>
                </div>
            </div>
        </div>
        '''
    except Exception as e:
        print(f"Error updating week: {e}")
        return '''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Error al actualizar la semana</p>
                </div>
            </div>
        </div>
        '''

@admin_bp.route('/toggle_picks_lock', methods=['POST'])
@admin_required
def toggle_picks_lock():
    """Alternar el estado de bloqueo de picks"""
    try:
        current_locked = check_picks_deadline()
        new_state = not current_locked
        
        # Actualizar configuración
        SystemConfig.set_config('picks_locked', '1' if new_state else '0')
        
        status_text = "bloqueados" if new_state else "desbloqueados"
        return f'''
        <div class="rounded-md p-4 bg-green-50 border border-green-200 text-green-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">✅ Picks {status_text} exitosamente</p>
                </div>
            </div>
        </div>
        '''
        
    except Exception as e:
        print(f"Error toggling picks lock: {e}")
        return '''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Error al cambiar el estado de los picks</p>
                </div>
            </div>
        </div>
        '''

# =============================================================================
# GESTIÓN DE LIGAS
# =============================================================================

@admin_bp.route('/create_league', methods=['POST'])
@admin_required
def create_league():
    """Crear una nueva liga"""
    try:
        league_name = request.form.get('league_name', '').strip()
        league_code = request.form.get('league_code', '').strip().upper()
        league_description = request.form.get('league_description', '').strip()
        
        if not league_name or not league_code:
            flash('El nombre y código de la liga son obligatorios', 'error')
            return redirect(url_for('admin.dashboard'))
        
        # Verificar que el código no exista
        if League.select().where(League.code == league_code).exists():
            flash(f'Ya existe una liga con el código {league_code}', 'error')
            return redirect(url_for('admin.dashboard'))
        
        # Crear la liga
        League.create(
            name=league_name,
            code=league_code,
            description=league_description or None,
            created_by=session['user_id'],
            is_active=True
        )
        
        # Retornar la lista actualizada de ligas
        return render_template('admin_leagues_partial.html', leagues=League.select())
        
    except Exception as e:
        print(f"Error creating league: {e}")
        return '''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800 mb-4">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Error al crear la liga</p>
                </div>
            </div>
        </div>
        '''

# =============================================================================
# GESTIÓN DE USUARIOS Y MEMBRESÍAS
# =============================================================================

@admin_bp.route('/add_user_to_league', methods=['POST'])
@admin_required
def add_user_to_league():
    """Agregar un usuario a una liga"""
    try:
        user_id = request.form.get('user_id')
        league_id = request.form.get('league_id')
        
        if not user_id or not league_id:
            flash('Debe seleccionar un usuario y una liga', 'error')
            return redirect(url_for('admin.dashboard'))
        
        # Verificar que el usuario y la liga existen
        user = User.get_by_id(user_id)
        league = League.get_by_id(league_id)
        
        # Verificar si ya es miembro
        membership_exists = LeagueMembership.select().where(
            (LeagueMembership.user == user) &
            (LeagueMembership.league == league) &
            (LeagueMembership.is_active == True)
        ).exists()
        
        if membership_exists:
            flash(f'El usuario {user.username} ya es miembro de la liga {league.name}', 'error')
        else:
            # Crear la membresía
            LeagueMembership.create(
                user=user,
                league=league,
                is_active=True
            )
            return f'''
            <div class="rounded-md p-4 bg-green-50 border border-green-200 text-green-800">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm font-medium">✅ Usuario {user.username} agregado exitosamente a la liga {league.name}</p>
                    </div>
                </div>
            </div>
            '''
        
    except (User.DoesNotExist, League.DoesNotExist):
        return '''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Usuario o liga no encontrado</p>
                </div>
            </div>
        </div>
        '''
    except Exception as e:
        print(f"Error adding user to league: {e}")
        return '''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Error al agregar usuario a la liga</p>
                </div>
            </div>
        </div>
        '''

@admin_bp.route('/all_memberships')
@admin_required
def all_memberships():
    """Ver todas las membresías del sistema"""
    try:
        # Consulta más explícita con manejo de errores
        memberships = []
        
        # Primero contar total de membresías
        total_memberships = LeagueMembership.select().count()
        print(f"Total memberships in database: {total_memberships}")
        
        if total_memberships == 0:
            print("No memberships found in database")
            return render_template('admin_memberships_modal.html', memberships=[])
        
        # Obtener membresías con JOIN más seguro
        query = (LeagueMembership
                .select(LeagueMembership, User, League)
                .join(User, on=(LeagueMembership.user == User.id))
                .switch(LeagueMembership)
                .join(League, on=(LeagueMembership.league == League.id))
                .order_by(LeagueMembership.joined_at.desc()))
        
        for membership in query:
            try:
                membership_data = {
                    'user_username': membership.user.username,
                    'user_full_name': f"{membership.user.first_name or ''} {membership.user.last_name or ''}".strip(),
                    'league_name': membership.league.name,
                    'league_code': membership.league.code,
                    'is_active': membership.is_active,
                    'joined_at': membership.joined_at
                }
                memberships.append(membership_data)
            except Exception as item_error:
                print(f"Error processing membership item: {item_error}")
                continue
        
        print(f"Successfully processed {len(memberships)} memberships")
        return render_template('admin_memberships_modal.html', memberships=memberships)
        
    except Exception as e:
        import traceback
        print(f"Error getting memberships: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Retornar modal con error en lugar de JSON
        return f'''
        <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" onclick="this.remove()">
            <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white" onclick="event.stopPropagation()">
                <div class="mt-3">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-medium text-gray-900">Error</h3>
                        <button onclick="this.closest('.fixed').remove()" 
                                class="text-gray-400 hover:text-gray-600">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        </button>
                    </div>
                    <div class="text-red-600">
                        <p class="text-sm">Error al cargar membresías: {str(e)}</p>
                    </div>
                </div>
            </div>
        </div>
        '''

# =============================================================================
# GESTIÓN DE RESULTADOS
# =============================================================================

@admin_bp.route('/process_results', methods=['POST'])
@admin_required
def process_results():
    """Procesar resultados de una semana específica"""
    try:
        week = int(request.form.get('week', get_current_week()))
        
        # 1. Obtener resultados de ESPN API
        games = get_espn_nfl_data(week)
        
        if not games:
            return '''
            <div class="rounded-md p-4 bg-yellow-50 border border-yellow-200 text-yellow-800">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm font-medium">⚠️ No se encontraron juegos para la semana especificada</p>
                    </div>
                </div>
            </div>
            '''
        
        processed_games = 0
        updated_games = 0
        
        # 2. Procesar cada juego y guardar resultados
        for game in games:
            game_id = game.get('id') or game.get('game_id')
            status = game.get('status', '').lower()
            
            # Solo procesar juegos terminados
            if game.get('completed', False) or status in ['final', 'status_final', 'completed']:
                home_team = game.get('home_team', {}).get('abbreviation', '')
                away_team = game.get('away_team', {}).get('abbreviation', '')
                home_score = game.get('home_score', 0)
                away_score = game.get('away_score', 0)
                
                # Verificar que tenemos datos válidos
                if not game_id or not home_team or not away_team:
                    print(f"Datos incompletos para juego: id={game_id}, home={home_team}, away={away_team}")
                    continue
                
                # Determinar ganador
                if home_score > away_score:
                    winner = home_team
                elif away_score > home_score:
                    winner = away_team
                else:
                    winner = 'TIE'  # Empate (raro en NFL pero posible)
                
                # Guardar o actualizar resultado
                try:
                    # Convertir scores a int de forma segura
                    home_score_int = int(home_score) if str(home_score).isdigit() else 0
                    away_score_int = int(away_score) if str(away_score).isdigit() else 0
                    
                    result, created = GameResult.get_or_create(
                        game_id=game_id,
                        week=week,
                        defaults={
                            'home_team': home_team,
                            'away_team': away_team,
                            'home_score': home_score_int,
                            'away_score': away_score_int,
                            'winner': winner
                        }
                    )
                    
                    if not created:
                        # Actualizar resultado existente solo si cambió algo
                        needs_update = (
                            result.home_team != home_team or 
                            result.away_team != away_team or
                            result.home_score != home_score_int or 
                            result.away_score != away_score_int or
                            result.winner != winner
                        )
                        
                        if needs_update:
                            result.home_team = home_team
                            result.away_team = away_team
                            result.home_score = home_score_int
                            result.away_score = away_score_int
                            result.winner = winner
                            result.save()
                            updated_games += 1
                            print(f"Actualizado juego {game_id}: {away_team} @ {home_team} ({away_score_int}-{home_score_int})")
                    else:
                        processed_games += 1
                        print(f"Procesado nuevo juego {game_id}: {away_team} @ {home_team} ({away_score_int}-{home_score_int})")
                        
                except Exception as e:
                    print(f"Error processing game {game_id}: {e}")
                    continue
        
        # 3. Calcular estadísticas de procesamiento
        total_completed = processed_games + updated_games
        completed_games_in_api = sum(1 for game in games if game.get('completed', False) or game.get('status', '').lower() in ['final', 'status_final', 'completed'])
        
        if total_completed > 0:
            message = f"✅ Procesados {total_completed} de {completed_games_in_api} juegos completados en semana {week}"
            details = []
            if processed_games > 0:
                details.append(f"{processed_games} nuevos")
            if updated_games > 0:
                details.append(f"{updated_games} actualizados")
            
            if details:
                message += f" ({', '.join(details)})"
            
            return f'''
            <div class="rounded-md p-4 bg-green-50 border border-green-200 text-green-800">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <p class="text-sm font-medium">{message}</p>
                        <p class="text-xs text-green-700 mt-1">Los picks de los usuarios serán evaluados automáticamente con estos resultados.</p>
                    </div>
                </div>
            </div>
            '''
        else:
            return f'''
            <div class="rounded-md p-4 bg-yellow-50 border border-yellow-200 text-yellow-800">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm font-medium">⚠️ No hay juegos completados para procesar en la semana {week}</p>
                    </div>
                </div>
            </div>
            '''
        
    except ValueError:
        return '''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Semana inválida</p>
                </div>
            </div>
        </div>
        '''
    except Exception as e:
        print(f"Error processing results: {e}")
        return f'''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Error al procesar resultados: {str(e)}</p>
                </div>
            </div>
        </div>
        '''

@admin_bp.route('/declare_winner', methods=['POST'])
@admin_required
def declare_winner():
    """Declarar ganador de una semana"""
    try:
        week = int(request.form.get('week', get_current_week()))
        
        # Importar WinnersHistory si no está disponible
        try:
            from quinielasapp.models.models import WinnersHistory
        except ImportError:
            print("Warning: WinnersHistory model not found")
            return '''
            <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm font-medium">❌ Error: Modelo WinnersHistory no encontrado</p>
                    </div>
                </div>
            </div>
            '''
        from peewee import fn
        
        # 1. Verificar que hay resultados para esta semana
        results_count = GameResult.select().where(GameResult.week == week).count()
        
        if results_count == 0:
            return f'''
            <div class="rounded-md p-4 bg-yellow-50 border border-yellow-200 text-yellow-800">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm font-medium">⚠️ No hay resultados procesados para la semana {week}. Procesa los resultados primero.</p>
                    </div>
                </div>
            </div>
            '''
        
        # 2. Calcular puntuaciones por liga
        winners_declared = 0
        leagues_processed = []
        
        # Obtener todas las ligas activas que tienen picks para esta semana
        leagues_with_picks = League.select().join(Pick).where(
            (Pick.week == week) & 
            (League.is_active == True)
        ).distinct()
        
        for league in leagues_with_picks:
            # Calcular puntuaciones para esta liga específica
            user_scores = {}
            
            # Obtener todos los picks de esta liga para la semana
            try:
                # Obtener resultados de esta semana
                results = GameResult.select().where(GameResult.week == week)
                results_dict = {result.game_id: result for result in results}
                
                # Obtener todos los picks de la liga para esta semana
                picks_query = Pick.select().join(User).where(
                    (Pick.league_id == league.id) &
                    (Pick.week == week)
                )
                
                # Procesar cada pick y verificar si es correcto
                for pick in picks_query:
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
                        
                        # Verificar si el pick es correcto
                        if picked_team_abbr == result.winner or picked_team_name == result.winner:
                            user_id = pick.user.id
                            username = pick.user.username
                            
                            if user_id not in user_scores:
                                user_scores[user_id] = {
                                    'username': username,
                                    'user_id': user_id,
                                    'correct_picks': 0
                                }
                            
                            user_scores[user_id]['correct_picks'] += 1
                            
            except Exception as query_error:
                print(f"Error in picks query for league {league.name}: {query_error}")
                continue
            
            if not user_scores:
                continue  # No hay picks correctos en esta liga
            
            # Encontrar la puntuación máxima
            max_score = max(score['correct_picks'] for score in user_scores.values())
            
            # Encontrar todos los usuarios con la puntuación máxima (pueden ser empates)
            winners = [data for data in user_scores.values() if data['correct_picks'] == max_score]
            
            # 3. Limpiar ganadores existentes para esta liga/semana y crear nuevos
            WinnersHistory.delete().where(
                (WinnersHistory.league_id == league.id) & 
                (WinnersHistory.week == week)
            ).execute()
            
            # Crear entradas de ganadores (uno por ganador en caso de empate)
            for winner in winners:
                WinnersHistory.create(
                    user_id=winner['user_id'],
                    league_id=league.id,
                    week=week,
                    winner_username=winner['username'],
                    score=winner['correct_picks'],
                    is_tie=len(winners) > 1
                )
            
            print(f"Declared winners for league {league.name}: {[w['username'] for w in winners]} with {max_score} points")
            
            winners_declared += len(winners)
            leagues_processed.append({
                'league_name': league.name,
                'winners': winners,
                'max_score': max_score
            })
        
        # 4. Preparar mensaje de respuesta
        if winners_declared > 0:
            message = f"✅ Ganadores de la semana {week} declarados exitosamente:<br>"
            for league_info in leagues_processed:
                winners_text = ', '.join([w['username'] for w in league_info['winners']])
                tie_text = " (EMPATE)" if len(league_info['winners']) > 1 else ""
                message += f"<br>• Liga <strong>{league_info['league_name']}</strong>: {winners_text} ({league_info['max_score']} puntos){tie_text}"
            
            return f'''
            <div class="rounded-md p-4 bg-green-50 border border-green-200 text-green-800">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm font-medium">{message}</p>
                    </div>
                </div>
            </div>
            '''
        else:
            return f'''
            <div class="rounded-md p-4 bg-yellow-50 border border-yellow-200 text-yellow-800">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm font-medium">⚠️ No se encontraron ligas con picks para la semana {week}</p>
                    </div>
                </div>
            </div>
            '''
        
    except ValueError:
        return '''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Semana inválida</p>
                </div>
            </div>
        </div>
        '''
    except Exception as e:
        print(f"Error declaring winner: {e}")
        return f'''
        <div class="rounded-md p-4 bg-red-50 border border-red-200 text-red-800">
            <div class="flex">
                <div class="ml-3">
                    <p class="text-sm font-medium">❌ Error al declarar ganador: {str(e)}</p>
                </div>
            </div>
        </div>
        '''

@admin_bp.route('/view_week_games')
@admin_required
def view_week_games():
    """Ver juegos de una semana específica"""
    try:
        week = int(request.args.get('week', get_current_week()))
        
        # Obtener juegos de la semana desde ESPN API
        games = get_espn_nfl_data(week)
        
        # Obtener resultados existentes
        results = GameResult.select().where(GameResult.week == week)
        results_dict = {result.game_id: result for result in results}
        
        # Calcular estadísticas de juegos
        total_games = len(games)
        completed_games = 0
        in_progress_games = 0
        
        for game in games:
            status = game.get('status', '').lower()
            if game.get('completed', False) or status in ['final', 'status_final', 'completed']:
                completed_games += 1
            elif status in ['status_in_progress', 'in_progress', 'live']:
                in_progress_games += 1
        
        return render_template('admin_week_games_partial.html', 
                             games=games, 
                             week=week,
                             results=results_dict,
                             total_games=total_games,
                             completed_games=completed_games,
                             in_progress_games=in_progress_games)
        
    except ValueError:
        return render_template('toast_partial.html',
                             category='error',
                             message='Semana inválida')
    except Exception as e:
        print(f"Error getting week games: {e}")
        return render_template('toast_partial.html',
                             category='error',
                             message='Error al obtener juegos')

# =============================================================================
# API ENDPOINTS PARA ESTADÍSTICAS
# =============================================================================

@admin_bp.route('/view_league/<int:league_id>')
@admin_required
def view_league(league_id):
    """Ver detalles de una liga"""
    try:
        league = League.get_by_id(league_id)
        
        # Obtener estadísticas de la liga
        member_count = league.member_count
        
        # Picks totales en la liga
        total_picks = Pick.select().where(Pick.league_id == league.id).count()
        
        # Miembros activos
        active_members = list(User.select().join(LeagueMembership).where(
            (LeagueMembership.league_id == league.id) & 
            (LeagueMembership.is_active == True)
        ).limit(10))
        
        return render_template('league_detail_modal.html',
                             league=league,
                             member_count=member_count,
                             total_picks=total_picks,
                             active_members=active_members)
                             
    except League.DoesNotExist:
        return render_template('toast_partial.html',
                             category='error',
                             message='Liga no encontrada')
    except Exception as e:
        print(f"Error viewing league: {e}")
        return render_template('toast_partial.html',
                             category='error',
                             message='Error cargando detalles de liga')

@admin_bp.route('/edit_league/<int:league_id>')
@admin_required
def edit_league(league_id):
    """Formulario para editar liga"""
    try:
        league = League.get_by_id(league_id)
        return render_template('league_edit_modal.html', league=league)
        
    except League.DoesNotExist:
        return render_template('toast_partial.html',
                             category='error',
                             message='Liga no encontrada')

@admin_bp.route('/update_league/<int:league_id>', methods=['POST'])
@admin_required
def update_league(league_id):
    """Actualizar liga"""
    try:
        league = League.get_by_id(league_id)
        
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        max_members = request.form.get('max_members', '50')
        is_active = request.form.get('is_active') == 'on'
        
        if not name:
            return render_template('toast_partial.html',
                                 category='error',
                                 message='El nombre es requerido')
        
        try:
            max_members = int(max_members)
            if max_members < 1:
                raise ValueError()
        except (ValueError, TypeError):
            return render_template('toast_partial.html',
                                 category='error',
                                 message='Número de miembros inválido')
        
        # Actualizar liga
        league.name = name
        league.description = description if description else None
        league.max_members = max_members
        league.is_active = is_active
        league.save()
        
        return render_template('toast_partial.html',
                             category='success',
                             message=f'Liga "{league.name}" actualizada exitosamente')
        
    except League.DoesNotExist:
        return render_template('toast_partial.html',
                             category='error',
                             message='Liga no encontrada')
    except Exception as e:
        print(f"Error updating league: {e}")
        return render_template('toast_partial.html',
                             category='error',
                             message='Error actualizando liga')

@admin_bp.route('/league_members/<int:league_id>')
@admin_required
def league_members(league_id):
    """Ver miembros de una liga"""
    try:
        league = League.get_by_id(league_id)
        
        # Obtener membresías con información de usuario
        memberships = (LeagueMembership.select(LeagueMembership, User)
                      .join(User)
                      .where(LeagueMembership.league == league)
                      .order_by(LeagueMembership.joined_at.desc()))
        
        # Obtener todos los usuarios para el selector
        all_users = User.select().where(User.is_admin == False).order_by(User.username)
        
        return render_template('league_members_modal.html',
                             league=league,
                             memberships=memberships,
                             all_users=all_users)
                             
    except League.DoesNotExist:
        return render_template('toast_partial.html',
                             category='error',
                             message='Liga no encontrada')
    except Exception as e:
        print(f"Error getting league members: {e}")
        return render_template('toast_partial.html',
                             category='error',
                             message='Error cargando miembros')

@admin_bp.route('/remove_user_from_league', methods=['POST'])
@admin_required
def remove_user_from_league():
    """Remover usuario de liga"""
    user_id = request.form.get('user_id')
    league_id = request.form.get('league_id')
    
    if not user_id or not league_id:
        return render_template('toast_partial.html',
                             category='error',
                             message='Parámetros faltantes')
    
    try:
        # Encontrar la membresía
        membership = LeagueMembership.get(
            (LeagueMembership.user_id == user_id) &
            (LeagueMembership.league_id == league_id)
        )
        
        user = User.get_by_id(user_id)
        league = League.get_by_id(league_id)
        
        # Desactivar membresía en lugar de eliminar
        membership.is_active = False
        membership.save()
        
        return render_template('toast_partial.html',
                             category='success',
                             message=f'Usuario {user.username} removido de {league.name}')
        
    except (LeagueMembership.DoesNotExist, User.DoesNotExist, League.DoesNotExist):
        return render_template('toast_partial.html',
                             category='error',
                             message='Membresía no encontrada')
    except Exception as e:
        print(f"Error removing user from league: {e}")
        return render_template('toast_partial.html',
                             category='error',
                             message='Error removiendo usuario')

@admin_bp.route('/debug_api/<int:week>')
@admin_required
def debug_api(week):
    """Debug de la API de ESPN (solo admin)"""
    try:
        # Import local para evitar circular import
        from app import get_espn_nfl_data, get_mock_nfl_data
        
        # Forzar obtener datos de ESPN para la semana específica
        games_data = get_espn_nfl_data(week)
        
        # También obtener datos mock para comparar
        mock_data = get_mock_nfl_data()
        
        return jsonify({
            'week': week,
            'espn_games_count': len(games_data),
            'espn_games': games_data[:3],  # Mostrar solo los primeros 3
            'mock_games_count': len(mock_data),
            'mock_games': mock_data[:2]   # Mostrar solo los primeros 2
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@admin_bp.route('/stats')
@admin_required
def stats():
    """Estadísticas del sistema"""
    try:
        # Estadísticas básicas
        total_users = User.select().count()
        total_leagues = League.select().count()
        total_picks = Pick.select().count()
        active_leagues = League.select().where(League.is_active == True).count()
        
        return render_template('admin_stats_partial.html',
                             total_users=total_users,
                             total_leagues=total_leagues,
                             total_picks=total_picks,
                             active_leagues=active_leagues)
    except Exception as e:
        print(f"Error getting stats: {e}")
        return render_template('toast_partial.html',
                             category='error',
                             message='Error cargando estadísticas')

@admin_bp.route('/get_leagues_table_html')
@admin_required
def get_leagues_table_html():
    """Obtener HTML de tabla de ligas para HTMX"""
    try:
        # Obtener todas las ligas con información del creador
        leagues = (League.select(League, User.username.alias('creator_username'))
                  .join(User, on=(League.created_by == User.id))
                  .order_by(League.created_at.desc()))
        
        # Agregar conteo de miembros
        leagues_with_counts = []
        for league in leagues:
            member_count = LeagueMembership.select().where(
                (LeagueMembership.league == league) & 
                (LeagueMembership.is_active == True)
            ).count()
            
            leagues_with_counts.append({
                'league': league,
                'member_count': member_count,
                'creator_username': league.creator_username
            })
        
        return render_template('leagues_table_partial.html', leagues=leagues_with_counts)
        
    except Exception as e:
        print(f"Error getting leagues table: {e}")
        return '<p>Error cargando ligas</p>'


# =============================================================================
# DEBUG ENDPOINTS (Solo para validación)
# =============================================================================

@admin_bp.route('/debug_process_validation')
@admin_required
def debug_process_validation():
    """Debug endpoint para validar el procesamiento de resultados"""
    try:
        week = int(request.args.get('week', get_current_week()))
        
        # Obtener juegos de ESPN
        games = get_espn_nfl_data(week)
        
        # Obtener resultados ya procesados
        existing_results = GameResult.select().where(GameResult.week == week)
        results_dict = {r.game_id: r for r in existing_results}
        
        debug_info = {
            'week': week,
            'total_games_api': len(games),
            'completed_games_api': sum(1 for g in games if g.get('completed', False) or g.get('status', '').lower() in ['final', 'status_final', 'completed']),
            'existing_results_db': len(results_dict),
            'games_details': []
        }
        
        for game in games[:3]:  # Solo primeros 3 para debug
            game_id = game.get('id') or game.get('game_id')
            is_completed = game.get('completed', False) or game.get('status', '').lower() in ['final', 'status_final', 'completed']
            is_processed = game_id in results_dict
            
            debug_info['games_details'].append({
                'game_id': game_id,
                'home_team': game.get('home_team', {}),
                'away_team': game.get('away_team', {}),
                'home_score': game.get('home_score'),
                'away_score': game.get('away_score'),
                'status': game.get('status'),
                'completed': is_completed,
                'processed': is_processed
            })
        
        return f"<pre>{json.dumps(debug_info, indent=2)}</pre>"
        
    except Exception as e:
        return f"Error en debug: {str(e)}"

@admin_bp.route('/debug_winner_validation')
@admin_required 
def debug_winner_validation():
    """Debug endpoint para validar la declaración de ganadores"""
    try:
        week = int(request.args.get('week', get_current_week()))
        
        # Importar modelo necesario
        try:
            from quinielasapp.models.models import WinnersHistory
        except ImportError:
            return "Error: WinnersHistory model not found"
        
        # Información básica
        results_count = GameResult.select().where(GameResult.week == week).count()
        leagues_with_picks = League.select().join(Pick).where(
            (Pick.week == week) & 
            (League.is_active == True)
        ).distinct()
        
        debug_info = {
            'week': week,
            'results_count': results_count,
            'leagues_with_picks_count': leagues_with_picks.count(),
            'leagues_details': []
        }
        
        # Detalles por liga
        for league in leagues_with_picks:
            # Contar picks totales y correctos por usuario
            picks_count = Pick.select().where(
                (Pick.league_id == league.id) & 
                (Pick.week == week)
            ).count()
            
            # Obtener ganadores actuales si existen
            current_winners = WinnersHistory.select().where(
                (WinnersHistory.league_id == league.id) & 
                (WinnersHistory.week == week)
            )
            
            league_info = {
                'league_name': league.name,
                'league_id': league.id,
                'total_picks': picks_count,
                'current_winners': [
                    {
                        'username': w.winner_username,
                        'score': w.score,
                        'is_tie': w.is_tie
                    } for w in current_winners
                ]
            }
            
            debug_info['leagues_details'].append(league_info)
        
        return f"<pre>{json.dumps(debug_info, indent=2)}</pre>"
        
    except Exception as e:
        import traceback
        return f"<pre>Error en debug: {str(e)}\n\nTraceback:\n{traceback.format_exc()}</pre>"

@admin_bp.route('/view_standings')
@admin_required
def admin_view_standings():
    """Ver clasificaciones desde el panel de administración"""
    try:
        # Obtener todas las ligas activas
        leagues = League.select().where(League.is_active == True)
        
        all_standings = []
        
        for league in leagues:
            # Obtener standings para esta liga específica
            try:
                league_standings = get_user_standings_by_league(league.id)
                
                if league_standings:
                    # Los standings ya vienen ordenados por total_score descendente
                    # Solo agregar información de la liga a cada entrada
                    for standing in league_standings:
                        standing['league_name'] = league.name
                        standing['league_code'] = league.code
                    
                    all_standings.extend(league_standings)
            except Exception as league_error:
                print(f"Error getting standings for league {league.name}: {league_error}")
                continue
        
        # Agrupar por league manteniendo el orden interno de cada liga
        # Solo ordenar por nombre de liga para presentación
        all_standings.sort(key=lambda x: x.get('league_name', ''))
        
        # Crear modal con template personalizado
        return render_template('admin_standings_modal.html', standings=all_standings, leagues=leagues)
        
    except Exception as e:
        import traceback
        print(f"Error in admin standings: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
        return f'''
        <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" onclick="this.remove()">
            <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white" onclick="event.stopPropagation()">
                <div class="mt-3">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-medium text-gray-900">Error</h3>
                        <button onclick="this.closest('.fixed').remove()" 
                                class="text-gray-400 hover:text-gray-600">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        </button>
                    </div>
                    <div class="text-red-600">
                        <p class="text-sm">Error al cargar clasificaciones: {str(e)}</p>
                    </div>
                </div>
            </div>
        </div>
        '''