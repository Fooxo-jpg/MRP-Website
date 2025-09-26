document.addEventListener("DOMContentLoaded", () => {
  // =========================
  // Sidebar Navigation
  // =========================
  const toggleButton = document.getElementById('toggle-btn');
  const sidebar = document.getElementById('sidebar');

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
  // Filter Toggle (row expand)
  // -------------------------
  const filterBtn = document.querySelector(".filter-btn");
  const filterRow = document.getElementById("filter-row");
  if (filterBtn && filterRow) {
    filterBtn.addEventListener("click", () => {
      filterRow.classList.toggle("show");
    });
  }

  // -------------------------
  // Create Modal
  // -------------------------
  const modal = document.getElementById("createModal");
  const openBtn = document.getElementById("openCreateModalBtn"); // ✅ new selector
  const closeBtn = document.querySelector(".createmodal-close");

  if (openBtn && modal && closeBtn) {
    // Open modal
    openBtn.addEventListener("click", (e) => {
      e.preventDefault();
      modal.style.display = "flex";
    });

    // Close modal
    closeBtn.addEventListener("click", () => modal.style.display = "none");

    // Close modal when clicking outside
    window.addEventListener("click", (e) => {
      if (e.target === modal) modal.style.display = "none";
    });
  }
  // -------------------------
  // Import from CSV
  // -------------------------
  const csvInput = document.getElementById("csvFileInput");
  const importModal = document.getElementById("importModal");

  document.getElementById("importBtn").addEventListener("click", () => csvInput.click());

  csvInput.addEventListener("change", (event) => {
    if (event.target.files.length > 0) {
      const file = event.target.files[0];
      console.log("CSV selected:", file.name);
      const hasData = document.getElementById("hasData").value === "true";
      if (hasData) {
        importModal.style.display = "flex";
      } else {
        handleCSV("delete");
      }
    }
  });

  document.getElementById("cancelImport").addEventListener("click", () => {
    importModal.style.display = "none";
    csvInput.value = "";
  });
  document.getElementById("keepImport").addEventListener("click", () => handleCSV("keep"));
  document.getElementById("deleteImport").addEventListener("click", () => handleCSV("delete"));

  function handleCSV(action) {
    const file = csvInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("action", action);

    fetch("/import_csv", { method: "POST", body: formData })
      .then(res => res.json())
      .then(data => {
        alert(data.message);
        return fetch("/BOM");
      })
      .then(res => res.text())
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");
        const newTbody = doc.querySelector(".inventory-table tbody");
        const oldTbody = document.querySelector(".inventory-table tbody");
        if (newTbody && oldTbody) oldTbody.innerHTML = newTbody.innerHTML;
        sortTable(0, 'asc');
      })
      .catch(err => alert("Error importing: " + err));

    importModal.style.display = "none";
    csvInput.value = "";
  }

  // -------------------------
  // Table Filter & Sorting
  // -------------------------
  const filterToggle = document.getElementById("filterToggle");
  const filterMenu = document.getElementById("filterMenu");
  const filterColumn = document.getElementById("filterColumn");
  const filterOrder = document.getElementById("filterOrder");

  if (filterToggle && filterMenu) {
    filterToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      filterMenu.classList.toggle("show");
    });

    document.addEventListener("click", (e) => {
      if (!filterMenu.contains(e.target) && !filterToggle.contains(e.target)) {
        filterMenu.classList.remove("show");
      }
    });
  }

  function sortTable(columnIndex, order) {
    const table = document.querySelector("table");
    const tbody = table.querySelector("tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));

    rows.sort((a, b) => {
      const A = a.children[columnIndex].innerText.trim();
      const B = b.children[columnIndex].innerText.trim();
      let cmp;

      switch (columnIndex) {
        case 0: // PRODUCT CODE
        case 2: // BOM LEVEL
        case 5: //QTY PER UNIT
        case 8: // LEAD TIME
        case 9: //COST/UNIT
          const numA = parseFloat(A.replace(/[^0-9.-]+/g, "")) || 0;
          const numB = parseFloat(B.replace(/[^0-9.-]+/g, "")) || 0;
          cmp = numA - numB;
          break;
        case 3: // ITEM CODE [XX-00]
          const extractNum = (val) => {
            const match = val.match(/-(\d+)$/);
            return match ? parseInt(match[1], 10) : 0;
          };
          cmp = extractNum(A) - extractNum(B);
          break;
        default: // ALL OTHER COLUMNS
          cmp = A.localeCompare(B, undefined, { numeric: true, sensitivity: "base" });
          break;
      }

      return order === "asc" ? cmp : -cmp;
    });

    rows.forEach(row => tbody.appendChild(row));
  }

  function applySorting() {
    if (filterColumn.value && filterOrder.value) {
      sortTable(parseInt(filterColumn.value), filterOrder.value);
      filterMenu.classList.remove("show");
    }
  }

  if (filterColumn && filterOrder) {
    filterColumn.addEventListener("change", applySorting);
    filterOrder.addEventListener("change", applySorting);
    sortTable(0, "asc");
    filterColumn.value = "0";
    filterOrder.value = "asc";
  }

  // -------------------------
  // Form Part (Groups + Input)
  // -------------------------
  const nameInput = document.getElementById("name");
  const groupNameSelect = document.getElementById("groupName");
  const groupMapping = {
    "Raw Materials": "RM0001",
    "Mechanical Part": "MP0101",
    "Electrical Part": "EP0201",
    "Hardware": "HW0301",
    "Consumable": "CS0401",
    "Packaging": "PK0501"
  };

  if (nameInput) {
    nameInput.addEventListener("input", () => {
      nameInput.value = nameInput.value.replace(/[^a-zA-Z0-9 ]/g, "");
    });
  }

  const defaultGroups = Object.keys(groupMapping);
  if (groupNameSelect) {
    defaultGroups.forEach(group => {
      const option = document.createElement("option");
      option.value = group;
      option.textContent = group;
      groupNameSelect.appendChild(option);
    });

    groupNameSelect.addEventListener("change", () => {
      const selected = groupNameSelect.value;
      if (!defaultGroups.includes(selected) && selected.trim() !== "") {
        defaultGroups.push(selected);
        const option = document.createElement("option");
        option.value = selected;
        option.textContent = selected;
        groupNameSelect.appendChild(option);
      }
    });
  }

  document.querySelectorAll(".group-name").forEach(select => {
    select.addEventListener("change", function () {
      const row = this.closest("tr");
      const groupIdField = row.querySelector(".group-id");
      groupIdField.value = groupMapping[this.value] || "";
    });
  });

  // -------------------------
  // Search BOM
  // -------------------------
  const searchBtn = document.querySelector("#filter-row .secondary-btn:nth-child(1)");
  const clearBtn = document.querySelector("#filter-row .secondary-btn:nth-child(2)");
  const tableBody = document.querySelector(".inventory-table tbody");

  if (searchBtn && clearBtn) {
    searchBtn.addEventListener("click", () => {
      const filters = Array.from(filterRow.querySelectorAll("input"))
        .map(input => input.value.trim().toLowerCase());

      Array.from(tableBody.querySelectorAll("tr")).forEach(row => {
        const cells = Array.from(row.querySelectorAll("td"));
        let show = true;

        cells.forEach((cell, index) => {
          if (index === 6) {
            const min = parseFloat(filters[index * 2]) || -Infinity;
            const max = parseFloat(filters[index * 2 + 1]) || Infinity;
            const cost = parseFloat(cell.textContent.replace(/[^0-9.-]+/g, ""));
            if (!isNaN(cost) && (cost < min || cost > max)) show = false;
          } else if (filters[index] && !cell.textContent.toLowerCase().includes(filters[index])) {
            show = false;
          }
        });

        row.style.display = show ? "" : "none";
      });
    });

    clearBtn.addEventListener("click", () => {
      filterRow.querySelectorAll("input").forEach(input => input.value = "");
      tableBody.querySelectorAll("tr").forEach(row => row.style.display = "");
    });
  }

  // -------------------------
  // Cost Field (2 decimals)
  // -------------------------
  const costInput = document.getElementById("cost");
  if (costInput && modal) {
    const formatToTwoDecimals = () => {
      let value = costInput.value.trim();
      if (value !== "") {
        let num = parseFloat(value);
        if (!isNaN(num)) costInput.value = num.toFixed(2);
      }
    };
    costInput.addEventListener("blur", formatToTwoDecimals);
    modal.addEventListener("submit", formatToTwoDecimals);
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
  // Export CSV
  // -------------------------
  document.getElementById("csv").addEventListener("click", () => {
    fetch("/export_csv", { method: "POST" })
      .then(response => response.blob())
      .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "bom_export.csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
      })
      .catch(err => {
        console.error("CSV download failed:", err);
        alert("Failed to export CSV.");
      });
  });

  // -------------------------
  // Export PDF
  // -------------------------
  document.getElementById("pdf").addEventListener("click", () => {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const table = document.querySelector(".inventory-table tbody");
    if (!table) return alert("No table data found!");

    let y = 20;
    table.querySelectorAll("tr").forEach(row => {
      const cells = row.querySelectorAll("td");
      if (cells.length >= 10) {
        const rowData = {
          productCode: cells[0].innerText.trim(),
          productName: cells[1].innerText.trim(),
          bomLevel: cells[2].innerText.trim(),
          itemCode: cells[3].innerText.trim(),
          itemName: cells[4].innerText.trim(),
          qtyPerUnit: cells[5].innerText.trim(),
          uom: cells[6].innerText.trim(),
          supplier: cells[7].innerText.trim(),
          leadTime: cells[8].innerText.trim(),
          costPerUnit: cells[9].innerText.trim(),
        };

        doc.text(`Product Code: ${rowData.productCode}`, 10, y); y += 8;
        doc.text(`Product Name: ${rowData.productName}`, 10, y); y += 8;
        doc.text(`BOM Level: ${rowData.bomLevel}`, 10, y); y += 8;
        doc.text(`Item Code: ${rowData.itemCode}`, 10, y); y += 8;
        doc.text(`Item Name: ${rowData.itemName}`, 10, y); y += 8;
        doc.text(`Qty per Unit: ${rowData.qtyPerUnit}`, 10, y); y += 8;
        doc.text(`UOM: ${rowData.uom}`, 10, y); y += 8;
        doc.text(`Supplier: ${rowData.supplier}`, 10, y); y += 8;
        doc.text(`Lead Time: ${rowData.leadTime}`, 10, y); y += 8;
        doc.text(`Cost/Unit: ${rowData.costPerUnit}`, 10, y); y += 12;

        if (y > 270) { doc.addPage(); y = 20; }
      }
    });
    doc.save("BOM.pdf");
  });
});

