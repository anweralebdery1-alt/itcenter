"""Sync client to run on POS machine. Reads local SQLite change_log (from your EXE) and pushes to server.
Usage: set SERVER_URL and API_TOKEN then run: python sync_client.py
"""
import sqlite3, json, requests, os
SERVER_URL = os.environ.get('SYNC_SERVER','http://localhost:8000')
API_TOKEN = os.environ.get('SYNC_API_TOKEN','changeme_token')
LOCAL_DB = r"D:\shop\old\offlinesales\store.db"


def read_changes():
    if not os.path.exists(LOCAL_DB):
        print('local DB not found:', LOCAL_DB); return []
    conn = sqlite3.connect(LOCAL_DB)
    cur = conn.cursor()
    try:
        cur.execute('SELECT id, table_name, pk, operation, data_json, ts_utc FROM change_log WHERE synced=0')
    except Exception as e:
        print('change_log missing or error:', e); return []
    rows = cur.fetchall(); conn.close()
    changes = []
    for r in rows:
        try:
            data = json.loads(r[4]) if r[4] else {}
        except:
            data = {}
        changes.append({'id': r[0], 'table': r[1], 'operation': r[3], 'data': data, 'ts': r[5]})
    return changes


def push(changes):
    if not changes:
        print('no changes to push')
        return
    payload = {'device_id':'POS-01','changes':changes}
    headers = {'Authorization': 'Token ' + API_TOKEN, 'Content-Type':'application/json'}
    url = SERVER_URL.rstrip('/') + '/api/sync/push/'
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        print('server response', r.status_code, r.text)
        if r.status_code==200:
            conn = sqlite3.connect(LOCAL_DB); cur = conn.cursor()
            ids = [str(c['id']) for c in changes]
            q = 'UPDATE change_log SET synced=1 WHERE id IN (%s)' % ','.join(ids)
            cur.execute(q); conn.commit(); conn.close()
    except Exception as e:
        print('push error', e)

if __name__ == '__main__':
    ch = read_changes()
    print('found', len(ch), 'changes')
    push(ch)
