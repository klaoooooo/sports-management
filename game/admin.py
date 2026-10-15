from django.contrib import admin
from .models import Profile, Sport, Athlete, Event, CompetesIn, FieldPoint, TrackPoint

for m in (Profile, Sport, Athlete, Event, CompetesIn, FieldPoint, TrackPoint):
    admin.site.register(m)
