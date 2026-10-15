"""Optional model UI acceptance using a local fake HTTP provider, never a paid model."""
import json
import os
from pathlib import Path
import sys
from threading import Thread
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from brain_relay.app import create_app

output=Path(os.environ['RELAY_BROWSER_OUTPUT']);output.mkdir(parents=True,exist_ok=True)
state={'status':200,'requests':[]}
example=json.loads((root/'brain_relay/examples/park-map.json').read_text())
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  state['requests'].append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
  self.send_response(state['status']);self.send_header('Content-Type','application/json');self.end_headers()
  self.wfile.write(json.dumps({'choices':[{'message':{'content':json.dumps(example,ensure_ascii=False)}}]}).encode())
 def log_message(self,*args):pass
provider=ThreadingHTTPServer(('127.0.0.1',0),Handler)
provider_thread=Thread(target=provider.serve_forever,daemon=True);provider_thread.start()
app=create_app({'DATA_DIR':output/'model-data','MODEL_URL':f'http://127.0.0.1:{provider.server_port}/v1/chat/completions','MODEL_NAME':'synthetic-http-fixture','MODEL_KEY':'synthetic-not-a-secret'})
server=make_server('127.0.0.1',0,app,threaded=True)
thread=Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True);page=browser.new_page(locale='en-US');page.on('dialog',lambda dialog:dialog.accept())
  page.goto(f'http://127.0.0.1:{server.server_port}')
  expect(page.locator('#provider-status')).to_contain_text('Configured provider')
  page.locator('#title').fill('Synthetic model extraction')
  page.locator('#conversation').fill('Plan a bilingual map. Do not track visitors.\n中文对话 📝')
  with page.expect_response(lambda r:r.url.endswith('/api/extract')) as response:
   page.locator('#extract').click()
  assert response.value.status==202 and response.value.json()['task_id']
  expect(page.locator('#load-draft')).to_be_visible(timeout=15000)
  assert page.request.get(f'http://127.0.0.1:{server.server_port}/api/bootstrap').json()['capsules']==[]
  page.locator('#load-draft').click()
  assert page.locator('#confirmed-list textarea').count()==0
  assert page.locator('#candidates-list input[type=checkbox]').count()==2
  assert page.locator('#candidates-list input[type=checkbox]:checked').count()==0
  assert 'Do not collect visitor' in page.locator('#rejected-list textarea').first.input_value()
  before=page.locator('#title').input_value()
  state['status']=500
  page.locator('#conversation').fill('A second synthetic extraction must fail')
  page.locator('#extract').click()
  expect(page.locator('#model-error')).to_contain_text('failed',timeout=15000)
  assert page.locator('#load-draft').is_hidden()
  assert page.locator('#title').input_value()==before
  assert not page.request.get(f'http://127.0.0.1:{server.server_port}/api/bootstrap').json()['capsules']
  assert 'synthetic-not-a-secret' not in page.content()
  assert '中文对话 📝' in state['requests'][0]['messages'][1]['content']
  assert len(state['requests'])==2
  browser.close()
 result={'passed':2,'checks':['UI extraction returns 202, polls real HTTP provider and loads only unconfirmed draft','provider 500 produces visible failure without fallback or persistent capsule']}
 (output/'model-browser-results.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result))
finally:
 server.shutdown();server.server_close();thread.join()
 provider.shutdown();provider.server_close();provider_thread.join()
 app.extensions['relay_jobs'].pool.shutdown(wait=True)
