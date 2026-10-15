"""คำนวณแต้ม อันดับ และเหรียญของ event

กติกาแต้มของอาจารย์ "จะประกาศภายหลัง" จึงแยกสูตรไว้ที่ไฟล์นี้ไฟล์เดียว
- ถ้ามีแถวพารามิเตอร์ใน TrackPoint/FieldPoint (ตรง เพศ + ชื่อ event + class)
  ใช้สูตร  points = a * (ผลงาน ** b) + c
- ถ้าไม่มี ใช้ค่าเริ่มต้น: เทียบกับผลงานที่ดีที่สุดใน event นั้น (1000 แต้ม = ดีที่สุด)
อันดับเรียงตามแต้มมากไปน้อย (คนเข้าเส้นชัยก่อนจึงไม่จำเป็นต้องชนะ)
"""
from .models import TrackPoint, FieldPoint

GENDER_CODE = {'men': 'M', 'male': 'M', 'women': 'W', 'female': 'W'}


def parse_score(raw):
    """รับ '14.98' หรือ '4:05.30' คืนค่าเป็นวินาที/เมตร (float)"""
    s = str(raw).strip().replace(',', '.')
    if ':' in s:
        minutes, seconds = s.split(':', 1)
        return int(minutes) * 60 + float(seconds)
    return float(s)


def _params(event, athlete):
    model = TrackPoint if event.is_track else FieldPoint
    code = GENDER_CODE.get(athlete.gender.lower(), athlete.gender[:1].upper())
    return model.objects.filter(
        gender=code, event=event.name, classification=athlete.classification
    ).first()


def calculate_event(event):
    entries = list(event.competesin_set.select_related('athlete'))
    scored = []
    for e in entries:
        v = e.score_value
        if v is not None and v > 0:
            scored.append((e, v))
        else:
            e.rank, e.point, e.medal = None, 0, 0
            e.save()
    if not scored:
        return

    values = [v for _, v in scored]
    best = min(values) if event.is_track else max(values)

    raw = []
    for e, v in scored:
        p = _params(event, e.athlete)
        if p:
            pts = p.a * (v ** p.b) + p.c
        else:
            pts = 1000 * best / v if event.is_track else 1000 * v / best
        raw.append((e, round(pts)))

    raw.sort(key=lambda t: -t[1])
    rank, prev = 0, None
    for i, (e, pts) in enumerate(raw, start=1):
        if pts != prev:
            rank, prev = i, pts
        e.point = pts
        e.rank = rank
        e.medal = rank if rank <= 3 else 0
        e.save()
