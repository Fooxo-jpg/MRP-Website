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
  }

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

  // -------------------------
  // ITEM LIST
  // -------------------------
  const rows = document.querySelectorAll(".inventory-table tbody tr[data-id]");
  const modal = document.getElementById("bomModal");
  const closeBtn = modal.querySelector(".close");
  const modalProductName = document.getElementById("modalProductName");
  const modalQtyOrdered = document.getElementById("modalQtyOrdered");
  const bomTableBody = document.querySelector("#bomTable tbody");
  const bomTotal = document.getElementById("bomTotal");

  rows.forEach(row => {
    row.addEventListener("click", async (e) => {
      if (
        e.target.classList.contains("edit-btn") ||
        e.target.classList.contains("status-dropdown")
      ) {
        return; // don't open modal
      }

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
  });

  closeBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });

  window.addEventListener("click", e => {
    if (e.target === modal) {
      modal.style.display = "none";
    }
  });
});