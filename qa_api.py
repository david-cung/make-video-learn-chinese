"""Run with the local studio listening on port 3015."""
import json,pathlib,urllib.request,urllib.error
BASE='http://127.0.0.1:3015'
def request(path,data=None,headers=None):
    h={'Content-Type':'application/json',**(headers or {})}
    return urllib.request.urlopen(urllib.request.Request(BASE+path,None if data is None else json.dumps(data).encode(),h))
with request('/') as r: assert r.status==200
with request('/api/plan',{'topic':'Gọi cà phê'}) as r: plan=json.load(r)
bad=json.loads(json.dumps(plan));bad['scenes'][1]['text']='ni hao'
try:
    request('/api/jobs',bad)
    raise AssertionError('Invalid Chinese audio text accepted')
except urllib.error.HTTPError as e: assert e.code==400
try:
    request('/api/plan',{'topic':'cà phê'},{'Origin':'https://unrelated.example'})
    raise AssertionError('Cross-origin action accepted')
except urllib.error.HTTPError as e: assert e.code==403
with request('/api/jobs') as r: jobs=json.load(r)
job=next(j for j in jobs if j['status']=='done')
with request(job['video'],headers={'Range':'bytes=0-127'}) as r:
    assert r.status==206 and len(r.read())==128
with request(job['subtitles']) as r: assert '-->' in r.read().decode('utf-8-sig')
print('API PASS: page, planning, language validation, origin check, video range, subtitles')
