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
  // ====== Create User ======
  const createUserBtn = document.getElementById("createUserBtn");
  if (createUserBtn) {
    createUserBtn.addEventListener("click", async () => {
      const username = document.getElementById("inpUsername").value.trim();
      const email = document.getElementById("inpEmail").value.trim();
      const contact = document.getElementById("inpContact").value.trim();
      const password = document.getElementById("inpPassword").value.trim();

      if (!username || !email || !password) {
        alert("Username, Email and Password are required");
        return;
      }

      try {
        const res = await fetch("/create-user", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email, contact, password }),
        });

        const data = await res.json();
        if (data.success) {
          location.reload(); // reload to show new user in table
        } else {
          alert(data.message || "Failed to create user");
        }
      } catch (err) {
        console.error("Error creating user:", err);
        alert("Error creating user");
      }
    });
  }


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
  // User Management
  // -------------------------

  const modalBackdrop = document.getElementById("modalBackdrop");
  const openCreate = document.getElementById("openCreate");
  const closeModal = document.getElementById("closeModal");

  // ====== Modal Controls ======
  function openModal() {
    modalBackdrop.classList.add("show");
    modalBackdrop.setAttribute("aria-hidden", "false");
    document.getElementById("inpUsername").focus();
  }
  function closeModalFunc() {
    modalBackdrop.classList.remove("show");
    modalBackdrop.setAttribute("aria-hidden", "true");
  }

  if (openCreate) openCreate.addEventListener("click", openModal);
  if (closeModal) closeModal.addEventListener("click", closeModalFunc);
  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", (e) => {
      if (e.target === modalBackdrop) closeModalFunc();
    });
  }
  const usernameInput = document.getElementById("inpUsername");
  usernameInput.addEventListener("input", (e) => {
    e.target.value = e.target.value.replace(/\s+/g, "");
  });

  const emailInput = document.getElementById("inpEmail");

  emailInput.addEventListener("input", (e) => {
    let value = e.target.value;

    // Prevent @ at start
    if (value.startsWith("@")) {
      value = value.replace(/^@+/, ""); // strip any leading @
    }

    // Prevent multiple '@'
    const atCount = (value.match(/@/g) || []).length;
    if (atCount > 1) {
      // keep only the first @, remove others
      let firstAtIndex = value.indexOf("@");
      value =
        value.slice(0, firstAtIndex + 1) +
        value.slice(firstAtIndex + 1).replace(/@/g, "");
    }

    e.target.value = value;

    // Final regex validation for format
    const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
    if (value && !emailRegex.test(value)) {
      emailInput.setCustomValidity("Enter a valid email (e.g., user@example.com)");
    } else {
      emailInput.setCustomValidity("");
    }
  });


  function attachDeleteHandlers() {
    document.querySelectorAll(".delete-btn").forEach(btn => {
      if (btn.dataset.bound === "1") return; // prevent duplicate bindings
      btn.dataset.bound = "1";

      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        if (!confirm("Delete this user?")) return;

        try {
          const res = await fetch("/delete-user", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ _id: id })
          });

          const data = await res.json();
          if (data.success) {
            btn.closest("tr").remove(); // remove row from table
          } else {
            alert(data.message || "Failed to delete user");
          }
        } catch (err) {
          console.error("Error deleting user:", err);
          alert("Error deleting user");
        }
      });
    });
  }

  // attach at start
  attachDeleteHandlers();


  // ====== Password Toggle ======
  function attachToggleHandlers(root = document) {
    root.querySelectorAll(".toggle-pw").forEach(btn => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";

      btn.addEventListener("click", (e) => {
        const cell = e.currentTarget.closest(".pw-cell");
        const input = cell.querySelector(".pw-display");
        if (!input) return;
        if (input.type === "password") {
          input.type = "text";
          e.currentTarget.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M3 3l18 18" stroke="#6b6b6b" stroke-width="1.4" stroke-linecap="round"/></svg>`;
        } else {
          input.type = "password";
          e.currentTarget.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" stroke="#6b6b6b" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" stroke="#6b6b6b" stroke-width="1.2"/></svg>`;
        }
      });
    });
  }

  // Attach to initial table
  attachToggleHandlers(document);
});