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

  const buttons = document.querySelectorAll(".place-order-btn");

  buttons.forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const productDiv = e.target.closest(".product-request");
      const itemId = productDiv.querySelector(".delete-btn").dataset.id;

      try {
        const response = await fetch("/place-order", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ _id: itemId }),
        });

        const result = await response.json();
        if (result.success) {
          // Remove the item row from DOM
          productDiv.remove();

          // Optional: show a success alert
          alert(`Order placed! New stock: ${result.newStock}`);
        } else {
          alert(`Error: ${result.message}`);
        }
      } catch (err) {
        console.error(err);
        alert("Failed to place order.");
      }
    });
  });

});