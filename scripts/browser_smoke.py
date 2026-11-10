import json,time,os,httpx
import sys
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
    print('Playwright not installed, skipping E2E browser smoke test.', file=sys.stderr)
    sys.exit(0)
from pathlib import Path
from playwright.sync_api import sync_playwright
Path('work').mkdir(exist_ok=True)
for attempt in range(30):
 try:
  if httpx.get('http://127.0.0.1:8000/api/health').status_code==200:break
 except httpx.ConnectError:pass
 time.sleep(1)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.getenv('BROWSER_EXECUTABLE','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1512,'height':1100},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8000',wait_until='networkidle')
 page.get_by_text('The city\'s heat landscape').wait_for()
 page.wait_for_timeout(1800)
 page.screenshot(path='work/overview-desktop.png',full_page=True)
 assert page.locator('.leaflet-interactive').count()==324
 for name in ['AI prediction','Explainable AI','Heat risk']:
  page.get_by_role('navigation').get_by_role('button',name=name,exact=True).click()
  page.wait_for_timeout(700)
 page.get_by_role('button',name='Recalculate priorities').click()
 page.get_by_text('Recalculated framework',exact=False).wait_for()
 page.get_by_role('navigation').get_by_role('button',name='Intervention simulator',exact=True).click()
 page.get_by_role('button',name='Run & save scenario').click()
 page.get_by_text('Feasible under supplied constraints').wait_for()
 page.screenshot(path='work/simulator-desktop.png',full_page=True)
 page.get_by_role('navigation').get_by_role('button',name='Optimization',exact=True).click()
 page.get_by_role('button',name='Optimize interventions',exact=True).click()
 page.get_by_text('Mean hypothetical cooling',exact=True).wait_for(timeout=30000)
 page.get_by_role('navigation').get_by_role('button',name='AI assistant',exact=True).click()
 page.get_by_label('AI provider').select_option('local')
 page.get_by_role('button',name='Why is this area hotter?').click()
 page.get_by_text('Template fallback',exact=True).wait_for()
 page.get_by_role('navigation').get_by_role('button',name='Reports',exact=True).click()
 page.get_by_role('button',name='Generate analysis report').click()
 page.get_by_role('button',name='Download CSV').wait_for()
 with page.expect_download() as info:page.get_by_role('button',name='Download CSV').click()
 d=info.value;d.save_as('work/browser-export.csv');assert Path('work/browser-export.csv').stat().st_size>1000
 page.get_by_label('City',exact=True).select_option('Delhi')
 page.get_by_role('navigation').get_by_role('button',name='Overview',exact=True).click()
 page.get_by_text('The city\'s heat landscape').wait_for(timeout=30000)
 assert page.locator('.map-badge').inner_text().startswith('Delhi')
 page.get_by_label('City',exact=True).select_option('Ahmedabad')
 page.get_by_text('The city\'s heat landscape').wait_for()
 if page.get_by_label('Dismiss notification').count():page.get_by_label('Dismiss notification').click()
 page.set_viewport_size({'width':390,'height':844})
 page.wait_for_timeout(700)
 page.screenshot(path='work/overview-mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
 page.get_by_label('Open navigation').click()
 page.get_by_role('navigation').get_by_role('button',name='Heat map',exact=True).click()
 assert not page.locator('.sidebar').evaluate("el=>el.classList.contains('open')")
 assert not errors,errors
 print(json.dumps({'status':'PASS','workflows':['overview map 324 interactive cells','prediction charts','SHAP','risk weights','saved simulation','constrained optimization','local evidence assistant','report CSV download','city switch','mobile navigation and no horizontal overflow'],'console_errors':errors}))
 browser.close()
