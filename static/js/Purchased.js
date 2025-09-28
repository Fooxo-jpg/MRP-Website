document.addEventListener("DOMContentLoaded", () => {
  // =========================
  // Sidebar Navigation
  // =========================
  window.toggleSidebar = function () {
    const sidebar = document.getElementById('sidebar');
    const toggleButton = document.getElementById('toggle-btn');
    if (!sidebar || !toggleButton) return;
    sidebar.classList.toggle('close');
    toggleButton.classList.toggle('rotate');
    closeAllSubMenus();
  };

  window.toggleSubMenu = function (button) {
    const sidebar = document.getElementById('sidebar');
    const toggleButton = document.getElementById('toggle-btn');
    if (!button || !button.nextElementSibling) return;
    if (!button.nextElementSibling.classList.contains('show')) {
      closeAllSubMenus();
    }
    button.nextElementSibling.classList.toggle('show');
    button.classList.toggle('rotate');

    if (sidebar.classList.contains('close')) {
      sidebar.classList.toggle('close');
      toggleButton.classList.toggle('rotate');
    }
  };

  function closeAllSubMenus() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    Array.from(sidebar.getElementsByClassName('show')).forEach(ul => {
      ul.classList.remove('show');
      ul.previousElementSibling.classList.remove('rotate');
    });
  }
  // -------------------------
  // Profile Menu
  // -------------------------
  const profileBtn = document.querySelector(".topbar-icon-btn:last-of-type");
  const profileMenu = document.getElementById("profileMenu");

  if (profileBtn && profileMenu) {
    profileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      profileMenu.classList.toggle("show");
    });
    document.addEventListener("click", (e) => {
      if (!profileMenu.contains(e.target) && !profileBtn.contains(e.target)) {
        profileMenu.classList.remove("show");
      }
    });
  }
  // =========================
  // Purchased Orders Table
  // =========================
  const table = document.querySelector(".inventory-table tbody");
  const modal = document.getElementById("bomModal");
  const closeBtn = modal.querySelector(".close");
  const modalProductName = document.getElementById("modalProductName");
  const modalQtyOrdered = document.getElementById("modalQtyOrdered");
  const bomTableBody = document.querySelector("#bomTable tbody");
  const bomTotal = document.getElementById("bomTotal");

  table.addEventListener("click", async (e) => {
    const row = e.target.closest("tr");
    if (!row) return;

    const btn = e.target.closest("button");
    const receivedTd = row.querySelector(".receivedQuantity");
    const statusTd = row.querySelector(".status");
    const actionsTd = row.querySelector(".actions");
    const qtyOrdered = parseInt(row.children[4].textContent, 10);
    const outstandingTd = row.children[9];

    // ----- EDIT -----
    if (btn?.classList.contains("edit-btn")) {
      const currentQty = receivedTd.textContent.trim();
      const currentStatus = statusTd.textContent.trim();

      receivedTd.innerHTML = `<input type="number" class="edit-received" value="${currentQty}" min="0">`;
      statusTd.innerHTML = `
        <select class="edit-status styled-dropdown">
          <option value="Pending" ${currentStatus === "Pending" ? "selected" : ""}>Pending</option>
          <option value="Processing" ${currentStatus === "Processing" ? "selected" : ""}>Processing</option>
          <option value="Completed" ${currentStatus === "Completed" ? "selected" : ""}>Completed</option>
          <option value="Cancelled" ${currentStatus === "Cancelled" ? "selected" : ""}>Cancelled</option>
        </select>

      `;

      actionsTd.innerHTML = `
      <div class="action-buttons">
        <button class="save-btn" id="save-btn-styled">Save</button>
        <button class="cancel-btn" id="cancel-btn-styled">Cancel</button>
      </div>
      `;
      row.classList.add("editing");

      // Dynamically update outstanding and status while typing
      const input = receivedTd.querySelector(".edit-received");
      const outstandingTd = row.children[9];

      const statusSelect = statusTd.querySelector(".edit-status");
      input.addEventListener("input", () => {
        let received = parseInt(input.value) || 0;
        let newOutstanding = Math.max(qtyOrdered - received, 0);
        outstandingTd.textContent = newOutstanding;

        if (statusSelect.value !== "Cancelled") {
          if (received >= qtyOrdered) {
            statusSelect.value = "Completed"; // front-end reflects completed
          } else if (received > 0) {
            statusSelect.value = "Processing"; // optional: in progress
          } else {
            statusSelect.value = "Pending";
          }
        }
      });

      return;
    }

    // ----- SAVE -----
    if (btn?.classList.contains("save-btn")) {
      const id = row.dataset.id;
      let newQty = row.querySelector(".edit-received").value;
      let newStatus = row.querySelector(".edit-status").value;

      if (newStatus === "Cancelled") {
        const confirmCancel = confirm("Are you sure you want to mark this order as Cancelled?");
        if (!confirmCancel) return; // Stop Save
      }

      fetch("/update-purchased", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          _id: id,
          receivedQuantity: newQty,
          status: newStatus
        }),
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            receivedTd.textContent = data.receivedQuantity;
            outstandingTd.textContent = data.outstandingQuantity;
            statusTd.textContent = data.status;

            if (["Completed", "Cancelled"].includes(data.status.toLowerCase())) {
              actionsTd.innerHTML = "";
            } else {
              actionsTd.innerHTML = `<button class="edit-btn">Edit</button>`;
            }
            row.classList.remove("editing");
          } else {
            alert(data.message || "Error saving changes.");
          }
        })
        .catch(err => {
          console.error(err);
          alert("Error saving changes.");
        });

      return;
    }

    // ----- CANCEL -----
    if (btn?.classList.contains("cancel-btn")) {
      const input = row.querySelector(".edit-received");
      const select = row.querySelector(".edit-status");

      receivedTd.textContent = input.defaultValue;
      statusTd.textContent = select.querySelector("option[selected]")?.value || "pending";
      actionsTd.innerHTML = `<button class="edit-btn">Edit</button>`;
      row.classList.remove("editing");
      return;
    }

    // ----- OPEN MODAL -----
    // Don't open modal if row is in edit mode or click is on input/select/button
    if (
      row.classList.contains("editing") ||
      e.target.closest("button, input, select")
    ) return;

    const productName = row.children[3].innerText.trim();
    const quantityOrdered = parseInt(row.children[4].innerText.trim(), 10);

    modalProductName.textContent = productName;
    modalQtyOrdered.textContent = quantityOrdered;

    try {
      const response = await fetch(`/get_bom_items/${encodeURIComponent(productName)}`);
      const items = await response.json();

      bomTableBody.innerHTML = "";
      let grandTotal = 0;

      items.forEach(item => {
        const qtyPerUnit = item.qtyPerUnit;
        const pricePerUnit = item.pricePerUnit;
        const totalPrice = qtyPerUnit * quantityOrdered * pricePerUnit;
        grandTotal += totalPrice;

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${item.itemName}</td>
          <td>${qtyPerUnit}</td>
          <td>$ ${pricePerUnit.toFixed(2)}</td>
          <td>$ ${totalPrice.toFixed(2)}</td>
        `;
        bomTableBody.appendChild(tr);
      });

      bomTotal.textContent = `$ ${grandTotal.toFixed(2)}`;
      modal.style.display = "flex";
    } catch (err) {
      console.error("Error fetching BOM:", err);
    }
  });

  closeBtn.addEventListener("click", () => modal.style.display = "none");
  window.addEventListener("click", e => {
    if (e.target === modal) modal.style.display = "none";
  });
});