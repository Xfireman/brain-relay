(() => {
  'use strict';
  translate();
  document.getElementById('theme').addEventListener('click',()=>{
    const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';
    document.documentElement.dataset.theme=theme;
    try{localStorage.setItem('relay-theme',theme);}catch(e){}
  });
  document.getElementById('language').addEventListener('click',()=>{
    const language=document.documentElement.lang==='zh'?'en':'zh';
    document.documentElement.lang=language;
    try{localStorage.setItem('relay-lang',language);}catch(e){}
    translate();
    document.dispatchEvent(new Event('relay-language'));
  });
})();
