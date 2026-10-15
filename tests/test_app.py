import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from brain_relay.app import create_app
from test_relay import capsule


@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING':True,'DATA_DIR':tmp_path,'MODEL_URL':'','MODEL_NAME':'','MODEL_KEY':''})


def authenticated(app):
    client=app.test_client()
    response=client.get('/api/bootstrap')
    assert response.status_code==200
    return client, {'X-CSRF-Token':response.json['csrf_token']}


def test_save_overwrites_and_survives_new_app_instance(app,tmp_path):
    client,headers=authenticated(app)
    original=capsule()
    response=client.post('/api/capsules',json=original,headers=headers)
    assert response.status_code==200
    original['goal']='新的目标\n中文 🌿'
    assert client.post('/api/capsules',json=original,headers=headers).status_code==200
    other=create_app({'TESTING':True,'DATA_DIR':tmp_path,'MODEL_URL':'','MODEL_NAME':'','MODEL_KEY':''}).test_client()
    assert other.get('/api/capsules/sample-1/export').json['goal']=='新的目标\n中文 🌿'
    assert len(other.get('/api/bootstrap').json['capsules'])==1


def test_export_import_preserves_unicode_false_states_and_text_html(app):
    client,headers=authenticated(app)
    original=capsule();original['context']='<img src=x onerror="alert(1)">\n📝'
    assert client.post('/api/import',json=original,headers=headers).status_code==200
    exported=client.get('/api/capsules/sample-1/export').json
    assert exported['context']==original['context']
    assert exported['decisions'][1]['confirmed'] is False
    assert exported['sources']==original['sources']
    assert client.get('/').status_code==200


def test_cross_site_and_missing_csrf_writes_are_blocked(app):
    client,headers=authenticated(app)
    assert client.post('/api/capsules',json=capsule()).status_code==403
    assert client.post('/api/capsules',json=capsule(),headers={**headers,'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/capsules',json=capsule(),headers={**headers,'Sec-Fetch-Site':'cross-site'}).status_code==403
    assert client.get('/api/bootstrap',headers={'Host':'evil.example'}).status_code==400
    assert client.get('/api/bootstrap').json['capsules']==[]


def test_actual_handoff_json_contract_and_budget_error(app):
    client,headers=authenticated(app)
    response=client.post('/api/handoff',json={'capsule':capsule(),'max_chars':20},headers=headers)
    assert response.status_code==422
    assert response.json['code']=='budget_too_small'
    assert response.json['omitted']['decisions']==2
    assert response.json['required_chars']>20
    response=client.post('/api/handoff',json={'capsule':capsule(),'max_chars':None},headers=headers)
    assert response.status_code==200 and '春日步道 🌿' in response.json['text']
    assert response.json['chars']==len(response.json['text'])


def test_no_key_means_no_fake_extraction(app):
    client,headers=authenticated(app)
    assert client.get('/api/bootstrap').json['model_configured'] is False
    response=client.post('/api/extract',json={'conversation':'hello','title':'A'},headers=headers)
    assert response.status_code==503
    assert response.json['code']=='model_not_configured'
    assert client.get('/api/bootstrap').json['capsules']==[]


def test_invalid_json_body_schema_and_oversize_are_errors(app):
    client,headers=authenticated(app)
    assert client.post('/api/import',data='{"broken"',content_type='application/json',headers=headers).status_code==400
    assert client.post('/api/import',json={'schema_version':2},headers=headers).status_code==400
    assert client.post('/api/import',data='x'*600000,content_type='application/json',headers=headers).status_code==413


def test_example_is_explicitly_synthetic_and_never_saves_itself(app):
    client,headers=authenticated(app)
    response=client.get('/api/example')
    assert response.status_code==200 and response.json['origin']=='demo'
    assert client.get('/api/bootstrap').json['capsules']==[]
    assert client.get('/styleguide').status_code==200


@pytest.mark.parametrize('url',['http://example.com/chat','file:///tmp/x','https://name:password@example.com/chat','https://example.com/chat#secret'])
def test_unsafe_provider_url_rejected_at_startup(tmp_path,url):
    with pytest.raises(ValueError):
        create_app({'TESTING':True,'DATA_DIR':tmp_path,'MODEL_URL':url,'MODEL_NAME':'test','MODEL_KEY':'synthetic-key'})


@pytest.fixture
def provider():
    state={'status':200,'content':capsule(),'requests':[]}
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['requests'].append((self.path,body,self.headers.get('Authorization')))
            self.send_response(state['status']);self.send_header('Content-Type','application/json');self.end_headers()
            payload={'choices':[{'message':{'content':json.dumps(state['content'],ensure_ascii=False)}}]}
            self.wfile.write(json.dumps(payload).encode())
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}/v1/chat/completions',state
    server.shutdown();server.server_close();thread.join()


