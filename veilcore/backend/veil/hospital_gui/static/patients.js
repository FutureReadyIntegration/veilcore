function openForm() {
    const modal = document.getElementById("patient-form");
    if (modal) modal.style.display = "flex";
}

function closeForm() {
    const modal = document.getElementById("patient-form");
    if (modal) modal.style.display = "none";
}

async function submitPatient() {
    const name = document.getElementById("patient-name").value.trim();
    const dob = document.getElementById("patient-dob").value.trim();

    if (!name || !dob) return;

    await fetch("/api/patients", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, dob })
    });

    closeForm();
    await loadPatients();
}

async function loadPatients() {
    const res = await fetch("/api/patients");
    const data = await res.json();
    const list = document.getElementById("patient-list");

    if (!data || data.length === 0) {
        list.innerHTML = "<div class='vh-empty'>No patients yet.</div>";
        return;
    }

    list.innerHTML = "";
    data.forEach(p => {
        const row = document.createElement("div");
        row.className = "vh-row";
        row.innerHTML = `
            <div class="vh-row-main">
                <span class="vh-glyph">🩺</span>
                <span class="vh-row-title">${p.name || "Unnamed"}</span>
                <span class="vh-badge">${p.dob || "DOB unknown"}</span>
            </div>
        `;
        list.appendChild(row);
    });
}

window.addEventListener("load", () => {
    loadPatients();
});
