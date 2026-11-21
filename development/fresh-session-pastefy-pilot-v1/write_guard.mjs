// Registered last, before navigation: every non-read request is aborted.
// Never call fetch/fulfill/continue for writes, including unexpected origins.
export async function installWriteGuard(context, records) {
  await context.route('**/*', async route => {
    const request=route.request();
    if (['GET','HEAD','OPTIONS'].includes(request.method())) return route.fallback();
    const url=new URL(request.url());
    records.push({method:request.method(),origin:url.origin,path:url.pathname,
      request:request.postData(),disposition:'aborted_before_forwarding'});
    await route.abort('blockedbyclient');
  });
}