def poll(client,task):
    for _ in range(100):
        response=client.get('/api/jobs/'+task)
        assert response.status_code==200
        if response.json['status'] in ('succeeded','failed'): return response.json
        time.sleep(.01)
    pytest.fail('local fake provider job did not terminate')


def test_configured_provider_returns_unconfirmed_draft_not_saved_product(tmp_path,provider):
    url,state=provider
    app=create_app({'TESTING':True,'DATA_DIR':tmp_path,'MODEL_URL':url,'MODEL_NAME':'test-model','MODEL_KEY':'synthetic-key'})
    client,headers=authenticated(app)
    response=client.post('/api/extract',json={'conversation':'Keep bilingual maps; reject visitor tracking.\n中文 📝','title':'Map'},headers=headers)
    assert response.status_code==202
    job=poll(client,response.json['task_id'])
    assert job['status']=='succeeded'
    draft=job['result'];assert draft['origin']=='configured provider'
    assert all(item['confirmed'] is False for key in ('decisions','rejected','next_steps') for item in draft[key])
    assert '不要收集游客位置' in draft['rejected'][0]['text']
    assert client.get('/api/bootstrap').json['capsules']==[]
    path,payload,authorization=state['requests'][0]
    assert path=='/v1/chat/completions' and authorization=='Bearer synthetic-key'
    assert '中文 📝' in payload['messages'][1]['content']
    assert 'synthetic-key' not in json.dumps(job)


@pytest.mark.parametrize('failure',['http','schema'])
def test_model_failure_does_not_fallback_or_save(tmp_path,provider,failure):
    url,state=provider
    if failure=='http':state['status']=500
    else:state['content']={'goal':'not a capsule'}
    app=create_app({'TESTING':True,'DATA_DIR':tmp_path,'MODEL_URL':url,'MODEL_NAME':'test','MODEL_KEY':'synthetic-key'})
    client,headers=authenticated(app)
    response=client.post('/api/extract',json={'conversation':'hello','title':'test'},headers=headers)
    assert response.status_code==202
    job=poll(client,response.json['task_id'])
    assert job['status']=='failed' and 'result' not in job
    assert client.get('/api/bootstrap').json['capsules']==[]
    assert 'synthetic-key' not in json.dumps(job)


def test_failed_atomic_replace_preserves_previous_saved_capsule(app,monkeypatch):
    client,headers=authenticated(app)
    assert client.post('/api/capsules',json=capsule(),headers=headers).status_code==200
    import brain_relay.storage as module
    def fail_replace(*args):raise OSError('synthetic disk failure')
    monkeypatch.setattr(module.os,'replace',fail_replace)
    changed=capsule();changed['goal']='must not persist'
    assert client.post('/api/capsules',json=changed,headers=headers).status_code==500
    assert client.get('/api/capsules/sample-1/export').json['goal']=='做一份双语地图\n可离线使用'
    assert not list(app.extensions['relay_store'].directory.glob('*.tmp'))


def test_provider_redirect_is_not_followed(tmp_path):
    hits=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            hits.append(self.path)
            self.send_response(307)
            self.send_header('Location',f'http://127.0.0.1:{self.server.server_port}/leak')
            self.end_headers()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        app=create_app({'TESTING':True,'DATA_DIR':tmp_path,'MODEL_URL':f'http://127.0.0.1:{server.server_port}/start','MODEL_NAME':'test','MODEL_KEY':'synthetic-key'})
        client,headers=authenticated(app)
        response=client.post('/api/extract',json={'conversation':'synthetic','title':'test'},headers=headers)
        job=poll(client,response.json['task_id'])
        assert job['status']=='failed' and hits==['/start']
    finally:
        server.shutdown();server.server_close();thread.join()


def test_corrupted_local_store_is_not_reset_on_save(app):
    path=app.extensions['relay_store'].path
    path.write_text('invalid JSON')
    client=app.test_client()
    response=client.get('/api/bootstrap')
    assert response.status_code==500
    assert path.read_text()=='invalid JSON'
