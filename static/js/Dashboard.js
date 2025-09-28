document.addEventListener("DOMContentLoaded", () => {
  const evtSource = new EventSource("/stream");
  evtSource.onmessage = function (event) {
    const data = JSON.parse(event.data);
    const notificationsContainer = document.getElementById("notifications-container");
    if (notificationsContainer) {
      notificationsContainer.insertAdjacentHTML("afterbegin", data.html);
    }
  };
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
});