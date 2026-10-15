(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const timestamp=()=>new Date().toISOString();
  const fresh=()=>({schema_version:1,id:crypto.randomUUID(),title:'',goal:'',context:'',decisions:[],rejected:[],next_steps:[],sources:[],updated_at:timestamp(),origin:'manual'});
  let current=fresh(), saved=[], csrf='', dirty=false, configured=false, pendingImport=false, extracted=null, activeJob=null;
  let handoff='', exportText='';
  const messages={};
  function message(id,key,values){messages[id]={key,values};$(id).textContent=key?t(key,values):'';}
  function invalidate(){handoff='';exportText='';$('handoff-text').value='';$('export-text').value='';$('copy').disabled=true;$('download-text').disabled=true;$('download-json').disabled=true;message('handoff-count','');}
  function changed(){dirty=true;current.updated_at=timestamp();$('updated').textContent=current.updated_at;message('save-state','unsaved');message('save-feedback','');invalidate();}
  function errorMessage(error){
    if(error.code==='model_not_configured')return t('modelUnavailable');
    if(error.code==='storage_error')return t('storageError');
    if(['csrf','cross_site','invalid_request'].includes(error.code))return t('invalidRequest');
    return error.code==='validation'?t('validation')+' '+error.message:error.message||t('network');
  }
  async function api(path,body){
    const options=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)};
    let response;
    try{response=await fetch(path,{...options,credentials:'same-origin'});}catch(e){throw new Error(t('network'));}
    let data;try{data=await response.json();}catch(e){throw new Error(t('network'));}
    if(!response.ok){const error=new Error(data.error||t('network'));Object.assign(error,data);throw error;}
    return data;
  }
  async function busy(button,fn){
    if(button.disabled)return;
    button.disabled=true;const label=button.textContent;button.textContent=t('busy');
    try{await fn();}finally{button.disabled=false;button.textContent=label;}
  }
  function collect(){['title','goal','context'].forEach(key=>{current[key]=$(key).value;});return structuredClone(current);}
  function ready(){
    collect();let valid=true;
    ['title','goal'].forEach(key=>{const bad=!current[key].trim();$(key).setAttribute('aria-invalid',String(bad));if(bad)valid=false;});
    message('form-error',valid?'':'required');return valid;
  }
  function canReplace(){return !dirty||window.confirm(t('discard'));}
  function renderLibrary(){
    $('library').replaceChildren();
    const first=document.createElement('option');first.value='';first.textContent=t('emptyLibrary');$('library').append(first);
    saved.forEach(c=>{const option=document.createElement('option');option.value=c.id;option.textContent=c.title;$('library').append(option);});
    $('library').value=saved.some(c=>c.id===current.id)?current.id:'';
  }
  function addField(parent,label,value,onInput,multiline=false){
    const id='field-'+crypto.randomUUID();const caption=document.createElement('label');caption.htmlFor=id;caption.textContent=t(label);
    const field=document.createElement(multiline?'textarea':'input');field.id=id;field.className='relay-input';field.value=value;
    if(multiline)field.rows=2;
    field.maxLength=label==='source'?2000:label==='sourceTitle'?200:20000;
    field.addEventListener('input',()=>{onInput(field.value);changed();});parent.append(caption,field);return field;
  }
  function renderLists(){
    ['confirmed','candidates','rejected','next_steps','sources'].forEach(group=>{
      const target=$(group+'-list');target.replaceChildren();
      const key=['confirmed','candidates'].includes(group)?'decisions':group;
      const indices=current[key].map((_,index)=>index).filter(index=>group==='confirmed'?current[key][index].confirmed:group==='candidates'?!current[key][index].confirmed:true);
      if(!indices.length){const empty=document.createElement('p');empty.className='relay-empty';empty.textContent=t('emptyItems');target.append(empty);return;}
      indices.forEach(index=>{
        const item=current[key][index],row=document.createElement('div');row.className='item';
        if(key==='sources'){
          addField(row,'sourceTitle',item.title,v=>{item.title=v;},true);
          addField(row,'reference',item.reference,v=>{item.reference=v;},true);
        }else{
          addField(row,'itemText',item.text,v=>{item.text=v;},true);
          addField(row,'source',item.source,v=>{item.source=v;},true);
        }
        const time=document.createElement('p');time.className='relay-muted relay-mono';time.textContent=t('recorded')+' · '+item.recorded_at;row.append(time);
        const bottom=document.createElement('div');bottom.className='item-bottom';
        if(key!=='sources'){
          const check=document.createElement('label');check.className='check';const input=document.createElement('input');input.type='checkbox';input.checked=item.confirmed;
          const text=document.createElement('span');text.textContent=t('checked');check.append(input,text);
          input.addEventListener('change',()=>{item.confirmed=input.checked;changed();renderLists();if(key==='decisions')$(item.confirmed?'confirmed-list':'candidates-list').querySelector('textarea')?.focus();});bottom.append(check);
        }
        const remove=document.createElement('button');remove.type='button';remove.className='relay-btn ghost small danger';remove.textContent=t('remove');
        remove.addEventListener('click',()=>{if(window.confirm(t('removeConfirm'))){current[key].splice(index,1);changed();renderLists();}});bottom.append(remove);row.append(bottom);target.append(row);
      });
    });
  }
  function render(){
    ['title','goal','context'].forEach(key=>{$(key).value=current[key];$(key).removeAttribute('aria-invalid');});
    $('updated').textContent=current.updated_at;
    message('origin',current.origin==='demo'?'demoOrigin':current.origin==='configured provider'?'modelOrigin':'manualOrigin');
    message('save-state',dirty?'unsaved':saved.some(c=>c.id===current.id)?'saved':'notSaved');
    message('provider-status',configured?'hasModel':'noModel');$('extract').disabled=!configured;
    renderLists();renderLibrary();
  }
  function load(c,unsaved=true){current=structuredClone(c);dirty=unsaved;pendingImport=false;invalidate();message('form-error','');render();}
  function download(text,name,type){const url=URL.createObjectURL(new Blob([text],{type}));const link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  ['title','goal','context'].forEach(key=>{$(key).addEventListener('input',()=>{current[key]=$(key).value;changed();});});
  $('budget').addEventListener('input',invalidate);
  document.querySelectorAll('[data-add]').forEach(button=>{button.addEventListener('click',()=>{
    const group=button.dataset.add;const key=['confirmed','candidates'].includes(group)?'decisions':group;
    current[key].push(key==='sources'?{title:'',reference:'',recorded_at:timestamp()}:{text:'',source:'',confirmed:group==='confirmed',recorded_at:timestamp()});changed();renderLists();const fields=$(group+'-list').querySelectorAll('textarea,input');fields[fields.length-(key==='sources'?2:3)]?.focus();
  });});
  $('library').addEventListener('change',()=>{const selected=saved.find(c=>c.id===$('library').value);if(selected&&canReplace())load(selected,false);else renderLibrary();});
  $('new').addEventListener('click',()=>{if(canReplace()){load(fresh(),false);message('save-feedback','newReady');$('title').focus();}});
  $('example').addEventListener('click',()=>busy($('example'),async()=>{if(!canReplace())return;try{const demo=await api('/api/example');demo.id=crypto.randomUUID();load(demo);message('save-feedback','exampleReady');}catch(e){$('form-error').textContent=errorMessage(e);}}));
  $('import').addEventListener('change',async()=>{
    const file=$('import').files[0];$('import').value='';if(!file||!canReplace())return;
    try{if(file.size>500000)throw new Error(t('fileTooLarge'));const data=JSON.parse(await file.text());await api('/api/handoff',{capsule:data,max_chars:null});load(data);pendingImport=true;message('save-feedback','importReady');}catch(e){$('form-error').textContent=e.code?errorMessage(e):t('importError')+' '+e.message;}
  });
  $('capsule-form').addEventListener('submit',event=>{event.preventDefault();busy($('save'),async()=>{
    if(!ready())return;if(pendingImport&&saved.some(c=>c.id===current.id)&&!window.confirm(t('overwrite')))return;
    try{const result=await api(pendingImport?'/api/import':'/api/capsules',collect());saved=[result,...saved.filter(c=>c.id!==result.id)];current=result;dirty=false;pendingImport=false;renderLibrary();message('save-state','saved');message('save-feedback','saved');}catch(e){$('form-error').textContent=errorMessage(e);}
  });});
  $('generate').addEventListener('click',()=>busy($('generate'),async()=>{
    if(!ready())return;const raw=$('budget').value;const budget=raw===''?null:Number(raw);
    if(budget!==null&&(!Number.isInteger(budget)||budget<1||budget>1000000)){message('handoff-error','invalidBudget');$('budget').setAttribute('aria-invalid','true');return;}
    $('budget').removeAttribute('aria-invalid');message('handoff-error','');
    try{const result=await api('/api/handoff',{capsule:collect(),max_chars:budget});handoff=result.text;$('handoff-text').value=handoff;$('handoff-count').textContent=result.chars+' '+t('savedCount');$('copy').disabled=false;$('download-text').disabled=false;}
    catch(e){invalidate();if(e.code==='budget_too_small'){message('handoff-error','budgetError',{required:e.required_chars,budget:e.max_chars,...e.omitted});}else $('handoff-error').textContent=errorMessage(e);}
  }));
  $('copy').addEventListener('click',()=>busy($('copy'),async()=>{try{await navigator.clipboard.writeText(handoff);message('handoff-count','copied');}catch(e){message('handoff-error','copyFail');$('handoff-text').focus();$('handoff-text').select();}}));
  $('download-text').addEventListener('click',()=>download(handoff,'brain-relay-handoff.txt','text/plain;charset=utf-8'));
  $('export').addEventListener('click',()=>busy($('export'),async()=>{
    if(!ready())return;try{const value=collect();await api('/api/handoff',{capsule:value,max_chars:null});exportText=JSON.stringify(value,null,2)+'\n';$('export-text').value=exportText;$('export-panel').open=true;$('download-json').disabled=false;message('handoff-error','');}catch(e){$('handoff-error').textContent=errorMessage(e);}
  }));
  $('download-json').addEventListener('click',()=>download(exportText,'brain-relay-capsule.json','application/json;charset=utf-8'));
  async function poll(){
    for(let count=0;count<90;count++){
      const job=await api('/api/jobs/'+activeJob);
      if(job.status==='succeeded'){extracted=job.result;activeJob=null;message('model-state','jobReady');$('load-draft').hidden=false;return;}
      if(job.status==='failed'){activeJob=null;throw new Error(t('jobFailed'));}
      message('model-state',job.status==='queued'?'jobQueued':'jobRunning');await new Promise(resolve=>setTimeout(resolve,1000));
    }
    message('model-state','jobTimeout');
  }
  $('extract').addEventListener('click',()=>busy($('extract'),async()=>{
    message('model-error','');
    try{if(!activeJob){if(!$('conversation').value.trim()||!$('title').value.trim()){message('model-error','extractRequired');return;}extracted=null;$('load-draft').hidden=true;const result=await api('/api/extract',{conversation:$('conversation').value,title:$('title').value});activeJob=result.task_id;}await poll();}
    catch(e){$('model-error').textContent=errorMessage(e);}
    finally{setTimeout(()=>message('extract',activeJob?'checkStatus':'extractAction'),0);}
  }));
  $('load-draft').addEventListener('click',()=>{if(extracted&&canReplace()){load(extracted);$('load-draft').hidden=true;message('save-feedback','draftApplied');$('title').focus();}});
  document.addEventListener('relay-language',()=>{collect();render();Object.entries(messages).forEach(([id,state])=>{$(id).textContent=state.key?t(state.key,state.values):'';});if(activeJob)message('extract','checkStatus');});
  window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
  render();
  api('/api/bootstrap').then(data=>{csrf=data.csrf_token;saved=data.capsules;configured=data.model_configured;render();}).catch(e=>{$('form-error').textContent=errorMessage(e);});
})();
