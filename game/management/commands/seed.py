"""สร้างข้อมูลตัวอย่างสำหรับเดโม:  python manage.py seed  (ใส่ --reset เพื่อล้างข้อมูลเดิม)"""
from datetime import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from game.models import (Athlete, CompetesIn, Event, FieldPoint, Profile, Sport, TrackPoint)
from game.scoring import calculate_event

PASSWORD = 'Pass1234!'

ATHLETES = [
    # country, bib, first, last, gender, class
    ('THA', '872', 'Chaiwat', 'Rattana', 'Men', 'T34'),
    ('THA', '843', 'Sombun', 'Phrimkhun', 'Men', 'T34'),
    ('THA', '829', 'Arnon', 'Nawong', 'Men', 'T34'),
    ('UAE', '1001', 'Mohamad', 'Alhama', 'Men', 'T33'),
    ('MAS', '607', 'Ahmad Fizzi', 'Rosni', 'Men', 'T36'),
    ('MAS', '601', 'Zulkifly', 'Abdullah', 'Men', 'F13'),
    ('INA', '201', 'Jaenal', 'Aripin', 'Men', 'F13'),
    ('CAM', '101', 'Chantrea', 'Leng', 'Men', 'F13'),
    ('THA', '834', 'Sukanya', 'Pandongyang', 'Women', 'T54'),
    ('INA', '204', 'Nanda Mei', 'Sholihah', 'Women', 'T54'),
    ('MAS', '602', 'Siti', 'Noorain', 'Women', 'T54'),
]


class Command(BaseCommand):
    help = 'Seed demo data'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true')

    def handle(self, *args, **opts):
        if opts['reset']:
            for m in (CompetesIn, Event, Athlete, Sport, TrackPoint, FieldPoint):
                m.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()

        # users
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', PASSWORD)
        for name, role, country in [('judge1', 'judge', ''), ('agent_tha', 'agent', 'THA'),
                                    ('visitor1', 'visitor', '')]:
            u, _ = User.objects.get_or_create(username=name)
            u.set_password(PASSWORD); u.save()
            Profile.objects.update_or_create(user=u, defaults={'role': role, 'country': country})
        sp, _ = User.objects.get_or_create(username='sporter1')
        sp.set_password(PASSWORD); sp.save()
        Profile.objects.update_or_create(user=sp, defaults={'role': 'sporter', 'country': 'THA'})

        # athletes
        ath = {}
        for c, bib, f, l, g, cl in ATHLETES:
            ath[bib], _ = Athlete.objects.update_or_create(
                bib=bib, country=c,
                defaults=dict(first_name=f, last_name=l, gender=g, classification=cl))
        a = ath['872']; a.user = sp; a.save()

        # point parameters (ค่าสมมติ จนกว่าอาจารย์จะประกาศกติกา) points = a * x^b + c
        for cls, ref in (('T34', 15.0), ('T33', 20.0)):
            TrackPoint.objects.update_or_create(gender='M', event='100 m', classification=cls,
                                                defaults=dict(a=1000 * ref, b=-1, c=0))
        FieldPoint.objects.update_or_create(gender='M', event='Shot Put', classification='F13',
                                            defaults=dict(a=1000 / 14.0, b=1, c=0))

        # events
        track, _ = Sport.objects.get_or_create(type='Track', sub_type='Sprint')
        field, _ = Sport.objects.get_or_create(type='Field', sub_type='Throw')
        judge = User.objects.get(username='judge1')

        def ev(num, name, sport, gender, cls, when, status, judge_=None):
            e, _ = Event.objects.update_or_create(
                number=num, defaults=dict(
                    sport=sport, name=name, gender=gender, classification=cls, stage='final',
                    status=status, judge=judge_, location='80th Birthday Stadium, Khon Kaen',
                    score_format='time' if sport.type == 'Track' else 'distance',
                    date_time=timezone.make_aware(when)))
            return e

        def enter(e, rows):
            for i, (bib, score) in enumerate(rows, start=1):
                CompetesIn.objects.update_or_create(
                    event=e, athlete=ath[bib],
                    defaults=dict(order=i, score={'value': score} if score else None))

        e1 = ev('104', '100 m', track, 'Men', 'T33/34', datetime(2026, 10, 18, 15, 30), 'result', judge)
        enter(e1, [('872', 14.98), ('1001', 15.75), ('843', 16.70), ('829', 18.79)])
        calculate_event(e1)

        e2 = ev('101', 'Shot Put', field, 'Men', 'F13', datetime(2026, 10, 18, 15, 0), 'result')
        enter(e2, [('601', 11.20), ('201', 10.50), ('101', 9.80)])
        calculate_event(e2)

        e3 = ev('108', '100 m', track, 'Women', 'T54', datetime(2026, 10, 18, 15, 50), 'live', judge)
        enter(e3, [('834', None), ('204', None), ('602', None)])

        e4 = ev('120', '400 m', track, 'Men', 'T34/36', datetime(2026, 10, 19, 9, 30), 'start-list')
        enter(e4, [('843', None), ('607', None)])

        self.stdout.write(self.style.SUCCESS('Seed OK'))
        self.stdout.write(f'Logins (password {PASSWORD}): admin, judge1, agent_tha, sporter1, visitor1')
