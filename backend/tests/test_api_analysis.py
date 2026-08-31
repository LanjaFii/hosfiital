from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.models import Recommendation, Analysis
from datetime import date


client = TestClient(app)


def test_post_analysis_valid():
    payload = {'start': '2026-08-01', 'end': '2026-08-01', 'triggered_by': 'test-api'}
    r = client.post('/analyses', json=payload)
    assert r.status_code == 201
    j = r.json()
    assert 'analysis_id' in j
    # cleanup created analysis via DB
    session = SessionLocal()
    aid = j['analysis_id']
    session.query(Recommendation).filter_by(analysis_id=aid).delete()
    session.query(Analysis).filter_by(id=aid).delete()
    session.commit()
    session.close()


def test_post_analysis_invalid_period():
    payload = {'start': '2026-08-02', 'end': '2026-08-01'}
    r = client.post('/analyses', json=payload)
    assert r.status_code == 422 or r.status_code == 400


def test_get_analysis_existing():
    # create via POST
    payload = {'start': '2026-08-04', 'end': '2026-08-04', 'triggered_by': 'test-get'}
    r = client.post('/analyses', json=payload)
    aid = r.json()['analysis_id']
    g = client.get(f'/analyses/{aid}')
    assert g.status_code == 200
    data = g.json()
    assert data['id'] == aid
    # cleanup
    session = SessionLocal()
    session.query(Recommendation).filter_by(analysis_id=aid).delete()
    session.query(Analysis).filter_by(id=aid).delete()
    session.commit()
    session.close()


def test_get_analysis_nonexistent():
    g = client.get('/analyses/99999999')
    assert g.status_code == 404


def test_list_analyses_filters():
    # create one
    payload = {'start': '2026-08-05', 'end': '2026-08-05', 'triggered_by': 'test-list'}
    r = client.post('/analyses', json=payload)
    aid = r.json()['analysis_id']
    # list without date filter should include it
    l = client.get('/analyses')
    assert l.status_code == 200
    assert any(a['id'] == aid for a in l.json())
    # cleanup
    session = SessionLocal()
    session.query(Recommendation).filter_by(analysis_id=aid).delete()
    session.query(Analysis).filter_by(id=aid).delete()
    session.commit()
    session.close()


def test_patch_recommendation_valid():
    # create analysis to have recommendation
    payload = {'start': '2026-08-06', 'end': '2026-08-06', 'triggered_by': 'test-patch'}
    r = client.post('/analyses', json=payload)
    aid = r.json()['analysis_id']
    # fetch one recommendation id
    session = SessionLocal()
    rec = session.query(Recommendation).filter_by(analysis_id=aid).first()
    if rec is None:
        # create a test recommendation
        rrec = Recommendation(analysis_id=aid, service_id=None, text='test', type='test', status='open')
        session.add(rrec)
        session.commit()
        rid = rrec.id
    else:
        rid = rec.id
    p = client.patch(f'/recommendations/{rid}', json={'status': 'accepted'})
    assert p.status_code == 200
    assert p.json()['status'] == 'accepted'
    # cleanup
    session.query(Recommendation).filter_by(analysis_id=aid).delete()
    session.query(Analysis).filter_by(id=aid).delete()
    session.commit()
    session.close()


def test_patch_recommendation_nonexistent():
    p = client.patch('/recommendations/99999999', json={'status': 'accepted'})
    assert p.status_code == 404


def test_patch_recommendation_invalid_status():
    # create analysis to have recommendation
    payload = {'start': '2026-08-07', 'end': '2026-08-07', 'triggered_by': 'test-patch2'}
    r = client.post('/analyses', json=payload)
    aid = r.json()['analysis_id']
    session = SessionLocal()
    rec = session.query(Recommendation).filter_by(analysis_id=aid).first()
    if rec is None:
        rrec = Recommendation(analysis_id=aid, service_id=None, text='test', type='test', status='open')
        session.add(rrec)
        session.commit()
        rid = rrec.id
    else:
        rid = rec.id
    p = client.patch(f'/recommendations/{rid}', json={'status': 'invalid_status'})
    assert p.status_code == 422 or p.status_code == 400
    # cleanup
    session.query(Recommendation).filter_by(analysis_id=aid).delete()
    session.query(Analysis).filter_by(id=aid).delete()
    session.commit()
    session.close()
