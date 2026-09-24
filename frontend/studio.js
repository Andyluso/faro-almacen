// Presentational navigation; existing module functions remain the source of behavior.
document.querySelectorAll('[data-portal-view]').forEach(button => {
  button.type = 'button';
  button.title = button.textContent.trim();
  button.setAttribute('aria-label', button.textContent.trim());
  button.addEventListener('click', () => switchPortalView(button.dataset.portalView));
});
document.addEventListener('faro:view', event => {
  document.querySelectorAll('[data-portal-view]').forEach(button => {
    const active = button.dataset.portalView === event.detail;
    button.classList.toggle('is-active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
});
const today = new Date();
document.getElementById('studioDate').textContent = new Intl.DateTimeFormat('es-CO', {day:'numeric',month:'long',year:'numeric'}).format(today);
document.getElementById('studioSummaryDate').textContent = new Intl.DateTimeFormat('es-CO', {weekday:'long',day:'numeric',month:'short'}).format(today);
