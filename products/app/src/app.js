const preview=document.querySelector('#preview-cleanse');
const simulationStatus=document.querySelector('#simulation-status');
const navLinks=[...document.querySelectorAll('nav a[href^="#"]')];

preview?.addEventListener('click',()=>{
  preview.disabled=true;
  const title=preview.querySelector('span');
  const detail=preview.querySelector('small');
  if(title) title.textContent='Preview selected';
  if(detail) detail.textContent='Simulation only';
  if(simulationStatus) simulationStatus.textContent='Prototype cleanse preview selected. No device command was sent and no live telemetry is available.';
});

function syncNavigation(){
  const target=window.location.hash||'#home';
  for(const link of navLinks){
    const active=link.getAttribute('href')===target;
    link.classList.toggle('active',active);
    if(active) link.setAttribute('aria-current','location');
    else link.removeAttribute('aria-current');
  }
}

window.addEventListener('hashchange',syncNavigation);
syncNavigation();
