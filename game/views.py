import json
import re

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from django.views.decorators.http import require_POST

from .forms import RegisterForm
from .models import Athlete, CompetesIn, Event, Sport
from .permission import (get_role, agent_country, can_edit_results,
                         can_manage_athlete, roles_required, api_roles)
from .scoring import calculate_event, parse_score


# ---------------------------------------------------------------- helpers
def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _err(message, status=400):
    return JsonResponse({'status': 'error', 'message': message}, status=status)


def _ok(**extra):
    return JsonResponse({'status': 'ok', **extra})


def _int_or_none(v):
    return None if v in (None, '') else int(v)


# ---------------------------------------------------------------- public pages
def medals(request):
    """หน้าแรก: ตารางสรุปเหรียญ (ไม่ต้องล็อกอิน) นับเฉพาะ event ที่ประกาศผลแล้ว"""
    rows = (CompetesIn.objects
            .filter(event__status='result', medal__in=[1, 2, 3])
            .values('athlete__country')
            .annotate(gold=Count('id', filter=Q(medal=1)),
                      silver=Count('id', filter=Q(medal=2)),
                      bronze=Count('id', filter=Q(medal=3))))
    table = {r['athlete__country']: {'country': r['athlete__country'], 'gold': r['gold'],
                                     'silver': r['silver'], 'bronze': r['bronze']} for r in rows}
    for c in Athlete.objects.values_list('country', flat=True).distinct():
        table.setdefault(c, {'country': c, 'gold': 0, 'silver': 0, 'bronze': 0})
    table = list(table.values())
    for r in table:
        r['total'] = r['gold'] + r['silver'] + r['bronze']
    table.sort(key=lambda r: (-r['gold'], -r['silver'], -r['bronze'], r['country']))

    return render(request, 'medals.html', {
        'table': table,
        'event_count': Event.objects.count(),
        'published_count': Event.objects.filter(status='result').count(),
        'athlete_count': Athlete.objects.count(),
        'country_count': len(table),
        'recent': Event.objects.filter(status='result').select_related('sport').order_by('-date_time')[:5],
    })


def events(request):
    qs = Event.objects.select_related('sport', 'judge').annotate(n=Count('competesin'))
    status = request.GET.get('status', '')
    if status in ('start-list', 'live', 'result'):
        qs = qs.filter(status=status)
    role = get_role(request.user)
    events_json = []
    if role == 'admin':
        for e in qs:
            events_json.append({
                'id': e.id, 'number': e.number, 'name': e.name, 'type': e.sport.type,
                'sub_type': e.sport.sub_type, 'classification': e.classification,
                'gender': e.gender, 'stage': e.stage, 'location': e.location,
                'judge_id': e.judge_id,
                'date_time': timezone.localtime(e.date_time).strftime('%Y-%m-%dT%H:%M'),
            })
    return render(request, 'events.html', {
        'events': qs, 'status': status, 'events_json': events_json,
        'judges': User.objects.filter(profile__role='judge') if role == 'admin' else [],
    })


def event_detail(request, pk):
    event = get_object_or_404(Event.objects.select_related('sport', 'judge'), pk=pk)
    entries = event.competesin_set.select_related('athlete')
    role = get_role(request.user)
    user = request.user

    available = []
    if role in ('admin', 'agent') and event.status != 'result':
        available = Athlete.objects.exclude(competesin__event=event)
        if role == 'agent':
            available = available.filter(country__iexact=agent_country(user))

    rows = []
    for e in entries:
        e.can_remove = can_manage_athlete(user, e.athlete.country) and (
            event.status != 'result' or role == 'admin')
        rows.append(e)

    my_athlete = getattr(user, 'athlete', None) if user.is_authenticated else None
    joined = bool(my_athlete) and any(e.athlete_id == my_athlete.id for e in rows)
    open_event = event.status == 'start-list'
    return render(request, 'event_detail.html', {
        'event': event, 'entries': rows, 'available': available,
        'can_edit_results': user.is_authenticated and can_edit_results(user, event),
        'can_join': role == 'sporter' and bool(my_athlete) and open_event and not joined,
        'can_leave': role == 'sporter' and joined and open_event,
        'can_claim': role == 'judge' and event.judge_id is None and event.status != 'result',
        'can_release': role == 'judge' and event.judge_id == user.id and event.status != 'result',
    })


