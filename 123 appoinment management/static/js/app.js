const $ = (id) => document.getElementById(id);
const modal = $("modal");
const form = $("appointmentForm");
const table = $("appointmentTable");
let searchTimer;

function showToast(message, error=false){
  const toast=$("toast"); toast.textContent=message; toast.className=`toast show${error?' error':''}`;
  clearTimeout(showToast.timer); showToast.timer=setTimeout(()=>toast.className="toast",2800);
}
function openModal(record=null){
  form.reset(); $("appointmentId").value=record?.id||"";
  $("modalTitle").textContent=record?"Edit Appointment":"New Appointment";
  $("saveBtn").textContent=record?"Update Appointment":"Save Appointment";
  if(record){["name","phone","date","time","purpose","status"].forEach(k=>$(k).value=record[k]);}
  else $("status").value="Scheduled";
  modal.classList.remove("hidden"); modal.setAttribute("aria-hidden","false"); $("name").focus();
}
function closeModal(){modal.classList.add("hidden"); modal.setAttribute("aria-hidden","true");}
function escapeHtml(v){return String(v??"").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));}
async function api(url, options={}){
  const res=await fetch(url,{headers:{"Content-Type":"application/json",...(options.headers||{})},...options});
  const data=await res.json().catch(()=>({})); if(!res.ok) throw new Error(data.error||"Something went wrong."); return data;
}
async function load(){
  const q=$("searchInput").value.trim();
  try{
    const [records,stats]=await Promise.all([api(`/api/appointments?q=${encodeURIComponent(q)}`),api("/api/stats")]);
    $("totalCount").textContent=stats.total; $("scheduledCount").textContent=stats.scheduled; $("completedCount").textContent=stats.completed; $("cancelledCount").textContent=stats.cancelled;
    if(!records.length){table.innerHTML='<tr><td colspan="8" class="empty">No appointment records found.</td></tr>';return;}
    table.innerHTML=records.map(r=>`<tr><td>#${r.id}</td><td><b>${escapeHtml(r.name)}</b></td><td>${escapeHtml(r.phone)}</td><td>${escapeHtml(r.date)}</td><td>${escapeHtml(r.time)}</td><td>${escapeHtml(r.purpose)}</td><td><span class="badge ${r.status.toLowerCase()}">${escapeHtml(r.status)}</span></td><td><div class="actions"><button class="small-btn" onclick='editRecord(${JSON.stringify(r)})'>Edit</button><button class="small-btn delete" onclick="deleteRecord(${r.id})">Delete</button></div></td></tr>`).join("");
  }catch(e){table.innerHTML=`<tr><td colspan="8" class="empty">${escapeHtml(e.message)}</td></tr>`;showToast(e.message,true)}
}
window.editRecord=(record)=>openModal(record);
window.deleteRecord=async(id)=>{if(!confirm("Delete this appointment? This action cannot be undone."))return;try{await api(`/api/appointments/${id}`,{method:"DELETE"});showToast("Appointment deleted successfully.");load()}catch(e){showToast(e.message,true)}};
form.addEventListener("submit",async(e)=>{e.preventDefault();const id=$("appointmentId").value;const payload={name:$("name").value,phone:$("phone").value,date:$("date").value,time:$("time").value,purpose:$("purpose").value,status:$("status").value};try{await api(id?`/api/appointments/${id}`:"/api/appointments",{method:id?"PUT":"POST",body:JSON.stringify(payload)});showToast(id?"Appointment updated successfully.":"Appointment added successfully.");closeModal();load()}catch(e){showToast(e.message,true)}});
$("newAppointmentBtn").onclick=()=>openModal(); $("closeModal").onclick=closeModal; $("clearBtn").onclick=()=>form.reset(); $("refreshBtn").onclick=load;
modal.addEventListener("click",e=>{if(e.target===modal)closeModal()}); document.addEventListener("keydown",e=>{if(e.key==="Escape")closeModal()});
$("searchInput").addEventListener("input",()=>{clearTimeout(searchTimer);searchTimer=setTimeout(load,220)});
load();
