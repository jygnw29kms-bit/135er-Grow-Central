/* Grow Central GUI writes use the authenticated HttpOnly session.
   API tokens remain available for non-browser clients through app.security. */
writeApi=async function(url,options={}){
  const headers=new Headers(options.headers||{});
  headers.set('Content-Type','application/json');
  return api(url,{...options,headers});
};
