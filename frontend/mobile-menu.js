(() => {
  function setup(){
    const host=document.querySelector('.topbar,.studio-topline');
    if(!host)return;
    const button=document.createElement('button');
    button.className='mobile-menu-toggle';button.type='button';button.textContent='☰';
    button.setAttribute('aria-label','Abrir menú');button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-expanded','false');button.setAttribute('aria-controls','mobile-menu');
    host.prepend(button);
    const drawer=document.createElement('dialog');drawer.id='mobile-menu';drawer.setAttribute('aria-labelledby','mobile-menu-title');
    document.body.append(drawer);
    button.addEventListener('click',()=>{
      drawer.replaceChildren();
      const header=document.createElement('div');header.className='mobile-menu-heading';
      const title=document.createElement('strong');title.id='mobile-menu-title';title.textContent='FARO · Mi tienda';
      const close=document.createElement('button');close.textContent='✕';close.setAttribute('aria-label','Cerrar menú');close.onclick=()=>drawer.close();header.append(title,close);drawer.append(header);
      const source=document.querySelector('.sidebar');
      if(source){
        const nav=source.querySelector('nav').cloneNode(true);const footer=source.querySelector('.sidebar-bottom').cloneNode(true);
        for(const node of [...nav.querySelectorAll('[id]'),...footer.querySelectorAll('[id]')])node.removeAttribute('id');
        for(const node of nav.querySelectorAll('.active'))node.setAttribute('aria-current','page');
        drawer.append(nav,footer);
      }else{
        const nav=document.createElement('nav');nav.setAttribute('aria-label','Secciones de FARO');
        for(const [label,url] of [['Inicio','/workspace#home'],['Agenda de tienda','/workspace#agenda'],['Horarios','/workspace#schedules'],['Peticiones','/workspace#requests'],['Inventario','/inventory#faro'],['Catálogo','/inventory#catalogo'],['Equipo y accesos','/workspace#accounts']]){
          const a=document.createElement('a');a.textContent=label;a.href=url;if(url===location.pathname+location.hash)a.setAttribute('aria-current','page');nav.append(a);
        }
        drawer.append(nav);
      }
      drawer.showModal();document.body.classList.add('menu-visible');button.setAttribute('aria-expanded','true');
    });
    drawer.addEventListener('click',e=>{if(e.target.closest('a,[data-view],[data-action]'))drawer.close();else if(e.target===drawer){const r=drawer.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)drawer.close();}});
    drawer.addEventListener('close',()=>{document.body.classList.remove('menu-visible');button.setAttribute('aria-expanded','false');button.focus();});
    matchMedia('(min-width:701px)').addEventListener('change',e=>{if(e.matches&&drawer.open)drawer.close();});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup);else setup();
})();
