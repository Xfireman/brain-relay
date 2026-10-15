"""Browser state regressions. CI installs the browser extra and Chromium explicitly."""
import json
import re
from threading import Thread
import pytest
from werkzeug.serving import make_server
from brain_relay.app import create_app

playwright = pytest.importorskip('playwright.sync_api', reason='Install .[browser] and Chromium for UI regressions')
expect = playwright.expect


@pytest.fixture(scope='module')
def browser():
    with playwright.sync_playwright() as runner:
        instance = runner.chromium.launch(headless=True)
        yield instance
        instance.close()


@pytest.fixture
def workspace(tmp_path, browser):
    app = create_app({'DATA_DIR':tmp_path, 'MODEL_URL':'', 'MODEL_NAME':'', 'MODEL_KEY':''})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    context = browser.new_context(locale='en-US')
    page = context.new_page()
    page.on('dialog', lambda dialog: dialog.accept())
    base = f'http://127.0.0.1:{server.server_port}'
    page.goto(base)
    expect(page.locator('#provider-status')).to_contain_text('No model')
    page.locator('#example').click()
    expect(page.locator('#title')).to_have_value(re.compile('Neighborhood'))
    yield page, base
    context.close()
    server.shutdown()
    server.server_close()
    thread.join()
    app.extensions['relay_jobs'].pool.shutdown(wait=True)


def save(page):
    page.locator('#save').click()
    expect(page.locator('#save')).to_have_text('Save capsule locally')


def preview_export(page):
    page.locator('#export').click()
    expect(page.locator('#export-text')).to_have_value(re.compile('schema_version'))
    return json.loads(page.locator('#export-text').input_value())


def mutate(page, kind):
    if kind == 'edit':
        page.locator('#goal').fill('NEWER edits 中文 🌿')
    elif kind == 'switch':
        page.locator('#new').click()
        page.locator('#title').fill('A different capsule')
        page.locator('#goal').fill('A different goal')
    elif kind == 'budget':
        page.locator('#budget').fill('1')


def delay_real_response(page, path, action):
    def intercept(route):
        response = route.fetch()
        action()
        route.fulfill(response=response)
    page.route('**'+path, intercept)
    return intercept


def test_save_then_edit_every_nested_section_and_confirm_persists(workspace):
    page, base = workspace
    save(page)
    expected = {}
    for group in ('confirmed', 'candidates', 'rejected', 'next_steps', 'sources'):
        fields = page.locator(f'#{group}-list textarea')
        expected[group] = (f'UPDATED {group} 中文 🌿\nsecond line', f'SOURCE {group}\n📝')
        fields.nth(0).fill(expected[group][0])
        fields.nth(1).fill(expected[group][1])
    exported = preview_export(page)
    for group, key, index in [('confirmed','decisions',0), ('candidates','decisions',1), ('rejected','rejected',0), ('next_steps','next_steps',0)]:
        assert exported[key][index]['text'] == expected[group][0]
        assert exported[key][index]['source'] == expected[group][1]
    assert exported['sources'][0]['title'] == expected['sources'][0]
    assert exported['sources'][0]['reference'] == expected['sources'][1]
    page.locator('#candidates-list input[type=checkbox]').click()
    expect(page.locator('#candidates-list input[type=checkbox]')).to_have_count(0)
    page.locator('#rejected-list input[type=checkbox]').click()
    page.locator('#next_steps-list input[type=checkbox]').click()
    save(page)
    stored = page.request.get(base+'/api/capsules/'+exported['id']+'/export').json()
    assert stored['decisions'][1]['confirmed'] is True
    assert stored['rejected'][0]['confirmed'] is False
    assert stored['next_steps'][0]['confirmed'] is True
    for field in ('decisions','rejected','next_steps','sources'):
        assert [(x.get('text',x.get('title')),x.get('source',x.get('reference'))) for x in stored[field]] == [(x.get('text',x.get('title')),x.get('source',x.get('reference'))) for x in exported[field]]
    page.reload()
    expect(page.locator(f'#library option[value="{stored["id"]}"]')).to_have_count(1)
    page.locator('#library').select_option(stored['id'])
    assert preview_export(page) == stored