def results(request):
    role = get_role(request.user)
    qs = Event.objects.select_related('sport', 'judge').annotate(n=Count('competesin'))
    if role not in ('admin', 'judge'):
        qs = qs.filter(status__in=['live', 'result'])
    status = request.GET.get('status', '')
    if status in ('start-list', 'live', 'result'):
        qs = qs.filter(status=status)
    rows = []
    for e in qs:
        e.can_edit = request.user.is_authenticated and can_edit_results(request.user, e)
        rows.append(e)
    return render(request, 'results.html', {'events': rows, 'status': status})


def result_detail(request, pk):
    event = get_object_or_404(Event.objects.select_related('sport', 'judge'), pk=pk)
    can_edit = request.user.is_authenticated and can_edit_results(request.user, event)
    if not can_edit and event.status == 'start-list':
        messages.info(request, 'การแข่งขันนี้ยังไม่เริ่ม ยังไม่มีผล')
        return redirect('event_detail', pk=pk)
    entries = event.competesin_set.select_related('athlete')
    if not can_edit:
        entries = entries.order_by('rank', 'order') if event.status == 'result' else entries
    return render(request, 'result_detail.html', {
        'event': event, 'entries': entries, 'can_edit': can_edit,
        'show_scores': can_edit or event.status == 'result',
    })


def athletes(request):
    qs = Athlete.objects.all()
    rows, js = [], []
    for a in qs:
        a.can_manage = can_manage_athlete(request.user, a.country)
        rows.append(a)
        if a.can_manage:
            js.append({'id': a.id, 'email': a.email, 'first_name': a.first_name,
                       'last_name': a.last_name, 'country': a.country, 'bib': a.bib,
                       'gender': a.gender, 'classification': a.classification,
                       'date_of_birth': a.date_of_birth.isoformat() if a.date_of_birth else '',
                       'phone_number': a.phone_number, 'remark': a.remark})
    return render(request, 'athletes.html', {
        'athletes': rows, 'athletes_json': js,
        'countries': sorted({a.country for a in rows}),
        'agent_country': agent_country(request.user) if get_role(request.user) == 'agent' else '',
    })


def athlete_detail(request, pk):
    athlete = get_object_or_404(Athlete, pk=pk)
    entries = (athlete.competesin_set.select_related('event', 'event__sport')
               .order_by('event__date_time'))
    pub = [e for e in entries if e.event.status == 'result']
    return render(request, 'athlete_detail.html', {
        'athlete': athlete, 'entries': entries,
        'gold': sum(1 for e in pub if e.medal == 1),
        'silver': sum(1 for e in pub if e.medal == 2),
        'bronze': sum(1 for e in pub if e.medal == 3),
    })


# ---------------------------------------------------------------- auth / profile
def register(request):
    if request.user.is_authenticated:
        return redirect('medals')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'สมัครสมาชิกสำเร็จ')
        return redirect('medals')
    return render(request, 'register.html', {'form': form})


@roles_required('admin', 'agent', 'sporter', 'judge', 'visitor')
def me(request):
    athlete = getattr(request.user, 'athlete', None)
    if request.method == 'POST' and athlete:
        athlete.first_name = request.POST.get('first_name', athlete.first_name).strip()
        athlete.last_name = request.POST.get('last_name', athlete.last_name).strip()
        athlete.classification = request.POST.get('classification', athlete.classification).strip()
        athlete.phone_number = request.POST.get('phone_number', '').strip()
        athlete.date_of_birth = parse_date(request.POST.get('date_of_birth', '')) or None
        athlete.save()
        messages.success(request, 'บันทึกโปรไฟล์แล้ว')
        return redirect('me')
    entries = (athlete.competesin_set.select_related('event') if athlete else [])
    return render(request, 'me.html', {'athlete': athlete, 'entries': entries})


