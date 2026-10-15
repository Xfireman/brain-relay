"""Optional real-browser acceptance. Run against a disposable local data directory."""
import json
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

base=os.environ.get('RELAY_BASE_URL','http://127.0.0.1:7332')
output=Path(os.environ['RELAY_BROWSER_OUTPUT']);output.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[1]
checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(viewport={'width':1440,'height':1080},locale='en-US',accept_downloads=True)
    page=context.new_page();errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('dialog',lambda dialog:dialog.accept())
    page.goto(base);expect(page.locator("#provider-status")).to_contain_text("No model")
    assert page.locator('#extract').is_disabled()
    page.locator('#example').click();expect(page.locator("#title")).to_have_value(re.compile("Neighborhood"))
    page.locator('#save').click();expect(page.locator("#save-feedback")).to_have_text("Saved locally")
    page.locator('#generate').click();expect(page.locator("#handoff-text")).to_have_value(re.compile("Rejected approaches"))
    expected=page.locator('#handoff-text').input_value()
    assert '不收集游客位置数据' in expected
    assert '不收集游客位置数据' not in expected.split('Next steps / 下一步')[1]
    with page.expect_download() as download:
        page.locator('#download-text').click()
    path=output/'handoff.txt';download.value.save_as(path)
    assert path.read_text()==expected
    checks.append('synthetic example → save → handoff download matches preview')
    page.locator('#budget').fill('20');page.locator('#generate').click()
    expect(page.locator("#handoff-error")).to_contain_text("Omitted")
    assert not page.locator('#handoff-text').input_value() and page.locator('#download-text').is_disabled()
    checks.append('budget failure reports omissions and disables partial download')
    page.locator('#budget').fill('');page.locator('#generate').click()
    expect(page.locator("#handoff-text")).to_have_value(re.compile("Brain Relay"))
    for theme in ('light','dark'):
        page.evaluate("theme=>{document.documentElement.dataset.theme=theme;localStorage.setItem('relay-theme',theme)}",theme)
        assert page.evaluate("getComputedStyle(document.body).getPropertyValue('--relay-text').trim()")
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(output/f'workspace-{theme}.png'),full_page=False)
    page.locator('#language').click()
    assert page.locator('h1').inner_text()=='换个窗口，继续做事。'
    page.set_viewport_size({'width':390,'height':844})
    for theme in ('light','dark'):
        page.evaluate("theme=>document.documentElement.dataset.theme=theme",theme)
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(path=str(output/f'mobile-{theme}.png'),full_page=True)
    checks.append('English/Chinese and both themes at desktop/mobile widths')
    page.set_viewport_size({'width':1440,'height':1080})
    payload=json.loads((root/'brain_relay/examples/park-map.json').read_text())
    payload['id']='browser-roundtrip'
    payload['title']='中文 📝\n多行任务'
    payload['context']='<img src=x onerror="window.hostileExecuted=true">\n第一行 📝\n第二行'
    payload['decisions'][0]['source']='第一条来源\n第二行 🧩'
    payload['sources'][0]['title']='来源一\n来源二'
    page.locator('#import').set_input_files({'name':'roundtrip.json','mimeType':'application/json','buffer':json.dumps(payload,ensure_ascii=False).encode()})
    expect(page.locator("#context")).to_have_value(re.compile("hostileExecuted"))
    assert page.locator('img').count()==0 and not page.evaluate('Boolean(window.hostileExecuted)')
    page.locator('#export').click();expect(page.locator("#export-text")).to_have_value(re.compile("schema_version"))
    exported=json.loads(page.locator('#export-text').input_value())
    assert exported==payload,(exported,payload)
    checks.append('hostile HTML remains literal and multiline fields round-trip through actual UI')
    page.locator('#save').click();expect(page.locator("#save-feedback")).to_have_text("已保存到本机")
    page.reload();expect(page.locator("#library option[value=browser-roundtrip]")).to_have_count(1)
    page.locator('#library').select_option('browser-roundtrip')
    assert page.locator('#context').input_value()==payload['context']
    page.locator('#candidates-list input[type=checkbox]').click()
    assert page.locator('#candidates-list textarea').count()==0
    page.locator('#save').click();expect(page.locator("#save-feedback")).to_have_text("已保存到本机")
    page.locator('#export').click();expect(page.locator("#export-text")).to_have_value(re.compile("schema_version"))
    with page.expect_download() as download:
        page.locator('#download-json').click()
    path=output/'capsule.json';download.value.save_as(path)
    after=json.loads(path.read_text());assert all(x['confirmed'] for x in after['decisions'])
    assert after['rejected'][0]['text']==payload['rejected'][0]['text']
    checks.append('reload persisted data → explicit confirmation → exact JSON download')
    page.goto(base+'/styleguide')
    assert page.locator('.theme-pane').count()==2
    assert not errors,errors
    checks.append('live styleguide and no JavaScript exceptions')
    browser.close()
(output/'browser-results.json').write_text(json.dumps({'checks':checks,'passed':len(checks),'errors':errors},ensure_ascii=False,indent=2))
print(json.dumps({'checks':checks,'passed':len(checks),'errors':errors},ensure_ascii=False))
