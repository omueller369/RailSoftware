"""Shared personnel foundation for TF and future WGM portals; no new privileges."""
from ..models import EmployeeCategory


def category(db,user_id):
    row=db.get(EmployeeCategory,user_id)
    return row.category if row else 'tf'


def save_category(db,user_id,value):
    if value is None:return
    row=db.get(EmployeeCategory,user_id)
    if row:row.category=value
    else:db.add(EmployeeCategory(user_id=user_id,category=value))
