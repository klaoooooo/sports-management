from django.urls import path
from game import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('manage_players/', views.manage_players, name='manage_players'),
    path('manage_teams/', views.manage_teams, name='manage_teams'),
    path('schedule/', views.schedule, name='schedule'),
    path('standings/', views.standings, name='standings'),

    # APIs
    path('api/player/add/', views.add_player, name='add_player'),
    path('api/player/edit/<int:pk>/', views.edit_player, name='edit_player'),
    path('api/player/delete/<int:pk>/', views.delete_player, name='delete_player'),
    path('api/team/add/', views.add_team, name='add_team'),
    path('api/team/delete/<int:pk>/', views.delete_team, name='delete_team'),
    path('api/match/add/', views.add_match, name='add_match'),
    path('api/match/score/<int:pk>/', views.save_score, name='save_score'),
    path('api/match/delete/<int:pk>/', views.delete_match, name='delete_match'),
]