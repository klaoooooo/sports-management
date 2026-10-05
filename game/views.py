from django.shortcuts import render

def dashboard(request):
    return render(request, 'dashboard.html')  # ← เปลี่ยน

def players(request):
    return render(request, 'players.html')    # ← เปลี่ยน

def teams(request):
    return render(request, 'teams.html')      # ← เปลี่ยน

def matches(request):
    return render(request, 'matches.html')    # ← เปลี่ยน

def standings(request):
    return render(request, 'standings.html')

