from django.urls import path
from game import views


urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('manage_players/', views.players, name='manage_players'),
    path('manage_teams/', views.teams, name='manage_teams'),
    path('matches_schedule/', views.matches, name='matches_schedule'),
    path('standings/', views.standings, name='standings'),
]