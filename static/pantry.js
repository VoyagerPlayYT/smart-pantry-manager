// SMART PANTRY & EXPIRY // Production Logic
(function() {
  const metricExpiring = document.getElementById('metricExpiring');
  const metricExpired = document.getElementById('metricExpired');
  const pantryTableBody = document.getElementById('pantryTableBody');
  const recipesGrid = document.getElementById('recipesGrid');

  const locBtns = document.querySelectorAll('.loc-btn');
  const cntAll = document.getElementById('cntAll');
  const cntFridge = document.getElementById('cntFridge');
  const cntFreezer = document.getElementById('cntFreezer');
  const cntPantry = document.getElementById('cntPantry');
  const cntSpices = document.getElementById('cntSpices');

  const btnSyncExpiring = document.getElementById('btnSyncExpiring');
  const shoppingListItems = document.getElementById('shoppingListItems');
  const newShopItemInput = document.getElementById('newShopItemInput');
  const btnAddShopItem = document.getElementById('btnAddShopItem');

  const viewTabs = document.querySelectorAll('.v-tab');
  const tabPanes = document.querySelectorAll('.tab-pane');

  const productModal = document.getElementById('productModal');
  const btnOpenAddProduct = document.getElementById('btnOpenAddProduct');
  const btnCloseProductModal = document.getElementById('btnCloseProductModal');
  const btnSubmitProduct = document.getElementById('btnSubmitProduct');
  const prodName = document.getElementById('prodName');
  const prodLocation = document.getElementById('prodLocation');
  const prodQty = document.getElementById('prodQty');
  const prodUnit = document.getElementById('prodUnit');
  const prodExpiry = document.getElementById('prodExpiry');

  let activeLocation = "ALL";
  let products = [];

  // Tab switching
  viewTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      viewTabs.forEach(t => t.classList.remove('active'));
      tabPanes.forEach(p => p.classList.add('hidden'));

      tab.classList.add('active');
      const pane = document.getElementById('pane' + tab.dataset.tab.charAt(0).toUpperCase() + tab.dataset.tab.slice(1));
      if (pane) pane.classList.remove('hidden');

      if (tab.dataset.tab === 'recipes') fetchRecipeSuggestions();
    });
  });

  // Locations filtering
  locBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      locBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeLocation = btn.dataset.loc;
      fetchProducts();
    });
  });

  // Fetch Products
  async function fetchProducts() {
    try {
      const url = activeLocation === 'ALL' ? '/api/products' : `/api/products?location=${activeLocation}`;
      const res = await fetch(url);
      const data = await res.json();
      products = data.products;

      // Update counters
      let soon = 0, exp = 0;
      let cFridge = 0, cFreezer = 0, cPantry = 0, cSpices = 0;

      // Also get all products for count breakdown
      const resAll = await fetch('/api/products');
      const dataAll = await resAll.json();
      dataAll.products.forEach(p => {
        if (p.status === 'EXPIRING_SOON') soon++;
        if (p.status === 'EXPIRED') exp++;

        if (p.location === 'Fridge') cFridge++;
        else if (p.location === 'Freezer') cFreezer++;
        else if (p.location === 'Pantry') cPantry++;
        else if (p.location === 'Spice Rack') cSpices++;
      });

      metricExpiring.textContent = `${soon} ITEMS`;
      metricExpired.textContent = `${exp} ITEMS`;

      cntAll.textContent = dataAll.products.length;
      cntFridge.textContent = cFridge;
      cntFreezer.textContent = cFreezer;
      cntPantry.textContent = cPantry;
      cntSpices.textContent = cSpices;

      renderPantryTable();
    } catch (e) {
      console.error(e);
    }
  }

  function renderPantryTable() {
    pantryTableBody.innerHTML = '';
    products.forEach(p => {
      const tr = document.createElement('tr');
      let statusHtml = '<span class="badge-fresh">СВЕЖЕЕ</span>';
      let remainingText = `${p.days_left} дн.`;

      if (p.status === 'EXPIRING_SOON') {
        statusHtml = '<span class="badge-soon">ИСТЕКАЕТ СКОРО</span>';
        remainingText = `<strong class="text-amber">${p.days_left} дн.</strong>`;
      } else if (p.status === 'EXPIRED') {
        statusHtml = '<span class="badge-expired">ПРОСРОЧЕНО</span>';
        remainingText = `<strong class="text-red">Просрочено!</strong>`;
      }

      tr.innerHTML = `
        <td style="font-weight:700;">${escapeHtml(p.name)}</td>
        <td><span class="font-mono text-xs text-muted">${escapeHtml(p.location)}</span></td>
        <td class="font-mono">${p.quantity} ${escapeHtml(p.unit)}</td>
        <td class="font-mono">${p.expiry_date}</td>
        <td class="font-mono">${remainingText}</td>
        <td>${statusHtml}</td>
        <td>
          <button class="mini-btn text-muted del-prod-btn" data-id="${p.id}">✕ Употребить</button>
        </td>
      `;

      tr.querySelector('.del-prod-btn').addEventListener('click', () => deleteProduct(p.id));
      pantryTableBody.appendChild(tr);
    });
  }

  async function deleteProduct(id) {
    await fetch(`/api/products/${id}`, { method: 'DELETE' });
    fetchProducts();
  }

  // Shopping List
  async function fetchShoppingList() {
    try {
      const res = await fetch('/api/shopping');
      const data = await res.json();
      shoppingListItems.innerHTML = '';

      data.items.forEach(item => {
        const row = document.createElement('div');
        row.className = `shop-item-row ${item.is_bought ? 'bought' : ''}`;
        row.innerHTML = `
          <div style="display:flex;align-items:center;gap:6px;">
            <input type="checkbox" ${item.is_bought ? 'checked' : ''} class="toggle-bought">
            <span>${escapeHtml(item.item_name)} (${escapeHtml(item.quantity)})</span>
          </div>
          <button class="mini-btn text-muted del-shop-btn">✕</button>
        `;

        row.querySelector('.toggle-bought').addEventListener('change', async () => {
          await fetch(`/api/shopping/${item.id}/toggle`, { method: 'PUT' });
          fetchShoppingList();
        });

        row.querySelector('.del-shop-btn').addEventListener('click', async () => {
          await fetch(`/api/shopping/${item.id}`, { method: 'DELETE' });
          fetchShoppingList();
        });

        shoppingListItems.appendChild(row);
      });
    } catch (e) {
      console.error(e);
    }
  }

  btnAddShopItem.addEventListener('click', async () => {
    const val = newShopItemInput.value.trim();
    if (!val) return;
    await fetch('/api/shopping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_name: val, quantity: '1 шт' })
    });
    newShopItemInput.value = '';
    fetchShoppingList();
  });

  btnSyncExpiring.addEventListener('click', async () => {
    const res = await fetch('/api/shopping/sync-expiring', { method: 'POST' });
    const data = await res.json();
    alert(`Синхронизировано: добавлено ${data.added_count} истекающих позиций в список покупок.`);
    fetchShoppingList();
  });

  // Recipe Suggestions
  async function fetchRecipeSuggestions() {
    try {
      const res = await fetch('/api/recipes/suggestions');
      const data = await res.json();
      recipesGrid.innerHTML = '';

      data.suggestions.forEach(rec => {
        const card = document.createElement('div');
        card.className = 'recipe-card';
        card.innerHTML = `
          <div class="recipe-top">
            <span class="recipe-title">${escapeHtml(rec.name)}</span>
            <span class="recipe-cat">${escapeHtml(rec.category)}</span>
          </div>
          <div class="match-bar-track">
            <div class="match-bar-fill" style="width: ${rec.match_pct}%;"></div>
          </div>
          <div style="font-size:11px;font-family:monospace;font-weight:700;color:#D97706;">
            Готовность: ${rec.match_pct}%
          </div>
          <div class="ingredients-box">
            <div>В наличии: <span class="matched-tags">${escapeHtml(rec.matched_ingredients.join(', ') || 'нет')}</span></div>
            ${rec.missing_ingredients.length ? `<div>Не хватает: <span class="missing-tags">${escapeHtml(rec.missing_ingredients.join(', '))}</span></div>` : ''}
          </div>
          <div style="color:#A1A1AA;font-size:11px;margin-top:4px;line-height:1.4;">
            ${escapeHtml(rec.instructions)}
          </div>
        `;
        recipesGrid.appendChild(card);
      });
    } catch (e) {
      console.error(e);
    }
  }

  // Add Product Modal
  btnOpenAddProduct.addEventListener('click', () => {
    // Default expiry 7 days from now
    const d = new Date();
    d.setDate(d.getDate() + 7);
    prodExpiry.value = d.toISOString().split('T')[0];
    productModal.classList.remove('hidden');
  });

  btnCloseProductModal.addEventListener('click', () => productModal.classList.add('hidden'));

  btnSubmitProduct.addEventListener('click', async () => {
    const name = prodName.value.trim();
    if (!name) {
      alert("Укажите название продукта");
      return;
    }

    const payload = {
      name: name,
      location: prodLocation.value,
      quantity: parseFloat(prodQty.value) || 1.0,
      unit: prodUnit.value.trim() || 'шт',
      expiry_date: prodExpiry.value
    };

    const res = await fetch('/api/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      productModal.classList.add('hidden');
      fetchProducts();
    }
  });

  function escapeHtml(str) {
    return String(str).replace(/[&<>'"]/g, tag => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));
  }

  // Boot
  fetchProducts();
  fetchShoppingList();

})();
