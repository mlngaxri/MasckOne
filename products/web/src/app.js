const button=document.querySelector('#notify');
const status=document.querySelector('#access-status');
button?.addEventListener('click',()=>{
  button.disabled=true;
  button.textContent='Early access not open';
  if(status) status.textContent='Early access is not open yet. No signup or availability is implied by this preview.';
});