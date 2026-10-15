from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLES = [
        ('admin', 'Admin'),
        ('agent', 'Agent'),
        ('sporter', 'Sporter'),
        ('judge', 'Judge'),
        ('visitor', 'Visitor'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLES, default='visitor')
    country = models.CharField(max_length=5, blank=True)   # ใช้กับ agent

    def __str__(self):
        return f"{self.user.username} ({self.role})"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={'role': 'admin' if instance.is_superuser else 'visitor'},
        )


class Sport(models.Model):
    type = models.CharField(max_length=100)          # Track / Field
    sub_type = models.CharField(max_length=100, blank=True)
    remark = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.type} {self.sub_type}".strip()


class Athlete(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='athlete')
    email = models.EmailField(blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    profile_pic = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=5)          # THA, MAS ...
    bib = models.CharField(max_length=10)
    gender = models.CharField(max_length=10)          # Men / Women
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=255, blank=True)
    classification = models.CharField(max_length=50)  # T34, F13 ...
    remark = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['country', 'bib']

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name.upper()}"

    def __str__(self):
        return f"{self.bib} {self.full_name}"


class Event(models.Model):
    STATUS = [('start-list', 'Start list'), ('live', 'Live'), ('result', 'Result')]
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    judge = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='judged_events')    # ไม่บังคับ
    number = models.CharField(max_length=255)
    name = models.CharField(max_length=255)                    # 100 m, Shot Put
    classification = models.CharField(max_length=255)
    date_time = models.DateTimeField()
    gender = models.CharField(max_length=10)
    status = models.CharField(max_length=50, choices=STATUS, default='start-list')
    location = models.TextField(blank=True)
    stage = models.CharField(max_length=50, default='final')
    score_format = models.CharField(max_length=100, blank=True)  # time / distance
    remark = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['date_time', 'number']

    @property
    def is_track(self):
        return self.sport.type.strip().lower() == 'track'

    def __str__(self):
        return f"[{self.number}] {self.name} {self.gender} {self.classification}"


class CompetesIn(models.Model):
    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    score = models.JSONField(null=True, blank=True)     # {"value": 14.98}
    medal = models.IntegerField(default=0)               # 0 / 1 gold / 2 silver / 3 bronze
    rank = models.IntegerField(null=True, blank=True)
    point = models.IntegerField(default=0)
    order = models.IntegerField(default=0)
    remark = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('athlete', 'event')
        ordering = ['order', 'id']

    @property
    def score_value(self):
        if isinstance(self.score, dict):
            try:
                return float(self.score.get('value'))
            except (TypeError, ValueError):
                return None
        return None

    @property
    def score_display(self):
        v = self.score_value
        if v is None:
            return '-'
        if self.event.score_format == 'time':
            if v >= 60:
                m, s = divmod(v, 60)
                return f"{int(m)}:{s:05.2f}"
            return f"{v:.2f} s"
        return f"{v:.2f} m"


class PointParam(models.Model):
    """พารามิเตอร์สูตรแต้ม: points = a * (ผลงาน ** b) + c"""
    gender = models.CharField(max_length=1)            # M / W
    event = models.CharField(max_length=15)            # ชื่อ event เช่น "100 m"
    classification = models.CharField(max_length=10)   # เช่น T34
    a = models.FloatField()
    b = models.FloatField()
    c = models.FloatField(default=0)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.gender} {self.event} {self.classification}"


class FieldPoint(PointParam):
    pass


class TrackPoint(PointParam):
    pass
