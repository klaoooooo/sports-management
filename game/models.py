from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='fa-shield-halved')
    color = models.CharField(max_length=7, default='#22c55e')

    def __str__(self):
        return self.name

class Player(models.Model):
    POSITION_CHOICES = [
        ('กองหน้า', 'กองหน้า (FW)'),
        ('กองกลาง', 'กองกลาง (MF)'),
        ('กองหลัง', 'กองหลัง (DF)'),
        ('ผู้รักษาประตู', 'ผู้รักษาประตู (GK)'),
    ]
    name = models.CharField(max_length=100)
    age = models.IntegerField(default=0)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    apps = models.IntegerField(default=0)
    goals = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Match(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'รอแข่งขัน'),
        ('FINISHED', 'แข่งขันแล้ว'),
    ]
    team_a = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    team_b = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    score_a = models.IntegerField(default=0)
    score_b = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SCHEDULED')
    datetime = models.DateTimeField()
    venue = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.team_a} vs {self.team_b}"