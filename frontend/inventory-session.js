(() => {
 const originalFetch=window.fetch.bind(window);
 const session=originalFetch('/api/auth/me',{credentials:'same-origin'}).then(async r=>{if(!r.ok){location.replace('/login');throw Error('Sesión finalizada');}return r.json();});
 window.fetch=async(input,options={})=>{
   const target=new URL(typeof input==='string'?input:input.url,location.href);
   if(target.origin!==location.origin)return originalFetch(input,options);
   const auth=await session,headers=new Headers(options.headers||(input instanceof Request?input.headers:undefined));
   const method=(options.method||(input instanceof Request?input.method:'GET')).toUpperCase();
   if(!['GET','HEAD','OPTIONS'].includes(method))headers.set('X-CSRF-Token',auth.csrf);
   const result=await originalFetch(input,{...options,headers});if(result.status===401)location.replace('/login');return result;
 };
 document.addEventListener('DOMContentLoaded',async()=>{
   const auth=await session;
   const originalSwitch=window.switchPortalView;
   if(originalSwitch)window.switchPortalView=function(view,...args){const routes={hub:'home',schedules:'schedules',tasks:'agenda'};if(routes[view]){location.href='/workspace#'+routes[view];return;}return originalSwitch(view,...args);};
   if(auth.user.role!=='admin')document.querySelectorAll('[id*="Backup"],[id*="backup"],a[href="/api/system/backup"]').forEach(b=>b.hidden=true);
   const back=document.createElement('a');back.href='/workspace';back.textContent='← Volver a mi tienda';back.className='team-return';document.body.prepend(back);
 });
})();
