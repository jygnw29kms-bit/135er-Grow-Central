/* Grow Central GUI writes use the authenticated HttpOnly session.
   API tokens remain available for non-browser clients through app.security. */
writeApi=async function(url,options={}){
  const headers=new Headers(options.headers||{});
  headers.set('Content-Type','application/json');
  return api(url,{...options,headers});
};

/* Runtime hardening for iPhone/iPad and live cloud-link visibility. */
(() => {
  if (!document.querySelector('link[data-gc-mobile-runtime]')) {
    const link=document.createElement('link');
    link.rel='stylesheet';
    link.href='/static/mobile_runtime_fix.css?v=1';
    link.dataset.gcMobileRuntime='1';
    document.head.appendChild(link);
  }
  if (!document.querySelector('script[data-gc-mobile-runtime]')) {
    const script=document.createElement('script');
    script.src='/static/mobile_runtime_fix.js?v=1';
    script.defer=true;
    script.dataset.gcMobileRuntime='1';
    document.body.appendChild(script);
  }
})();
