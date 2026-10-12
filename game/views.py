from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Team, Player, Match

def dashboard(request):
    players = Player.objects.all()
    teams = Team.objects.all()
    matches = Match.objects.all()
    finished = matches.filter(status='FINISHED')
    top_scorer = players.order_by('-goals').first()
    recent_matches = matches.order_by('-datetime')[:3]
    total_goals = sum(p.goals for p in players)

    return render(request, 'dashboard.html', {
        'player_count': players.count(),
        'team_count': teams.count(),
        'match_count': matches.count(),
        'finished_count': finished.count(),
        'top_scorer': top_scorer,
        'recent_matches': recent_matches,
        'total_goals': total_goals,
    })

def manage_players(request):
    players = Player.objects.select_related('team').all()
    teams = Team.objects.all()
    return render(request, 'players.html', {
        'players': players,
        'teams': teams,
    })

def manage_teams(request):
    teams = Team.objects.all()
    return render(request, 'teams.html', {'teams': teams})

def schedule(request):
    matches = Match.objects.select_related('team_a', 'team_b').order_by('datetime')
    return render(request, 'matches.html', {'matches': matches})

def standings(request):
    teams = Team.objects.all()
    matches = Match.objects.filter(status='FINISHED')

    table = []
    for team in teams:
        played = won = drawn = lost = gf = ga = pts = 0
        for m in matches:
            if m.team_a == team:
                played += 1; gf += m.score_a; ga += m.score_b
                if m.score_a > m.score_b: won += 1; pts += 3
                elif m.score_a == m.score_b: drawn += 1; pts += 1
                else: lost += 1
            elif m.team_b == team:
                played += 1; gf += m.score_b; ga += m.score_a
                if m.score_b > m.score_a: won += 1; pts += 3
                elif m.score_b == m.score_a: drawn += 1; pts += 1
                else: lost += 1
        table.append({
            'team': team, 'played': played, 'won': won,
            'drawn': drawn, 'lost': lost, 'gf': gf,
            'ga': ga, 'gd': gf - ga, 'pts': pts
        })

    table.sort(key=lambda x: (-x['pts'], -x['gd'], -x['gf']))
    return render(request, 'standings.html', {'table': table})

# AJAX APIs สำหรับ Admin
@require_POST
def add_player(request):
    data = json.loads(request.body)
    team = Team.objects.get(id=data['team_id']) if data.get('team_id') else None
    Player.objects.create(
        name=data['name'], age=data['age'],
        position=data['position'], team=team,
        apps=data.get('apps', 0), goals=data.get('goals', 0),
        assists=data.get('assists', 0)
    )
    return JsonResponse({'status': 'ok'})

@require_POST
def edit_player(request, pk):
    data = json.loads(request.body)
    player = get_object_or_404(Player, pk=pk)
    team = Team.objects.get(id=data['team_id']) if data.get('team_id') else None
    player.name = data['name']; player.age = data['age']
    player.position = data['position']; player.team = team
    player.apps = data.get('apps', 0); player.goals = data.get('goals', 0)
    player.assists = data.get('assists', 0)
    player.save()
    return JsonResponse({'status': 'ok'})

@require_POST
def delete_player(request, pk):
    get_object_or_404(Player, pk=pk).delete()
    return JsonResponse({'status': 'ok'})

@require_POST
def add_team(request):
    data = json.loads(request.body)
    Team.objects.create(name=data['name'], icon=data['icon'], color=data['color'])
    return JsonResponse({'status': 'ok'})

@require_POST
def delete_team(request, pk):
    get_object_or_404(Team, pk=pk).delete()
    return JsonResponse({'status': 'ok'})

@require_POST
def add_match(request):
    data = json.loads(request.body)
    Match.objects.create(
        team_a=Team.objects.get(id=data['team_a']),
        team_b=Team.objects.get(id=data['team_b']),
        datetime=data['datetime'],
        venue=data['venue']
    )
    return JsonResponse({'status': 'ok'})

@require_POST
def save_score(request, pk):
    data = json.loads(request.body)
    match = get_object_or_404(Match, pk=pk)
    match.score_a = data['score_a']
    match.score_b = data['score_b']
    match.status = 'FINISHED'
    match.save()
    return JsonResponse({'status': 'ok'})

@require_POST
def delete_match(request, pk):
    get_object_or_404(Match, pk=pk).delete()
    return JsonResponse({'status': 'ok'})