# ---------------------------------------------------------------- APIs: athlete
@require_POST
@api_roles('admin', 'agent')
def api_athlete_save(request):
    d = _body(request)
    pk = d.get('id')
    athlete = get_object_or_404(Athlete, pk=pk) if pk else Athlete()
    country = (d.get('country') or '').strip().upper()
    if not can_manage_athlete(request.user, country) or (pk and not can_manage_athlete(request.user, athlete.country)):
        return _err('Agent จัดการได้เฉพาะนักกีฬาของประเทศตนเอง', 403)
    for f in ('first_name', 'last_name', 'bib', 'gender', 'classification'):
        if not str(d.get(f, '')).strip():
            return _err(f'กรุณากรอก {f}')
    if not country:
        return _err('กรุณากรอก country')
    athlete.first_name = d['first_name'].strip()
    athlete.last_name = d['last_name'].strip()
    athlete.country = country
    athlete.bib = d['bib'].strip()
    athlete.gender = d['gender']
    athlete.classification = d['classification'].strip()
    athlete.email = d.get('email', '')
    athlete.phone_number = d.get('phone_number', '')
    athlete.remark = d.get('remark', '')
    athlete.date_of_birth = parse_date(d.get('date_of_birth') or '') or None
    athlete.save()
    return _ok()


@require_POST
@api_roles('admin', 'agent')
def api_athlete_delete(request, pk):
    athlete = get_object_or_404(Athlete, pk=pk)
    if not can_manage_athlete(request.user, athlete.country):
        return _err('ไม่มีสิทธิ์ลบนักกีฬาคนนี้', 403)
    athlete.delete()
    return _ok()


# ---------------------------------------------------------------- APIs: event
@require_POST
@api_roles('admin')
def api_event_save(request):
    d = _body(request)
    pk = d.get('id')
    event = get_object_or_404(Event, pk=pk) if pk else Event()
    for f in ('number', 'name', 'gender', 'classification', 'date_time', 'type'):
        if not str(d.get(f, '')).strip():
            return _err(f'กรุณากรอก {f}')
    dt = parse_datetime(d['date_time'])
    if dt is None:
        return _err('รูปแบบวันเวลาไม่ถูกต้อง')
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    sport, _ = Sport.objects.get_or_create(type=d['type'], sub_type=(d.get('sub_type') or '').strip())
    event.sport = sport
    event.number = d['number'].strip()
    event.name = d['name'].strip()
    event.gender = d['gender']
    event.classification = d['classification'].strip()
    event.date_time = dt
    event.stage = d.get('stage') or 'final'
    event.location = d.get('location', '')
    event.score_format = 'time' if sport.type.lower() == 'track' else 'distance'
    event.judge = User.objects.filter(pk=d['judge_id']).first() if d.get('judge_id') else None
    event.save()
    return _ok()


@require_POST
@api_roles('admin')
def api_event_delete(request, pk):
    get_object_or_404(Event, pk=pk).delete()
    return _ok()


@require_POST
@api_roles('admin', 'agent')
def api_entry_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    d = _body(request)
    athlete = get_object_or_404(Athlete, pk=d.get('athlete_id'))
    if not can_manage_athlete(request.user, athlete.country):
        return _err('เพิ่มได้เฉพาะนักกีฬาของประเทศตนเอง', 403)
    if event.status == 'result':
        return _err('Event นี้ประกาศผลแล้ว เพิ่มนักกีฬาไม่ได้')
    if CompetesIn.objects.filter(event=event, athlete=athlete).exists():
        return _err('นักกีฬาคนนี้อยู่ใน event นี้แล้ว')
    CompetesIn.objects.create(event=event, athlete=athlete,
                              order=event.competesin_set.count() + 1)
    return _ok()


@require_POST
@api_roles('admin', 'agent')
def api_entry_delete(request, pk):
    entry = get_object_or_404(CompetesIn.objects.select_related('athlete', 'event'), pk=pk)
    if not can_manage_athlete(request.user, entry.athlete.country):
        return _err('ไม่มีสิทธิ์', 403)
    if entry.event.status == 'result' and get_role(request.user) != 'admin':
        return _err('Event นี้ประกาศผลแล้ว')
    entry.delete()
    return _ok()


