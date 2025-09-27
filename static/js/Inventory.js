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
        case 4: // CURRENT STOCK
        case 5: // REORDER LEVEL
        case 6: // REORDER QTY
        case 7: // COST/UNIT
        case 8: // TOTAL VALUE
        case 10: // LEAD TIME
          const numA = parseFloat(A.replace(/[^0-9.-]+/g, "")) || 0;
          const numB = parseFloat(B.replace(/[^0-9.-]+/g, "")) || 0;
          cmp = numA - numB;
          break;
        case 0: // ITEM CODE
          const extractNum = (val) => {
            const match = val.match(/-(\d+)$/);
            return match ? parseInt(match[1], 10) : 0;
          };
          cmp = extractNum(A) - extractNum(B);
          break;
        default: // All other columns (text)
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
  // ITEM ANALYTICS
  // -------------------------
  document.querySelectorAll(".itemAnalyticsBtn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const itemCode = btn.dataset.itemcode;
      const modal = document.getElementById("itemAnalyticsModal");
      const tbody = document.querySelector("#analyticsTable tbody");
      tbody.innerHTML = ""; // clear old rows

      try {
        const response = await fetch(`/item-analytics/${itemCode}`);
        const data = await response.json();

        if (data.length === 0) {
          tbody.innerHTML = `<tr><td colspan="3">No products use this item.</td></tr>`;
        } else {
          data.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td>${row.productName}</td><td>${row.qtyPerUnit}</td><td>${row.uom}</td>`;
            tbody.appendChild(tr);
          });
        }

        modal.style.display = "flex"; // show modal
      } catch (err) {
        console.error(err);
        alert("Failed to fetch item usage data.");
      }
    });
  });

  // Close when clicking outside modal
  window.addEventListener("click", e => {
    const modal = document.getElementById("itemAnalyticsModal");
    if (e.target === modal) modal.style.display = "none";
  });

  // -------------------------
  // EDIT INVENTORY ITEM MODAL
  // -------------------------
  const editModal = document.getElementById('edit_InventoryItemModal');
  const cancelBtn = editModal.querySelector('button[type="button"]');
  const saveBtn = editModal.querySelector('button[type="submit"]');
  const deleteBtn = editModal.querySelector('#deleteItemBtn');

  function openEditModal(itemData) {
    // Populate modal fields
    editModal.querySelector('#edit_itemId').value = itemData._id;
    editModal.querySelector('#edit_itemName').value = itemData.name;
    editModal.querySelector('#edit_itemCode').value = itemData.code;
    editModal.querySelector('#edit_category').value = itemData.category;
    editModal.querySelector('#edit_uom').value = itemData.uom;
    editModal.querySelector('#edit_currentStock').value = itemData.currentStock;
    editModal.querySelector('#edit_reorderLevel').value = itemData.reorderLevel;
    editModal.querySelector('#edit_reorderQty').value = itemData.reorderQty;
    editModal.querySelector('#edit_costPerUnit').value = itemData.costPerUnit;
    editModal.querySelector('#edit_totalValue').value = itemData.totalValue;
    editModal.querySelector('#edit_supplier').value = itemData.supplier;
    editModal.querySelector('#edit_leadTime').value = itemData.leadTime;

    // Populate USED IN table
    const usedInTableBody = editModal.querySelector('#usedInTable tbody');
    usedInTableBody.innerHTML = ''; // clear previous rows
    itemData.usedIn.forEach(product => {
      const row = document.createElement('tr');
      row.innerHTML = `<td>${product.code}</td><td>${product.name}</td><td>${product.qty}</td>`;
      usedInTableBody.appendChild(row);
    });

    // Show modal
    editModal.style.display = 'block';
  }

  document.querySelectorAll('.editItemBtn').forEach(btn => {
    btn.addEventListener('click', () => {
      const row = btn.closest('tr');
      currentEditingRow = row;
      const itemData = {
        _id: row.dataset.id,
        name: row.children[1].innerText,
        code: row.children[0].innerText,
        category: row.children[2].innerText,
        uom: row.children[3].innerText,
        currentStock: row.children[4].innerText,
        reorderLevel: row.children[5].innerText,
        reorderQty: row.children[6].innerText,
        costPerUnit: row.children[7].innerText.replace('$', '').trim(),
        totalValue: row.children[8].innerText.replace('$', '').trim(),
        supplier: row.children[9].innerText,
        leadTime: row.children[10].innerText.replace('Days', '').trim()
      };
      openEditModal(itemData);
    });
  });


  // CLOSE MODAL
  function closeModal() { editModal.style.display = 'none'; }
  cancelBtn.addEventListener('click', closeModal);

  // CLOSE MODAL IF CLICKED OUTSIDE
  window.addEventListener('click', (e) => {
    if (e.target === editModal) {
      closeModal();
    }
  });

  // DELETE BUTTON
  deleteBtn.addEventListener('click', async () => {
    if (!confirm("Are you sure you want to delete this item?")) return;

    const itemId = editModal.querySelector('#edit_itemId').value;

    try {
      const response = await fetch('/delete-inventory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ _id: itemId })
      });

      const result = await response.json();
      if (result.success) {
        alert('Item deleted successfully');
        closeModal();
        location.reload();
      } else {
        alert('Failed to delete: ' + result.message);
      }
    } catch (err) {
      console.error('Error deleting item:', err);
      alert('Error deleting item. Check console.');
    }
  })

  // SAVE BUTTON
  saveBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    const editedItem = {
      _id: editModal.querySelector('#edit_itemId').value,
      name: editModal.querySelector('#edit_itemName').value,
      code: editModal.querySelector('#edit_itemCode').value,
      category: editModal.querySelector('#edit_category').value,
      uom: editModal.querySelector('#edit_uom').value,
      currentStock: editModal.querySelector('#edit_currentStock').value,
      reorderLevel: editModal.querySelector('#edit_reorderLevel').value,
      reorderQty: editModal.querySelector('#edit_reorderQty').value,
      costPerUnit: editModal.querySelector('#edit_costPerUnit').value,
      totalValue: editModal.querySelector('#edit_totalValue').value,
      supplier: editModal.querySelector('#edit_supplier').value,
      leadTime: editModal.querySelector('#edit_leadTime').value
    };

    try {
      const response = await fetch('/update-inventory', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editedItem)
      });

      const result = await response.json();
      console.log(result);

      if (result.success) {
        alert('Item saved successfully!');
        closeModal();
        location.reload();
      } else {
        alert('Failed to save item: ' + result.message);
      }
    } catch (error) {
      console.error('Error saving item:', error);
      alert('Error saving item. Check console for details.');
    }
  });

  // Example: Attach edit buttons
  document.querySelectorAll('.editItemBtn').forEach(button => {
    button.addEventListener('click', () => {
      document.getElementById('edit_InventoryItemModal').style.display = 'block';
    });
  });

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
          itemCode: cells[0].innerText.trim(),
          itemName: cells[1].innerText.trim(),
          category: cells[2].innerText.trim(),
          uom: cells[3].innerText.trim(),
          currentStock: cells[4].innerText.trim(),
          reorderLvl: cells[5].innerText.trim(),
          reorderQty: cells[6].innerText.trim(),
          costPerUnit: cells[7].innerText.trim(),
          totalValue: cells[8].innerText.trim(),
          supplier: cells[9].innerText.trim(),
          leadTime: cells[10].innerText.trim(),
        };

        doc.text(`Item Code: ${rowData.itemCode}`, 10, y); y += 8;
        doc.text(`Item Name: ${rowData.itemName}`, 10, y); y += 8;
        doc.text(`Category: ${rowData.category}`, 10, y); y += 8;
        doc.text(`UOM: ${rowData.uom}`, 10, y); y += 8;
        doc.text(`Current Stock: ${rowData.currentStock}`, 10, y); y += 8;
        doc.text(`Reorder Level: ${rowData.reorderLvl}`, 10, y); y += 8;
        doc.text(`Reorder Qty: ${rowData.reorderQty}`, 10, y); y += 8;
        doc.text(`Cost/Unit: ${rowData.costPerUnit}`, 10, y); y += 8;
        doc.text(`Total Value: ${rowData.totalValue}`, 10, y); y += 8;
        doc.text(`Supplier: ${rowData.supplier}`, 10, y); y += 8;
        doc.text(`Lead Time: ${rowData.leadTime}`, 10, y); y += 12;

        if (y > 270) { doc.addPage(); y = 20; }
      }
    });
    doc.save("BOM.pdf");
  });
});

