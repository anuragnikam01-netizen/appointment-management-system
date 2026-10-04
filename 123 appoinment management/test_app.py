import os, tempfile
import app as application

fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
application.DB_PATH = __import__('pathlib').Path(path)
application.init_db()
client = application.app.test_client()

def test_crud_and_date_normalization():
    r = client.post('/api/appointments', json={
        'name':'Test User','phone':'9876543210','date':'15/10/2026','time':'10:30',
        'purpose':'Project meeting','status':'Scheduled'
    })
    assert r.status_code == 201
    data = r.get_json(); assert data['date'] == '15-10-2026'
    appointment_id = data['id']
    r = client.put(f'/api/appointments/{appointment_id}', json={
        'name':'Updated User','phone':'9876543210','date':'16.10.2026','time':'11:15',
        'purpose':'Demo','status':'Completed'
    })
    assert r.status_code == 200 and r.get_json()['status'] == 'Completed'
    assert client.get('/api/stats').get_json()['completed'] == 1
    assert client.delete(f'/api/appointments/{appointment_id}').status_code == 200

def test_invalid_date():
    r = client.post('/api/appointments', json={'name':'A','phone':'9876543210','date':'2026-10-15','time':'10:30','purpose':'Demo','status':'Scheduled'})
    assert r.status_code == 400

if __name__ == '__main__':
    test_crud_and_date_normalization(); test_invalid_date(); print('All tests passed')
