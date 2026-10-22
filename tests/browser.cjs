const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const output=path.resolve('reports/browser');fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.VG_BROWSER_PATH||undefined,headless:true,args:['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream',`--use-file-for-fake-audio-capture=${path.resolve('sampleA_short.wav')}`]});
 const context=await browser.newContext({acceptDownloads:true,permissions:['microphone']});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('console',msg=>{if(msg.type()==='error')errors.push(msg.text());});
 await page.goto(process.env.VG_BASE_URL||'http://127.0.0.1:8000');await page.waitForFunction(()=>document.getElementById('health').textContent==='Detector ready');
 await page.evaluate(()=>document.fonts.ready);
 for(const width of [320,390,768,1280]){
  await page.setViewportSize({width,height:900});
  await page.waitForFunction(()=>parseFloat(getComputedStyle(document.body).paddingTop)>=document.querySelector('.navbar').getBoundingClientRect().height);
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth||document.querySelector('.dashboard').getBoundingClientRect().top<document.querySelector('.navbar').getBoundingClientRect().bottom))throw Error('Header overlap or narrow-screen overflow');
 }
 if(!(await page.evaluate(()=>document.fonts.check('16px VoiceGuard')&&document.querySelector('.logo-image').currentSrc.endsWith('new-end.webp')&&parseFloat(getComputedStyle(document.querySelector('.logo-text small')).fontSize)>=12)))throw Error('Optimized assets or readable tagline missing');
 for(let i=0;i<20;i++){await page.keyboard.press('Tab');if(await page.evaluate(()=>document.activeElement.id==='file'))break;}
 if(!(await page.evaluate(()=>document.activeElement.id==='file'&&getComputedStyle(document.activeElement).outlineStyle==='solid')))throw Error('File input must be keyboard reachable with visible focus');
 await page.locator('#file').scrollIntoViewIfNeeded();
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const chooserPromise=page.waitForEvent('filechooser');await page.keyboard.press('Enter');await(await chooserPromise).setFiles(path.resolve('sampleA_short.wav'));
 await page.emulateMedia({reducedMotion:'reduce'});await page.locator('.logo').hover();
 if(!(await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior==='auto'&&getComputedStyle(document.querySelector('.logo')).transitionDuration==='0s'&&getComputedStyle(document.querySelector('.logo')).transform==='none'&&document.querySelector('.verdict-card').getAttribute('aria-live')==='polite'&&document.querySelector('.verdict-card').getAttribute('aria-atomic')==='true')))throw Error('Reduced motion or result announcements missing');
 await page.emulateMedia({reducedMotion:'no-preference'});
 await page.evaluate(require('fs').readFileSync(require.resolve('axe-core'),'utf8'));
 const axe=await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}));
 console.log('Axe violations',axe.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)})));
 const originalFooterTargets=new Set(['.footer-policy > span:nth-child(1)','.footer-policy > span:nth-child(3)','.footer-copyright']);
 function unexpectedFindings(violations){return violations.flatMap(v=>v.nodes.filter(n=>!(v.id==='color-contrast'&&originalFooterTargets.has(n.target.join(' ')))));}
 if(unexpectedFindings(axe.violations).length)throw Error('New accessibility violations');
 console.log('Preserved original footer contrast findings:',axe.violations.reduce((count,v)=>count+v.nodes.length,0));
 const optionLayout=await page.evaluate(()=>{const consent=document.getElementById('consent').closest('label'),explain=document.getElementById('explain').closest('label'),options=consent.parentElement;return options.classList.contains('analysis-options')&&explain.parentElement===options&&options.nextElementSibling.id==='analyze'&&consent.getBoundingClientRect().bottom<=explain.getBoundingClientRect().top;});
 if(!optionLayout)throw Error('Checkboxes must be stacked directly above Analyze');
 await page.getByLabel('I have permission and consent to processing this recording.').check();
 await page.locator('#file').setInputFiles(path.resolve('sampleA_short.wav'));
 await page.waitForFunction(()=>!document.getElementById('analyze').disabled);
 await page.locator('#analyze').click();await page.waitForFunction(()=>document.getElementById('status').textContent==='Analysis complete.',{timeout:120000});
 if(await page.locator('#scoreGauge').count()!==1||await page.locator('#score').count()!==1||await page.locator('#models').count()!==0)throw Error('Keep the circular score and remove only model-name scores');
 if(await page.locator('#segments tr').count()!==3)throw Error('Expected three windows');
 const downloadPromise=page.waitForEvent('download');await page.locator('#download').click();const download=await downloadPromise;
 const file=await download.path();const data=JSON.parse(fs.readFileSync(file,'utf8'));if(!data.sha256||data.prediction!=='inconclusive')throw Error('Bad calibration report');
 const predicted=data.scores.fake>data.scores.real?'fake':'real';
 if(data.model_prediction!==predicted)throw Error('Missing raw model prediction');
 if(await page.locator('#score').textContent()!==`${data.scores[predicted].toFixed(2)}%`)throw Error('Circle must show the predicted class confidence');
 if(await page.locator('#reason').textContent()!==`The model classified this audio as ${predicted}. ${predicted==='fake'?'Fake':'Real'}-class score: ${data.scores[predicted].toFixed(2)}%.`)throw Error('Result wording must match the original style');
 if(await page.locator('[data-i18n=aiConfidence]').textContent()!=='AI CONFIDENCE')throw Error('Incorrect circle wording');
 if(await page.locator('#verdict').textContent()!==(predicted==='fake'?'FAKE AUDIO DETECTED':'REAL AUDIO DETECTED'))throw Error('Model prediction heading does not match scores');
 // Software fixtures: calibrated abstention must override the raw higher class.
 for(const [decision,expectedColor] of [['real','rgb(53, 223, 145)'],['fake','rgb(255, 69, 79)'],['inconclusive','rgb(255, 165, 0)']]){
  await page.evaluate(({data,decision})=>render({...data,calibrated:true,prediction:decision,disagreement:false,decision_reason:'calibrated_thresholds'}),{data,decision});
  const shown=await page.locator('#results').getAttribute('data-prediction');
  if(shown!==decision||await page.locator('#verdict').evaluate(el=>getComputedStyle(el).color)!==expectedColor)throw Error('Calibrated decision/color was overridden by raw scores');
 }
 await page.evaluate(data=>render({...data,calibrated:false,disagreement:true,decision_reason:'model_disagreement'}),data);
 if(await page.locator('#results').getAttribute('data-prediction')!=='inconclusive')throw Error('Ensemble disagreement must abstain');
 await page.evaluate(data=>render(data),data);
 await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
 await page.locator('#language').click();if(await page.locator('#analysis').getAttribute('dir')!=='rtl')throw Error('RTL failed');
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'mobile-arabic.png'),fullPage:true});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile horizontal overflow');
 const arAxe=await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}));
 console.log('Arabic axe violations',arAxe.violations.map(v=>v.id));
 if(unexpectedFindings(arAxe.violations).length||errors.length)throw Error(JSON.stringify({errors,violations:arAxe.violations.map(v=>v.id)}));
 await page.locator('#record').click();await page.waitForFunction(()=>!document.getElementById('stop').disabled);
 await page.waitForTimeout(1200);await page.locator('#stop').click();await page.waitForFunction(()=>!document.getElementById('analyze').disabled);
 if(!(await page.locator('#selected').textContent()).includes('microphone.'))throw Error('Microphone recording selection failed');
 await page.locator('#analyze').click();await page.waitForFunction(()=>document.getElementById('status').textContent==='اكتمل التحليل.',{timeout:120000});
 const base64=fs.readFileSync(path.resolve('sampleA_short.wav')).toString('base64');
 await page.evaluate(data=>{const transfer=new DataTransfer();transfer.items.add(new File([Uint8Array.from(atob(data),c=>c.charCodeAt(0))],'dropped.wav',{type:'audio/wav'}));document.getElementById('drop').dispatchEvent(new DragEvent('drop',{dataTransfer:transfer,bubbles:true,cancelable:true}));},base64);
 await page.waitForFunction(()=>document.getElementById('selected').textContent.includes('dropped.wav'));
 await page.locator('#language').click();
 await page.evaluate(()=>{const samples=48000,buffer=new ArrayBuffer(44+samples*2),view=new DataView(buffer);const text=(offset,value)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};text(0,'RIFF');view.setUint32(4,36+samples*2,true);text(8,'WAVE');text(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,samples*2,true);const transfer=new DataTransfer();transfer.items.add(new File([buffer],'silence.wav',{type:'audio/wav'}));document.getElementById('file').files=transfer.files;document.getElementById('file').dispatchEvent(new Event('change',{bubbles:true}));});
 await page.waitForFunction(()=>!document.getElementById('analyze').disabled);await page.locator('#analyze').click();
 await page.waitForFunction(()=>document.getElementById('verdict').textContent==='NO SPEECH DETECTED');
 if(await page.locator('#score').textContent()!=='--%'||await page.locator('#reportDetails').isVisible())throw Error('No-speech input must not display a score or old analysis');
 await page.locator('#language').click();if(await page.locator('#verdict').textContent()!=='لم يتم اكتشاف كلام')throw Error('No-speech translation missing');
 console.log('Browser upload, result, report, RTL/mobile, voiced microphone, drop and no-speech feedback checks passed; original footer contrast findings retained');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
