/* minimal patients.js */
async function loadPatients(){
  const list = document.getElementById("patient-list"); if(!list) return;
  try{
    const res = await fetch('/api/patients',{credentials:'same-origin'});
    const data = await res.json();
    const patients = Array.isArray(data) ? data : (data.patients || []);
    if(!patients.length){ list.innerHTML = "<div class='vh-empty'>No patients yet.</div>"; return; }
    list.innerHTML = "";
    patients.forEach(p => {
      const row = document.createElement("div"); row.className = "vh-row";
      row.innerHTML = `<div class="vh-row-main"><span>🩺</span><span>${(p.name||'Unnamed')}</span><span>${(p.dob||'DOB unknown')}</span></div>`;
      list.appendChild(row);
    });
  }catch(e){ console.error(e); }
}
window.addEventListener('load', loadPatients);