def test_save_response_cannot_clear_newer_edits(workspace):
    page, base = workspace
    old_goal = page.locator('#goal').input_value()
    handler = delay_real_response(page, '/api/capsules', lambda: mutate(page,'edit'))
    save(page)
    page.unroute('**/api/capsules',handler)
    assert page.locator('#goal').input_value() == 'NEWER edits 中文 🌿'
    expect(page.locator('#save-state')).to_have_text('Unsaved changes')
    saved = page.request.get(base+'/api/bootstrap').json()['capsules'][0]
    assert saved['goal'] == old_goal
    save(page)
    assert page.request.get(base+'/api/capsules/'+saved['id']+'/export').json()['goal'] == 'NEWER edits 中文 🌿'


def test_save_response_cannot_replace_different_active_capsule(workspace):
    page, base = workspace
    handler = delay_real_response(page, '/api/capsules', lambda: mutate(page,'switch'))
    save(page)
    page.unroute('**/api/capsules',handler)
    expect(page.locator('#save-state')).to_have_text('Unsaved changes')
    exported = preview_export(page)
    assert exported['title'] == 'A different capsule'
    assert exported['id'] != page.request.get(base+'/api/bootstrap').json()['capsules'][0]['id']


@pytest.mark.parametrize('operation,download,preview', [('generate','download-text','handoff-text'), ('export','download-json','export-text')])
@pytest.mark.parametrize('change', ['edit','switch','budget'])
def test_old_preview_response_cannot_restore_download_after_change(workspace, operation, download, preview, change):
    page, _ = workspace
    handler = delay_real_response(page, '/api/handoff', lambda: mutate(page,change))
    page.locator('#'+operation).click()
    expect(page.locator('#'+operation)).to_be_enabled()
    page.unroute('**/api/handoff',handler)
    assert page.locator('#'+preview).input_value() == ''
    assert page.locator('#'+download).is_disabled()


def test_old_budget_error_does_not_report_failure_for_new_budget(workspace):
    page, _ = workspace
    page.locator('#budget').fill('1')
    delay_real_response(page, '/api/handoff', lambda: page.locator('#budget').fill(''))
    page.locator('#generate').click()
    expect(page.locator('#generate')).to_be_enabled()
    assert page.locator('#handoff-error').inner_text() == ''


@pytest.mark.parametrize('loader',['example','import'])
def test_delayed_load_does_not_replace_newer_edits(workspace,loader):
    page,base = workspace
    path = '/api/example' if loader == 'example' else '/api/handoff'
    handler = delay_real_response(page,path,lambda: mutate(page,'edit'))
    if loader == 'example':
        page.locator('#example').click()
        expect(page.locator('#example')).to_be_enabled()
    else:
        sample = page.request.get(base+'/api/example').json()
        with page.expect_response(lambda response:response.url.endswith('/api/handoff')):
            page.locator('#import').set_input_files({'name':'capsule.json','mimeType':'application/json','buffer':json.dumps(sample).encode()})
        # The response has finished; wait for its fetch continuation without mutating the editor.
        page.wait_for_load_state('networkidle')
    page.unroute('**'+path,handler)
    assert page.locator('#goal').input_value() == 'NEWER edits 中文 🌿'


def test_copy_completion_cannot_reenable_invalidated_output(workspace):
    page, _ = workspace
    page.locator('#generate').click()
    expect(page.locator('#copy')).to_be_enabled()
    # Delay only the browser clipboard boundary; the real UI state handler still runs.
    page.evaluate('() => { navigator.clipboard.writeText = () => new Promise(resolve => { window.finishCopy = resolve; }); }')
    page.locator('#copy').click()
    expect(page.locator('#copy')).to_be_disabled()
    mutate(page,'edit')
    page.evaluate('window.finishCopy()')
    expect(page.locator('#copy')).to_have_text('Copy')
    assert page.locator('#copy').is_disabled()
    assert page.locator('#handoff-count').inner_text() == ''
