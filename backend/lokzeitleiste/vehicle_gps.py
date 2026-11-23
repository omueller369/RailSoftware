# GPS-Fahrten werden innerhalb derselben Transaktion wie ihre Aufzeichnung verdichtet.
from sqlalchemy import select
from .models import VehicleGpsJourney
from .gps_analysis import distance


def sync_journey(db,user,journey_id,payload):
    if not payload.get('ended') or not payload.get('vehicle_id'):return
    points=[p for p in payload.get('points',[]) if p['accuracy']<=50]
    if len(points)<2:return
    metres=0;previous=None
    for point in payload.get('points',[]):
        if point.get('break_before'):previous=None
        if point['accuracy']>50:continue
        if previous is not None:metres+=distance(previous,point)
        previous=point
    row=db.scalar(select(VehicleGpsJourney).where(VehicleGpsJourney.owner_id==user.id,VehicleGpsJourney.journey_id==journey_id,VehicleGpsJourney.started_ms==points[0]['t']))
    if row is None:
        row=VehicleGpsJourney(owner_id=user.id,journey_id=journey_id,started_ms=points[0]['t'],tf_number=user.username);db.add(row)
    row.vehicle_id=payload['vehicle_id'];row.from_code=payload.get('start_station') or '';row.to_code=payload.get('end_station') or '';row.distance_m=metres