# ---------------------------------------------------------------- APIs: result
@require_POST
@api_roles('admin', 'judge')
def api_result_save(request, pk):
    event = get_object_or_404(Event.objects.select_related('sport'), pk=pk)
    if not can_edit_results(request.user, event):
        return _err('คุณไม่ใช่กรรมการของ event นี้', 403)
    d = _body(request)
    recalc = bool(d.get('recalc'))
    try:
        with transaction.atomic():
            entries = {e.id: e for e in event.competesin_set.all()}
            for row in d.get('entries', []):
                e = entries.get(int(row['id']))
                if not e:
                    continue
                raw = row.get('score')
                e.score = None if raw in (None, '') else {'value': parse_score(raw)}
                if not recalc:
                    e.rank = _int_or_none(row.get('rank'))
                    e.point = int(row.get('point') or 0)
                    e.medal = int(row.get('medal') or 0)
                e.remark = row.get('remark', e.remark)
                e.save()
            if recalc:
                calculate_event(event)
            if d.get('status') in ('start-list', 'live', 'result'):
                event.status = d['status']
                event.save()
    except (ValueError, TypeError, KeyError):
        return _err('ข้อมูลไม่ถูกต้อง (คะแนนต้องเป็นตัวเลข เช่น 14.98 หรือ 4:05.30)')
    return _ok()


# ---------------------------------------------------------------- self-service: sporter / judge
def _class_tokens(text):
    """'T12/13/20' -> {'T12','T13','T20'}"""
    tokens, prefix = set(), ''
    for part in re.split(r'[/,\s]+', (text or '').upper()):
        if not part:
            continue
        m = re.match(r'^([TF])?(\d+)$', part)
        if m:
            if m.group(1):
                prefix = m.group(1)
            tokens.add(f"{prefix}{m.group(2)}")
        else:
            tokens.add(part)
    return tokens


def _ineligible_reason(event, athlete):
    if athlete.classification.upper() not in _class_tokens(event.classification):
        return f'Class ของคุณ ({athlete.classification}) ไม่ตรงกับ event นี้ ({event.classification})'
    if event.gender in ('Men', 'Women') and athlete.gender != event.gender:
        return f'Event นี้สำหรับ {event.gender} เท่านั้น'
    return None


@require_POST
@api_roles('sporter')
def api_event_join(request, pk):
    event = get_object_or_404(Event, pk=pk)
    athlete = getattr(request.user, 'athlete', None)
    if not athlete:
        return _err('ไม่พบโปรไฟล์นักกีฬาของคุณ')
    if athlete.classification.strip().upper() in ('', 'TBD'):
        return _err('กรุณาระบุ Classification ในหน้า My profile ก่อนสมัคร')
    if event.status != 'start-list':
        return _err('สมัครได้เฉพาะ event ที่ยังเป็น Start list')
    reason = _ineligible_reason(event, athlete)
    if reason:
        return _err(reason)
    if CompetesIn.objects.filter(event=event, athlete=athlete).exists():
        return _err('คุณสมัคร event นี้แล้ว')
    CompetesIn.objects.create(event=event, athlete=athlete, order=event.competesin_set.count() + 1)
    return _ok()


@require_POST
@api_roles('sporter')
def api_event_leave(request, pk):
    athlete = getattr(request.user, 'athlete', None)
    entry = get_object_or_404(CompetesIn.objects.select_related('event'), event_id=pk, athlete=athlete)
    if entry.event.status != 'start-list':
        return _err('ถอนตัวได้เฉพาะ event ที่ยังเป็น Start list')
    entry.delete()
    return _ok()


@require_POST
@api_roles('judge')
def api_event_judge(request, pk):
    event = get_object_or_404(Event, pk=pk)
    action = _body(request).get('action')
    if event.status == 'result':
        return _err('Event นี้ประกาศผลแล้ว')
    if action == 'claim':
        if event.judge_id and event.judge_id != request.user.id:
            return _err('Event นี้มีกรรมการแล้ว')
        event.judge = request.user
    elif action == 'release':
        if event.judge_id != request.user.id:
            return _err('คุณไม่ใช่กรรมการของ event นี้', 403)
        event.judge = None
    else:
        return _err('คำสั่งไม่ถูกต้อง')
    event.save()
    return _ok()