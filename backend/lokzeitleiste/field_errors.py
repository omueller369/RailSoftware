"""Semantic form errors keep their readable message and add a stable field path."""
from fastapi import HTTPException
class FieldError(HTTPException):
    def __init__(self,message,loc,context=None):
        super().__init__(422,message)
        self.field_errors=[dict(loc=['body',*loc],msg=message,context=context or {})]


def validation_loc(error):
    """Map known report model checks to fields without echoing submitted values."""
    from .localization import source
    loc=list(error['loc']);message=str(error.get('ctx',{}).get('error',''))
    data=error.get('input')
    if not isinstance(data,dict):return loc
    end_checks=['e5bcd444576f','7191a2755c05','ecd10b0d9952','007ef8d9ea4c','2750690bb87f','a5efe0ebd18c','0f4caa8b3d88']
    if message in [source('server_work_reports_schemas.text_'+key) for key in end_checks]:return loc+['end_at']
    for token,field in [('a68a4fbcce44','reason_detail'),('a28beefb9700','cause_detail'),('90ea9c46ac6c','transport_detail')]:
        if message==source('server_work_reports_schemas.text_'+token):return loc+[field]
    if message==source('server_work_reports_schemas.text_8c8b67c386de'):
        if 'start_station' in data:
            return loc+['start_station' if not (data.get('start_station') or data.get('start_station_name')) else 'end_station']
        return loc+['station']
    if message in [source('server_work_reports_schemas.text_'+key) for key in ['7f776149fd52','daa968801d2d']]:
        from datetime import datetime
        try:
            start,end=(datetime.fromisoformat(data[key]) for key in ['start_at','end_at'])
            for ti,train in enumerate(data.get('train_journeys',[])):
                intervals=[(['train_journeys',ti],train)]+[(['train_journeys',ti,'events',ei],event) for ei,event in enumerate(train.get('events',[]))]
                for path,interval in intervals:
                    for key in ['start_at','end_at']:
                        if not start<=datetime.fromisoformat(interval[key])<=end:return loc+path+[key]
        except (ValueError,TypeError,KeyError):pass
    return loc
