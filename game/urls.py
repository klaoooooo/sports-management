from django.contrib.auth import views as auth_views
from django.urls import path

from game import views
from game.forms import StyledLoginForm

urlpatterns = [
    # public
    path('', views.medals, name='medals'),
    path('events/', views.events, name='events'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('results/', views.results, name='results'),
    path('results/<int:pk>/', views.result_detail, name='result_detail'),
    path('athletes/', views.athletes, name='athletes'),
    path('athletes/<int:pk>/', views.athlete_detail, name='athlete_detail'),

    # auth
    path('login/', auth_views.LoginView.as_view(template_name='login.html',
                                                authentication_form=StyledLoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('me/', views.me, name='me'),

    # APIs
    path('api/athlete/save/', views.api_athlete_save, name='api_athlete_save'),
    path('api/athlete/<int:pk>/delete/', views.api_athlete_delete, name='api_athlete_delete'),
    path('api/event/save/', views.api_event_save, name='api_event_save'),
    path('api/event/<int:pk>/delete/', views.api_event_delete, name='api_event_delete'),
    path('api/event/<int:pk>/entry/add/', views.api_entry_add, name='api_entry_add'),
    path('api/entry/<int:pk>/delete/', views.api_entry_delete, name='api_entry_delete'),
    path('api/result/<int:pk>/save/', views.api_result_save, name='api_result_save'),
]
