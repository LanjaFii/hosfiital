from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from fastapi import status

from backend.app.analysis import orchestrator
from backend.app.db.session import SessionLocal
from backend.app.models.models import Analysis, Recommendation

router = APIRouter()


class AnalysisCreate(BaseModel):
    start: date
    end: date
    services: Optional[List[int]] = None
    rules: Optional[List[str]] = None
    triggered_by: Optional[str] = None

    @validator('end')
    def check_dates(cls, v, values):
        start = values.get('start')
        if start and v < start:
            raise ValueError('end must be >= start')
        return v


class AnalysisResponse(BaseModel):
    analysis_id: int
    status: str


class RecommendationPatch(BaseModel):
    status: str = Field(...)

    @validator('status')
    def validate_status(cls, v):
        allowed = {'open', 'accepted', 'rejected'}
        if v not in allowed:
            raise ValueError('invalid status')
        return v


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post('/analyses', response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def post_analysis(payload: AnalysisCreate, db=Depends(get_db)):
    # run synchronously and persist
    report = orchestrator.run_analysis(start=payload.start, end=payload.end, services=payload.services, kpi_provider=None, triggered_by=payload.triggered_by, persist=True, db_session=db)
    return {'analysis_id': report.get('analysis_id'), 'status': 'created'}


@router.get('/analyses/{analysis_id}')
def get_analysis(analysis_id: int, db=Depends(get_db)):
    a = db.query(Analysis).get(analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail='analysis not found')
    recs = db.query(Recommendation).filter_by(analysis_id=analysis_id).all()
    return {
        'id': a.id,
        'triggered_by': a.triggered_by,
        'triggered_at': a.triggered_at.isoformat() if a.triggered_at else None,
        'risk_level': a.risk_level,
        'kpi_snapshot': a.kpi_snapshot,
        'anomalies': a.anomalies,
        'recommendations': [{'id': r.id, 'service_id': r.service_id, 'text': r.text, 'status': r.status} for r in recs],
    }


@router.get('/analyses')
def list_analyses(service: Optional[int] = None, date: Optional[date] = None, db=Depends(get_db)):
    q = db.query(Analysis)
    if service is not None:
        q = q.join(Recommendation).filter(Recommendation.service_id == service)
    if date is not None:
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        q = q.filter(Analysis.triggered_at >= start).filter(Analysis.triggered_at <= end)
    items = q.order_by(Analysis.triggered_at.desc()).all()
    out = []
    for a in items:
        out.append({'id': a.id, 'triggered_at': a.triggered_at.isoformat() if a.triggered_at else None, 'risk_level': a.risk_level})
    return out


@router.patch('/recommendations/{rec_id}')
def patch_recommendation(rec_id: int, payload: RecommendationPatch, db=Depends(get_db)):
    r = db.query(Recommendation).get(rec_id)
    if not r:
        raise HTTPException(status_code=404, detail='recommendation not found')
    r.status = payload.status
    db.add(r)
    db.commit()
    return {'id': r.id, 'status': r.status}
