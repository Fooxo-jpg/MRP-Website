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
  // STOCK
  // -------------------------

  // -------------------------
  // Update Summary Box live
  // -------------------------
  document.querySelectorAll(".product-request").forEach(productDiv => {
    const stockEl = productDiv.querySelector(".current-stock");
    const reorderEl = productDiv.querySelector(".base-reorder");
    const newStockEl = productDiv.querySelector(".new-stock");
    const multiplierInput = productDiv.querySelector(".order-input");
    const orderBtn = productDiv.querySelector(".order-btn");

    if (multiplierInput) {
      multiplierInput.addEventListener("input", () => {
        const multiplier = parseInt(multiplierInput.value) || 1;
        const baseReorder = parseInt(reorderEl.textContent) || 0;
        const currentStock = parseInt(stockEl.textContent) || 0;

        // Calculate live values
        const finalQty = baseReorder * multiplier;
        const projectedStock = currentStock + finalQty;

        // Update summary block
        newStockEl.textContent = projectedStock;
        productDiv.querySelector(".summary-reorder").textContent = finalQty;
      });
    }


    orderBtn.addEventListener("click", () => {
      const multiplier = parseInt(multiplierInput.value) || 1;
      const itemId = productDiv.dataset.id;  // ✅ store ObjectId in data-id in your HTML

      fetch("/place-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          _id: itemId,
          multiplier: multiplier
        })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            stockEl.textContent = data.newStock;
            newStockEl.textContent = data.newStock;
            alert(`✅ Ordered ${data.orderedQty} units. Total cost: $${data.totalCost.toFixed(2)}`);

            productDiv.remove();
          } else {
            alert(`❌ Error: ${data.message}`);
          }
        })
        .catch(err => console.error("Fetch error:", err));
    });
  });


});