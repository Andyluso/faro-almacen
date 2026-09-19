// FARO - Flujo de Almacén y Reorden Operativo
// Frontend Application Logic

let currentAuditId = null;
let audits = [];
let allAudits = [];
let selectedAuditDate = '';
let historySearchQuery = '';
let historyDateQuery = '';
let historyChipFilter = 'all';
let allItems = [];
let filteredItems = [];
let currentItemIndex = -1;
let currentFilter = 'all';
let currentGender = 'all';
let currentCategory = 'all';
let currentSizeFilter = 'all';
let sizeSummary = [];
let searchQuery = '';
let viewMode = 'table'; // Modo tabla por defecto (estilo Excel)
let currentSelectedVerdict = '';
let networkInfo = null;

// Navegación principal de pestañas (Auditoría / Catálogo / Archivos)
let currentMainTab = 'audit';

// Catálogo de referencias maestro
let catalogItems = [];
let filteredCatalogItems = [];
let catalogStats = null;
let catalogSearchQuery = '';
let catalogGenderFilter = 'all';
let catalogTypeFilter = 'all';
let catalogPhotoFilter = 'all';
let catalogViewMode = 'grid'; // 'grid' o 'table'
let catalogPhotoUploadRef = '';

// Sección Archivos Excel
let filesFilter = 'all'; // 'all', 'lunes', 'miercoles', 'this_month'
let filesSearchQuery = '';

// ============================================================================
// TABLA MAESTRA DE CODIFICACIÓN OFICIAL SEVEN SEVEN
// ============================================================================
const SEVEN_SEVEN_GARMENT_TYPES = {
  '00': 'Pantaloncillo',
  '01': 'Camisa',
  '06': 'Buzo',
  '07': 'Pantalón',
  '08': 'Chaqueta',
  '09': 'Camiseta',
  '10': 'Bermuda',
  '11': 'Polo',
  '12': 'Blusa',
  '14': 'Falda',
  '15': 'Conjunto 2 Piezas',
  '16': 'Jean',
  '17': 'Vestidos',
  '18': 'Ropa Interior',
  '19': 'Short',
  '20': 'Body',
  '21': 'Accesorios',
  '22': 'Top',
  '23': 'Leggins',
  '25': 'Chaleco',
  '26': 'Capri',
  '27': 'Ropa Playa',
  '29': 'Overol',
  '32': 'Enterizo',
  '33': 'Saco',
  '38': 'Varios',
  '40': 'Blazer',
  '41': 'Pantaloncillo x2',
  '42': 'Pantaloncillo x3',
  '45': 'Anillo',
  '46': 'Aretes',
  '47': 'Bufanda',
  '48': 'Collar',
  '49': 'Gafas',
  '50': 'Pulsera/Tobillera',
  '51': 'Set de Accesorios',
  '52': 'Sombrero/Caps',
  '53': 'Accesorios de Cabello',
  '54': 'Misceláneo',
  '55': 'Colaboraciones',
  '56': 'Autoliquidable',
  '57': 'Accesorios Belleza',
  '58': 'Maquillaje',
  '59': 'Esmalte',
  '60': 'Perfumería',
  '61': 'Corporales',
  '62': 'Bolso/Canguros',
  '63': 'Reloj',
  '64': 'Billetera',
  '98': 'Medias'
};

function decodeSevenSevenReference(ref, name = '') {
  const sRef = String(ref || '').trim();
  const digits = sRef.replace(/\D/g, '');
  let gender = 'Otro';
  let garmentCode = '';
  let garmentType = '';

  if (digits.length >= 4) {
    const dept = digits.substring(0, 2);
    if (dept === '28') {
      gender = 'Dama';
      const code = digits.substring(2, 4);
      if (SEVEN_SEVEN_GARMENT_TYPES[code]) {
        garmentCode = code;
        garmentType = SEVEN_SEVEN_GARMENT_TYPES[code];
      }
    } else if (dept === '45') {
      gender = 'Caballero';
      const code = digits.substring(2, 4);
      if (SEVEN_SEVEN_GARMENT_TYPES[code]) {
        garmentCode = code;
        garmentType = SEVEN_SEVEN_GARMENT_TYPES[code];
      }
    }
  }

  const sName = String(name || '').toLowerCase();
  if (gender === 'Otro' && sName) {
    if (sName.includes('dama') || sName.includes('mujer') || sName.includes('femenin')) {
      gender = 'Dama';
    } else if (sName.includes('caballero') || sName.includes('hombre') || sName.includes('masculin')) {
      gender = 'Caballero';
    }
  }

  return { gender, garmentCode, garmentType };
}

// ============================================================================
// INICIALIZACIÓN
// ============================================================================
document.addEventListener('DOMContentLoaded', async () => {
  initIcons();
  initTabs();
  setupEventListeners();
  initPwaSupport();
  await loadNetworkInfo();
  await loadDatabaseStatus();
  await loadAudits();
  await loadCatalogStats();
});

function initIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// ============================================================================
// HELPERS DE FECHA
// ============================================================================
function formatAuditDateLabel(dateStr) {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length !== 3) return dateStr;
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1;
  const day = parseInt(parts[2], 10);
  const dt = new Date(year, month, day);
  if (isNaN(dt.getTime())) return dateStr;
  
  const dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  return `${dias[dt.getDay()]} ${day} ${meses[month]}`;
}

function formatAuditDateFull(dateStr) {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length !== 3) return dateStr;
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1;
  const day = parseInt(parts[2], 10);
  const dt = new Date(year, month, day);
  if (isNaN(dt.getTime())) return dateStr;
  
  const dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
  const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
  return `${dias[dt.getDay()]}, ${day} de ${meses[month]} de ${year}`;
}

function getDayOfWeekFromDateStr(dateStr) {
  if (!dateStr) return -1;
  const parts = dateStr.split('-');
  if (parts.length !== 3) return -1;
  const dt = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
  return isNaN(dt.getTime()) ? -1 : dt.getDay(); // 0=Dom, 1=Lun, 2=Mar, 3=Mié...
}

// ============================================================================
// CARGA DE DATOS & API
// ============================================================================
async function loadNetworkInfo() {
  try {
    const res = await fetch('/api/system/network-info');
    if (res.ok) {
      networkInfo = await res.json();
      const mobileUrlText = document.getElementById('mobileUrlText');
      if (mobileUrlText) {
        mobileUrlText.textContent = networkInfo.mobile_url;
      }
    }
  } catch (err) {
    console.error('Error al obtener info de red:', err);
  }
}

async function loadDatabaseStatus() {
  try {
    const res = await fetch('/api/system/database-status');
    if (!res.ok) return;
    const data = await res.json();
    const badge = document.getElementById('dbStatusBadge');
    const dot = document.getElementById('dbStatusDot');
    const text = document.getElementById('dbStatusText');
    if (!badge || !text) return;

    if (data.mode === 'supabase' && data.supabase_connected) {
      badge.className = 'hidden sm:inline-flex text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 tracking-normal items-center gap-1 cursor-default';
      badge.title = 'Base de Datos: PostgreSQL (Supabase Cloud)';
      if (dot) dot.className = 'w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse';
      text.textContent = 'Supabase Cloud';
    } else {
      badge.className = 'hidden sm:inline-flex text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 tracking-normal items-center gap-1 cursor-default';
      badge.title = 'Base de Datos: SQLite Local';
      if (dot) dot.className = 'w-1.5 h-1.5 rounded-full bg-amber-400';
      text.textContent = 'SQLite Local';
    }
  } catch (err) {
    console.debug('No se pudo verificar estado de base de datos:', err);
  }
}

async function loadAudits(targetAuditId = null) {
  try {
    const res = await fetch('/api/audits');
    if (!res.ok) throw new Error('Error al listar auditorías');
    allAudits = await res.json();
    
    // Actualizar contador en la pestaña de archivos
    const badgeFiles = document.getElementById('tabFilesBadge');
    if (badgeFiles) {
      badgeFiles.textContent = allAudits.length;
    }

    if (currentMainTab === 'files') {
      renderFilesSection();
    }

    applyAuditDateFilter(selectedAuditDate, targetAuditId);
  } catch (err) {
    console.error(err);
    showToast('Error al cargar auditorías', 'error');
  }
}

function applyAuditDateFilter(dateStr, targetAuditId = null) {
  selectedAuditDate = (dateStr || '').trim();
  const dateInput = document.getElementById('auditDateFilter');
  const btnClear = document.getElementById('btnClearDateFilter');
  
  if (dateInput) dateInput.value = selectedAuditDate;
  if (btnClear) btnClear.classList.toggle('hidden', !selectedAuditDate);

  if (selectedAuditDate) {
    audits = allAudits.filter(a => {
      const aDate = a.audit_date || (a.uploaded_at ? a.uploaded_at.substring(0, 10) : '');
      return aDate === selectedAuditDate;
    });
  } else {
    audits = [...allAudits];
  }

  const selector = document.getElementById('auditSelector');
  if (!selector) return;
  selector.innerHTML = '';

  if (audits.length === 0) {
    if (selectedAuditDate) {
      selector.innerHTML = `<option value="">No hay inventarios el ${formatAuditDateLabel(selectedAuditDate)}</option>`;
      showToast(`No hay inventarios para la fecha ${selectedAuditDate}`, 'warning');
    } else {
      selector.innerHTML = '<option value="">No hay auditorías aún (sube un Excel)</option>';
    }
    clearView();
    return;
  }

  audits.forEach((a) => {
    const opt = document.createElement('option');
    opt.value = a.id;
    const dateFormatted = formatAuditDateLabel(a.audit_date || (a.uploaded_at ? a.uploaded_at.substring(0, 10) : ''));
    let uploadTime = '';
    if (a.uploaded_at && a.uploaded_at.includes(' ')) {
      uploadTime = a.uploaded_at.split(' ')[1].substring(0, 5);
    }
    const timeLabel = uploadTime ? ` [${uploadTime}]` : '';
    opt.textContent = `${dateFormatted ? dateFormatted + ' - ' : ''}${a.name}${timeLabel} (${a.total_items} prendas) #${a.id}`;
    selector.appendChild(opt);
  });

  // Determinar auditoría activa
  if (targetAuditId && audits.some(a => a.id === targetAuditId)) {
    currentAuditId = targetAuditId;
  } else if (!currentAuditId || !audits.some(a => a.id === currentAuditId)) {
    currentAuditId = audits[0].id;
  }
  
  selector.value = currentAuditId;
  loadAuditDetails(currentAuditId);
}

async function loadAuditDetails(auditId) {
  try {
    const res = await fetch(`/api/audits/${auditId}`);
    if (!res.ok) throw new Error('Error al cargar auditoría');
    const data = await res.json();
    
    allItems = (data.items || []).map(item => {
      if (!item.gender || !item.garment_type) {
        const decoded = decodeSevenSevenReference(item.reference, item.name);
        item.gender = item.gender || decoded.gender;
        item.garment_code = item.garment_code || decoded.garmentCode;
        item.garment_type = item.garment_type || decoded.garmentType || item.category || '';
      }
      return item;
    });

    sizeSummary = data.size_summary || [];
    populateCategories();
    populateSizes();
    renderSizeBreakdown();
    applyFilters();
    updateKPIs();
  } catch (err) {
    console.error(err);
    showToast('Error al cargar los detalles del inventario', 'error');
  }
}

function clearView() {
  allItems = [];
  filteredItems = [];
  sizeSummary = [];
  document.getElementById('cardsContainer').innerHTML = '';
  document.getElementById('tableBody').innerHTML = '';
  document.getElementById('emptyState').classList.remove('hidden');
  renderSizeBreakdown();
  updateKPIs();
  updateActiveFilterBadges();
}

// ============================================================================
// FILTROS, BÚSQUEDA, CATEGORÍAS Y TALLAS
// ============================================================================
function populateCategories() {
  const categoryFilter = document.getElementById('categoryFilter');
  if (!categoryFilter) return;

  // Filtrar items si hay un departamento/género activo para sugerir prendas relevantes
  const relevantItems = currentGender !== 'all' 
    ? allItems.filter(i => {
        const g = String(i.gender || '').trim().toLowerCase();
        const ref = String(i.reference || '').trim();
        const cleanDigits = ref.replace(/\D/g, '');
        if (currentGender === 'Dama') {
          return g === 'dama' || cleanDigits.startsWith('28') || ref.startsWith('28');
        }
        if (currentGender === 'Caballero') {
          return g === 'caballero' || g === 'hombre' || cleanDigits.startsWith('45') || ref.startsWith('45');
        }
        return g === currentGender.toLowerCase();
      })
    : allItems;

  // Mapa de tipo de prenda a su código (si existe) y conteo de referencias
  const catMap = new Map();
  relevantItems.forEach(i => {
    const type = (i.garment_type || i.category || '').trim();
    if (!type || type === '-' || type === 'General' || type === 'Otras Prendas') return;
    
    if (!catMap.has(type)) {
      catMap.set(type, {
        name: type,
        code: i.garment_code || '',
        count: 0
      });
    }
    catMap.get(type).count++;
  });

  categoryFilter.innerHTML = '<option value="all">Todas las prendas</option>';
  
  const sortedCategories = Array.from(catMap.values()).sort((a, b) => a.name.localeCompare(b.name));
  sortedCategories.forEach(cat => {
    const opt = document.createElement('option');
    opt.value = cat.name;
    const codeTag = cat.code ? ` (${cat.code})` : '';
    opt.textContent = `${cat.name}${codeTag} (${cat.count})`;
    categoryFilter.appendChild(opt);
  });

  // Si la categoría seleccionada previamente ya no existe en el género actual, resetear a 'all'
  if (currentCategory !== 'all' && !catMap.has(currentCategory)) {
    currentCategory = 'all';
  }
  categoryFilter.value = currentCategory;
}

function populateSizes() {
  const sizeSelect = document.getElementById('sizeFilter');
  if (!sizeSelect) return;
  sizeSelect.innerHTML = '<option value="all">Talla: Todas</option>';

  const orderMap = {'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, '28': 7, '30': 8, '32': 9, '34': 10, '36': 11};
  const rawSizes = Array.from(new Set(allItems.map(i => (i.size || '').trim()))).filter(Boolean);
  rawSizes.sort((a, b) => (orderMap[a.toUpperCase()] || 99) - (orderMap[b.toUpperCase()] || 99) || a.localeCompare(b));

  rawSizes.forEach(sz => {
    const opt = document.createElement('option');
    opt.value = sz;
    opt.textContent = `Talla ${sz}`;
    sizeSelect.appendChild(opt);
  });
  sizeSelect.value = currentSizeFilter;
}

function renderSizeBreakdown() {
  const container = document.getElementById('sizeBreakdownCards');
  const btnReset = document.getElementById('btnResetSizeFilter');
  if (!container) return;

  if (!sizeSummary || sizeSummary.length === 0) {
    container.innerHTML = '<span class="text-xs text-slate-400 italic py-1">No hay datos de tallas disponibles</span>';
    if (btnReset) btnReset.classList.add('hidden');
    return;
  }

  if (btnReset) {
    btnReset.classList.toggle('hidden', currentSizeFilter === 'all');
  }

  container.innerHTML = sizeSummary.map(item => {
    const sz = (item.size || '-').trim();
    const faltantes = item.faltante_units || 0;
    const sobrantes = item.sobrante_units || 0;
    const isSelected = currentSizeFilter.toUpperCase() === sz.toUpperCase();

    const activeClass = isSelected 
      ? 'border-blue-600 bg-blue-50/90 shadow-sm ring-2 ring-blue-500/40' 
      : 'border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50/80';

    return `
      <div class="size-pill cursor-pointer p-2 rounded-xl border text-center transition-all shrink-0 min-w-[110px] sm:min-w-[130px] ${activeClass}" onclick="selectSizeFilter('${sz}')" title="Filtrar prendas de Talla ${sz}">
        <div class="flex items-center justify-between gap-1 mb-1">
          <span class="text-xs font-black text-slate-900 bg-slate-100 px-2 py-0.5 rounded-md">Talla ${sz}</span>
          <span class="text-[10px] text-slate-400 font-bold">${item.total_refs} refs</span>
        </div>
        <div class="flex items-center justify-center gap-1.5 text-[11px] font-black">
          <span class="text-red-700 bg-red-50 px-1.5 py-0.5 rounded badge-pill">-${faltantes}</span>
          <span class="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded badge-pill">+${sobrantes}</span>
        </div>
      </div>
    `;
  }).join('');
}

function selectSizeFilter(size) {
  if (currentSizeFilter.toUpperCase() === size.toUpperCase()) {
    currentSizeFilter = 'all';
  } else {
    currentSizeFilter = size;
  }
  const sizeSelect = document.getElementById('sizeFilter');
  if (sizeSelect) sizeSelect.value = currentSizeFilter;
  renderSizeBreakdown();
  applyFilters();
}

function applyFilters() {
  const query = searchQuery.trim().toLowerCase();

  filteredItems = allItems.filter(item => {
    // 1. Filtro de Género / Departamento Oficial (28 Dama, 45 Caballero)
    if (currentGender !== 'all') {
      const g = String(item.gender || '').trim().toLowerCase();
      const ref = String(item.reference || '').trim();
      const cleanDigits = ref.replace(/\D/g, '');
      if (currentGender === 'Dama') {
        const isDama = g === 'dama' || cleanDigits.startsWith('28') || ref.startsWith('28');
        if (!isDama) return false;
      } else if (currentGender === 'Caballero') {
        const isCaballero = g === 'caballero' || g === 'hombre' || cleanDigits.startsWith('45') || ref.startsWith('45');
        if (!isCaballero) return false;
      } else if (g !== currentGender.toLowerCase()) {
        return false;
      }
    }

    // 2. Filtro de Tipo de Prenda / Categoría
    if (currentCategory !== 'all') {
      const type = (item.garment_type || '').toLowerCase();
      const cat = (item.category || '').toLowerCase();
      const code = (item.garment_code || '').toLowerCase();
      const target = currentCategory.toLowerCase();
      if (type !== target && cat !== target && code !== target) {
        return false;
      }
    }

    // 3. Filtro de Talla
    if (currentSizeFilter !== 'all' && (item.size || '').trim().toUpperCase() !== currentSizeFilter.toUpperCase()) {
      return false;
    }

    // 4. Filtro de Estado / Diferencia
    if (currentFilter === 'faltantes' && item.difference >= 0) return false;
    if (currentFilter === 'sobrantes' && item.difference <= 0) return false;
    if (currentFilter === 'reincidentes' && !item.is_recurrent) return false;
    if (currentFilter === 'pendientes' && item.status === 'validada') return false;
    if (currentFilter === 'validadas' && item.status !== 'validada') return false;
    if (currentFilter === 'sin_foto' && item.photo_url) return false;

    // 5. Búsqueda de Texto
    if (query) {
      const matchRef = (item.reference || '').toLowerCase().includes(query);
      const matchBarcode = (item.barcode || '').toLowerCase().includes(query);
      const matchName = (item.name || '').toLowerCase().includes(query);
      const matchColor = (item.color || '').toLowerCase().includes(query);
      const matchSize = (item.size || '').toLowerCase().includes(query);
      const matchType = (item.garment_type || '').toLowerCase().includes(query);
      const matchCat = (item.category || '').toLowerCase().includes(query);
      if (!matchRef && !matchBarcode && !matchName && !matchColor && !matchSize && !matchType && !matchCat) {
        return false;
      }
    }

    return true;
  });

  renderItems();
  updateFilterCounts();
  updateActiveFilterBadges();
}

function updateFilterCounts() {
  const setEl = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  setEl('countFilterAll', allItems.length);
  setEl('countFilterFaltantes', allItems.filter(i => i.difference < 0).length);
  setEl('countFilterSobrantes', allItems.filter(i => i.difference > 0).length);
  setEl('countFilterReincidentes', allItems.filter(i => i.is_recurrent).length);
  setEl('countFilterPendientes', allItems.filter(i => i.status !== 'validada').length);
  setEl('countFilterValidadas', allItems.filter(i => i.status === 'validada').length);
  setEl('countFilterSinFoto', allItems.filter(i => !i.photo_url).length);

  setEl('visibleCount', filteredItems.length);
  setEl('totalAuditCount', allItems.length);
}

function toggleFilterDrawer(forceState = null) {
  const drawer = document.getElementById('filterDrawer');
  const btnToggle = document.getElementById('btnToggleFilters');
  if (!drawer) return;

  const isCurrentlyOpen = !drawer.classList.contains('hidden');
  const shouldOpen = forceState !== null ? forceState : !isCurrentlyOpen;

  if (shouldOpen) {
    drawer.classList.remove('hidden');
    const input = document.getElementById('searchInput');
    if (input) {
      setTimeout(() => {
        input.focus();
        input.select();
      }, 50);
    }
  } else {
    drawer.classList.add('hidden');
  }

  updateActiveFilterBadges();
  initIcons();
}

function clearAllFilters() {
  searchQuery = '';
  const searchInput = document.getElementById('searchInput');
  if (searchInput) searchInput.value = '';
  const btnClearSearch = document.getElementById('btnClearSearch');
  if (btnClearSearch) btnClearSearch.classList.add('hidden');

  currentGender = 'all';
  const genderFilter = document.getElementById('genderFilter');
  if (genderFilter) genderFilter.value = 'all';

  currentCategory = 'all';
  const categoryFilter = document.getElementById('categoryFilter');
  if (categoryFilter) categoryFilter.value = 'all';

  currentSizeFilter = 'all';
  const sizeFilter = document.getElementById('sizeFilter');
  if (sizeFilter) sizeFilter.value = 'all';

  currentFilter = 'all';
  const statusFilter = document.getElementById('statusFilter');
  if (statusFilter) statusFilter.value = 'all';

  populateCategories();
  renderSizeBreakdown();
  applyFilters();
  showToast('Filtros restablecidos', 'info');
}

function removeSpecificFilter(type) {
  if (type === 'search') {
    searchQuery = '';
    const input = document.getElementById('searchInput');
    if (input) input.value = '';
    const btnClearSearch = document.getElementById('btnClearSearch');
    if (btnClearSearch) btnClearSearch.classList.add('hidden');
  } else if (type === 'gender') {
    currentGender = 'all';
    const gf = document.getElementById('genderFilter');
    if (gf) gf.value = 'all';
    populateCategories();
  } else if (type === 'category') {
    currentCategory = 'all';
    const cat = document.getElementById('categoryFilter');
    if (cat) cat.value = 'all';
  } else if (type === 'size') {
    currentSizeFilter = 'all';
    const sz = document.getElementById('sizeFilter');
    if (sz) sz.value = 'all';
    renderSizeBreakdown();
  } else if (type === 'status') {
    currentFilter = 'all';
    const sf = document.getElementById('statusFilter');
    if (sf) sf.value = 'all';
  }
  applyFilters();
}

function updateActiveFilterBadges() {
  const activeFiltersPill = document.getElementById('activeFiltersPill');
  const activeDrawerBadge = document.getElementById('activeFilterDrawerBadge');
  const btnToggle = document.getElementById('btnToggleFilters');
  const summaryBar = document.getElementById('activeFiltersSummaryBar');
  const btnQuickClear = document.getElementById('btnQuickClearFilters');

  let activeCount = 0;
  const activeTags = [];

  if (searchQuery.trim()) {
    activeCount++;
    activeTags.push({
      label: `"${searchQuery.trim()}"`,
      type: 'search'
    });
  }

  if (currentGender !== 'all') {
    activeCount++;
    const genderLabels = {
      'Dama': '👗 Dama (28)',
      'Caballero': '👔 Caballero (45)'
    };
    activeTags.push({
      label: genderLabels[currentGender] || currentGender,
      type: 'gender'
    });
  }

  if (currentCategory !== 'all') {
    activeCount++;
    activeTags.push({
      label: currentCategory,
      type: 'category'
    });
  }

  if (currentSizeFilter !== 'all') {
    activeCount++;
    activeTags.push({
      label: `Talla ${currentSizeFilter}`,
      type: 'size'
    });
  }

  if (currentFilter !== 'all') {
    activeCount++;
    const filterLabels = {
      'faltantes': '🔴 Faltantes',
      'sobrantes': '🟢 Sobrantes',
      'reincidentes': '🔥 Repetidas en otros inventarios',
      'pendientes': '⏳ Pendientes',
      'validadas': '✅ Validadas',
      'sin_foto': '📷 Sin Foto'
    };
    activeTags.push({
      label: filterLabels[currentFilter] || currentFilter,
      type: 'status'
    });
  }

  // Actualizar pill en botón de lupa
  if (activeFiltersPill) {
    if (activeCount > 0) {
      activeFiltersPill.textContent = activeCount;
      activeFiltersPill.classList.remove('hidden');
    } else {
      activeFiltersPill.classList.add('hidden');
    }
  }

  // Actualizar badge en panel desplegable
  if (activeDrawerBadge) {
    if (activeCount > 0) {
      activeDrawerBadge.textContent = `${activeCount} activos`;
      activeDrawerBadge.classList.remove('hidden');
    } else {
      activeDrawerBadge.classList.add('hidden');
    }
  }

  // Botón Limpiar Rápido junto al contador
  if (btnQuickClear) {
    btnQuickClear.classList.toggle('hidden', activeCount === 0);
  }

  // Estilo visual del botón de la lupa
  if (btnToggle) {
    const drawer = document.getElementById('filterDrawer');
    const isOpen = drawer && !drawer.classList.contains('hidden');
    if (isOpen) {
      btnToggle.className = 'relative inline-flex items-center justify-center p-2 sm:px-3 sm:py-1.5 rounded-lg bg-blue-50 border border-blue-500 text-blue-700 shadow-xs transition-all cursor-pointer touch-target group ring-2 ring-blue-500/20';
    } else if (activeCount > 0) {
      btnToggle.className = 'relative inline-flex items-center justify-center p-2 sm:px-3 sm:py-1.5 rounded-lg bg-blue-50/80 border border-blue-400 text-blue-800 shadow-xs transition-all cursor-pointer touch-target group';
    } else {
      btnToggle.className = 'relative inline-flex items-center justify-center p-2 sm:px-3 sm:py-1.5 rounded-lg bg-white border border-slate-300 hover:border-blue-500 hover:text-blue-600 text-slate-700 shadow-2xs hover:shadow-xs transition-all cursor-pointer touch-target group';
    }
  }

  // Barra de resumen de filtros activos (visibles sin abrir el panel)
  if (summaryBar) {
    const drawer = document.getElementById('filterDrawer');
    const isOpen = drawer && !drawer.classList.contains('hidden');

    if (activeCount > 0 && !isOpen) {
      summaryBar.innerHTML = activeTags.map(tag => `
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-[11px] font-semibold border border-slate-200">
          <span>${tag.label}</span>
          <button type="button" class="text-slate-400 hover:text-red-500 ml-0.5" onclick="removeSpecificFilter('${tag.type}')" title="Quitar este filtro">
            ×
          </button>
        </span>
      `).join('');
      summaryBar.classList.remove('hidden');
    } else {
      summaryBar.innerHTML = '';
      summaryBar.classList.add('hidden');
    }
  }
}

function updateKPIs() {
  const total = allItems.length;
  const faltantes = allItems.filter(i => i.difference < 0);
  const sobrantes = allItems.filter(i => i.difference > 0);
  const reincidentes = allItems.filter(i => i.is_recurrent);
  const validadas = allItems.filter(i => i.status === 'validada');
  const conFoto = allItems.filter(i => i.photo_url);

  const unitsFaltantes = faltantes.reduce((sum, i) => sum + Math.abs(i.difference || 0), 0);
  const unitsSobrantes = sobrantes.reduce((sum, i) => sum + Math.abs(i.difference || 0), 0);

  document.getElementById('kpiTotal').textContent = total;
  document.getElementById('kpiFaltantes').textContent = faltantes.length;
  document.getElementById('kpiFaltantesUnits').textContent = `-${unitsFaltantes} unids`;
  document.getElementById('kpiSobrantes').textContent = sobrantes.length;
  document.getElementById('kpiSobrantesUnits').textContent = `+${unitsSobrantes} unids`;
  document.getElementById('kpiReincidentes').textContent = reincidentes.length;
  
  document.getElementById('kpiValidadasCount').textContent = validadas.length;
  document.getElementById('kpiValidadasTotal').textContent = `/ ${total}`;
  const pct = total > 0 ? Math.round((validadas.length / total) * 100) : 0;
  document.getElementById('kpiValidadasPercent').textContent = `${pct}%`;
  document.getElementById('progressBar').style.width = `${pct}%`;

  document.getElementById('kpiConFoto').textContent = conFoto.length;
  document.getElementById('kpiSinFoto').textContent = `${total - conFoto.length} sin foto`;
}

// ============================================================================
// RENDERIZADO DE PRENDAS (TARJETAS & TABLA)
// ============================================================================
function renderItems() {
  const cardsContainer = document.getElementById('cardsContainer');
  const tableBody = document.getElementById('tableBody');
  const emptyState = document.getElementById('emptyState');

  if (filteredItems.length === 0) {
    cardsContainer.innerHTML = '';
    tableBody.innerHTML = '';
    emptyState.classList.remove('hidden');
    return;
  }

  emptyState.classList.add('hidden');

  if (viewMode === 'cards') {
    renderCards(cardsContainer);
  } else {
    renderTable(tableBody);
  }

  initIcons();
}

function renderCards(container) {
  container.innerHTML = '';

  filteredItems.forEach((item, index) => {
    const card = document.createElement('div');
    card.className = 'interactive-card bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs cursor-pointer flex flex-col justify-between';
    card.onclick = () => openInspector(index);

    const diff = item.difference || 0;
    const isFaltante = diff < 0;
    const isSobrante = diff > 0;
    const isValidated = item.status === 'validada';
    const hasPhoto = Boolean(item.photo_url);

    // Badges de diferencia con indicación explícita de Talla
    let diffBadge = '';
    const sizeLabel = (item.size || '-').trim();
    if (isFaltante) {
      diffBadge = `<span class="px-2 py-0.5 rounded-md bg-red-100 text-red-900 font-black text-xs inline-flex items-center gap-1 border border-red-200 badge-pill">
                    <i data-lucide="arrow-down-right" class="w-3.5 h-3.5 text-red-600 shrink-0"></i> Faltan ${Math.abs(diff)} en ${sizeLabel}
                   </span>`;
    } else if (isSobrante) {
      diffBadge = `<span class="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-900 font-black text-xs inline-flex items-center gap-1 border border-emerald-200 badge-pill">
                    <i data-lucide="arrow-up-right" class="w-3.5 h-3.5 text-emerald-600 shrink-0"></i> Sobran ${diff} en ${sizeLabel}
                   </span>`;
    } else {
      diffBadge = `<span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-bold text-xs inline-flex items-center badge-pill">Talla ${sizeLabel}: Exacto</span>`;
    }

    // Badge de Reincidencia: Solo el emoji del fuego
    let recurrentBadge = '';
    if (item.is_recurrent) {
      recurrentBadge = `<span class="px-1.5 py-0.5 rounded-md bg-amber-100 text-amber-900 font-bold text-xs border border-amber-200/80 inline-flex items-center justify-center cursor-pointer shadow-2xs badge-pill" title="Prenda repetida en otros inventarios. Haz clic para ver las fechas.">🔥</span>`;
    }

    // Badge de Foto
    let photoBadge = '';
    if (!hasPhoto) {
      photoBadge = `<span class="px-1.5 py-0.5 rounded bg-red-50 text-red-600 text-[10px] font-bold border border-red-200 inline-flex items-center gap-1 badge-pill">
                      <i data-lucide="camera-off" class="w-2.5 h-2.5 shrink-0"></i> Sin foto
                    </span>`;
    }

    // Badge de Validación
    let statusBadge = '';
    if (isValidated) {
      statusBadge = `<span class="px-2 py-0.5 rounded-md bg-blue-100 text-blue-800 font-bold text-[10px] inline-flex items-center gap-1 badge-pill">
                       <i data-lucide="check" class="w-3 h-3 shrink-0"></i> Validada
                     </span>`;
    } else {
      statusBadge = `<span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 font-semibold text-[10px] inline-flex items-center badge-pill">
                       Pendiente
                     </span>`;
    }

    card.innerHTML = `
      <div class="p-2.5 sm:p-3.5 flex flex-col gap-2 sm:gap-2.5">
        <!-- Fila Superior: Badges con Talla y Cantidad -->
        <div class="flex items-center justify-between gap-1 flex-wrap">
          <div class="flex items-center gap-1 flex-wrap">
            ${diffBadge}
            ${recurrentBadge}
          </div>
          <div class="flex items-center gap-1">
            ${photoBadge}
            ${statusBadge}
          </div>
        </div>

        <!-- Ficha Prenda con Miniatura -->
        <div class="flex items-start gap-2.5 sm:gap-3 mt-0.5 sm:mt-1">
          <div class="w-12 h-14 sm:w-14 sm:h-16 rounded-lg bg-slate-100 border border-slate-200 shrink-0 overflow-hidden flex items-center justify-center relative">
            ${hasPhoto 
              ? `<img src="${item.photo_url}" alt="${item.reference}" class="w-full h-full object-cover">` 
              : `<div class="text-slate-400 text-center p-1"><i data-lucide="image" class="w-5 h-5 mx-auto"></i><span class="text-[8px] font-bold block mt-0.5 text-amber-600">Sin foto</span></div>`}
          </div>

          <div class="flex-1 min-w-0">
            <span class="text-[11px] font-mono font-black text-slate-900 block truncate">
              ${item.reference}
            </span>
            <h4 class="text-xs font-bold text-slate-700 leading-tight line-clamp-2 mt-0.5" title="${item.name}">
              ${item.name}
            </h4>
            <div class="flex items-center gap-2 mt-1.5 text-[11px]">
              <span class="font-black text-blue-900 bg-blue-100 px-2 py-0.5 rounded badge-pill">Talla: ${item.size}</span>
              <span class="text-slate-500 truncate">Color: ${item.color}</span>
            </div>
          </div>
        </div>

        <!-- Conteo Resumido -->
        <div class="grid grid-cols-3 gap-1 bg-slate-50 p-2 rounded-lg border border-slate-200/80 text-center text-[10px] mt-1">
          <div>
            <span class="text-slate-400 block font-medium">Tienda</span>
            <span class="font-black text-slate-800 text-xs">${item.store_count}</span>
          </div>
          <div>
            <span class="text-slate-400 block font-medium">Bodega</span>
            <span class="font-black text-slate-800 text-xs">${item.warehouse_count}</span>
          </div>
          <div>
            <span class="text-slate-400 block font-medium">Teórico</span>
            <span class="font-black text-slate-800 text-xs">${item.theoretical_count}</span>
          </div>
        </div>

        ${isValidated && item.validation_verdict ? `
          <div class="text-[10px] text-blue-900 bg-blue-50/80 p-1.5 rounded border border-blue-200 truncate">
            <strong>Dictamen:</strong> ${item.validation_verdict}
          </div>
        ` : ''}
      </div>
    `;

    container.appendChild(card);
  });
}

function renderTable(tbody) {
  tbody.innerHTML = '';

  filteredItems.forEach((item, index) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-blue-50/50 cursor-pointer transition-colors group';
    tr.onclick = () => openInspector(index);

    const diff = item.difference || 0;
    let diffClass = 'text-slate-700 font-bold';
    let diffText = `${diff}`;
    if (diff < 0) {
      diffClass = 'text-red-700 bg-red-100 px-2 py-0.5 rounded-md font-black badge-pill';
      diffText = `-${Math.abs(diff)}`;
    } else if (diff > 0) {
      diffClass = 'text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-md font-black badge-pill';
      diffText = `+${diff}`;
    }

    const barcodeStr = (item.barcode && item.barcode !== '-' && item.barcode !== '0') ? item.barcode : '';

    const isDama = item.gender === 'Dama' || (item.reference && item.reference.startsWith('28'));
    const isCaballero = item.gender === 'Caballero' || (item.reference && item.reference.startsWith('45'));

    const genderTag = isDama
      ? `<span class="text-[9px] font-bold text-pink-700 bg-pink-50 border border-pink-200/90 px-1.5 py-0.5 rounded leading-none badge-pill">Dama</span>`
      : (isCaballero
        ? `<span class="text-[9px] font-bold text-blue-700 bg-blue-50 border border-blue-200/90 px-1.5 py-0.5 rounded leading-none badge-pill">Hombre</span>`
        : '');

    const garmentTypeTag = item.garment_type
      ? `<span class="text-[10px] text-slate-500 font-medium truncate max-w-[125px] inline-block">· ${item.garment_type}</span>`
      : '';

    tr.innerHTML = `
      <td class="py-2.5 px-3">
        <div class="flex flex-col">
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="font-mono font-black text-slate-900 text-xs sm:text-[13px] group-hover:text-blue-600 transition-colors">${item.reference}</span>
            ${genderTag}
          </div>
          <div class="flex items-center gap-1 text-[10px] text-slate-400 leading-tight mt-0.5">
            ${barcodeStr ? `<span class="font-mono">${barcodeStr}</span>` : ''}
            ${garmentTypeTag}
          </div>
        </div>
      </td>
      <td class="py-2.5 px-2 text-center">
        <span class="font-black text-blue-900 bg-blue-100 px-2 py-0.5 rounded text-xs badge-pill">${item.size || '-'}</span>
      </td>
      <td class="py-2.5 px-2 text-center text-slate-700 font-semibold text-xs">${item.color || '-'}</td>
      <td class="py-2.5 px-2 text-right font-medium text-slate-600 text-xs">${item.theoretical_count}</td>
      <td class="py-2.5 px-2 text-right font-bold text-slate-800 text-xs">${item.store_count}</td>
      <td class="py-2.5 px-2 text-right font-bold text-slate-800 text-xs">${item.warehouse_count}</td>
      <td class="py-2.5 px-2 text-center">
        <span class="${diffClass}">${diffText}</span>
      </td>
      <td class="py-2.5 px-2 text-center">
        ${item.is_recurrent ? `<span class="inline-block text-base leading-none cursor-pointer hover:scale-125 transition-transform" title="Prenda repetida en otros inventarios. Haz clic en la fila para ver las fechas.">🔥</span>` : `<span class="text-slate-300 text-xs font-semibold">-</span>`}
      </td>
      <td class="py-2.5 px-3 text-center">
        ${item.status === 'validada' 
          ? `<span class="text-blue-700 font-bold text-[11px] inline-flex items-center gap-1 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-200/60 badge-pill"><i data-lucide="check" class="w-3 h-3 shrink-0"></i> ${item.validation_verdict || 'Validada'}</span>`
          : `<span class="text-slate-400 text-[11px] bg-slate-50 px-2 py-0.5 rounded-md border border-slate-200/60 badge-pill">Pendiente</span>`}
      </td>
    `;

    tbody.appendChild(tr);
  });
}

// ============================================================================
// INSPECTOR EN PANTALLA COMPLETA & OBLIGATORIEDAD DE FOTO
// ============================================================================
function openInspector(index) {
  if (index < 0 || index >= filteredItems.length) return;
  currentItemIndex = index;
  const item = filteredItems[currentItemIndex];

  // Actualizar Contador Navegación
  document.getElementById('modalNavCounter').textContent = `${currentItemIndex + 1} / ${filteredItems.length}`;
  document.getElementById('btnModalPrev').disabled = currentItemIndex === 0;
  document.getElementById('btnModalNext').disabled = currentItemIndex === filteredItems.length - 1;

  // Header & Detalles
  document.getElementById('modalRefTitle').textContent = item.reference;

  // Badge de Género / Departamento Oficial
  const isDama = item.gender === 'Dama' || (item.reference && item.reference.startsWith('28'));
  const isCaballero = item.gender === 'Caballero' || (item.reference && item.reference.startsWith('45'));
  const genderBadge = document.getElementById('modalGenderBadge');
  if (genderBadge) {
    if (isDama) {
      genderBadge.className = 'text-[10px] sm:text-[11px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-pink-500/20 text-pink-300 border border-pink-400/30 shrink-0';
      genderBadge.textContent = '👗 Dama (28)';
      genderBadge.classList.remove('hidden');
    } else if (isCaballero) {
      genderBadge.className = 'text-[10px] sm:text-[11px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30 shrink-0';
      genderBadge.textContent = '👔 Caballero (45)';
      genderBadge.classList.remove('hidden');
    } else {
      genderBadge.classList.add('hidden');
    }
  }

  // Badge de Categoría / Tipo de Prenda
  const catBadgeText = item.garment_type 
    ? `${item.garment_type}${item.garment_code ? ' · Cód. ' + item.garment_code : ''}`
    : (item.category || 'General');
  document.getElementById('modalCategoryBadge').textContent = catBadgeText;
  document.getElementById('modalGarmentName').textContent = item.name;
  document.getElementById('modalSize').textContent = item.size;
  document.getElementById('modalColor').textContent = item.color;
  document.getElementById('modalBarcode').textContent = item.barcode || '-';

  // Código de barras visual escaneable (EAN-13 / 128)
  renderBarcodeSvg(item.barcode);

  // Conteos
  document.getElementById('modalCountStore').textContent = item.store_count;
  document.getElementById('modalCountWarehouse').textContent = item.warehouse_count;
  const totalPhysical = (item.store_count || 0) + (item.warehouse_count || 0);
  document.getElementById('modalCountTotalPhysical').textContent = totalPhysical;
  document.getElementById('modalCountTheoretical').textContent = item.theoretical_count;

  // Banner Diferencia destacando la talla específica
  const diff = item.difference || 0;
  const sizeLabel = (item.size || '-').trim();
  const diffBanner = document.getElementById('modalDiffBanner');
  const diffIcon = document.getElementById('modalDiffIcon');
  const diffLabel = document.getElementById('modalDiffLabel');
  const diffVal = document.getElementById('modalDiffValue');
  const diffExpl = document.getElementById('modalDiffExplanation');

  if (diff < 0) {
    diffBanner.className = 'p-2.5 sm:p-3 rounded-xl border flex items-center justify-between bg-red-50 border-red-200 text-red-900 transition-all';
    diffIcon.className = 'w-7 h-7 rounded-full flex items-center justify-center font-black text-xs shrink-0 bg-red-200 text-red-800';
    diffIcon.innerHTML = '↓';
    diffLabel.textContent = `Faltante (${sizeLabel})`;
    diffVal.textContent = `-${Math.abs(diff)}`;
    if (diffExpl) diffExpl.textContent = `Físico menor que teórico`;
  } else if (diff > 0) {
    diffBanner.className = 'p-2.5 sm:p-3 rounded-xl border flex items-center justify-between bg-emerald-50 border-emerald-200 text-emerald-900 transition-all';
    diffIcon.className = 'w-7 h-7 rounded-full flex items-center justify-center font-black text-xs shrink-0 bg-emerald-200 text-emerald-800';
    diffIcon.innerHTML = '↑';
    diffLabel.textContent = `Sobrante (${sizeLabel})`;
    diffVal.textContent = `+${diff}`;
    if (diffExpl) diffExpl.textContent = `Físico supera teórico`;
  } else {
    diffBanner.className = 'p-2.5 sm:p-3 rounded-xl border flex items-center justify-between bg-slate-50 border-slate-200 text-slate-800 transition-all';
    diffIcon.className = 'w-7 h-7 rounded-full flex items-center justify-center font-black text-xs shrink-0 bg-slate-200 text-slate-700';
    diffIcon.innerHTML = '=';
    diffLabel.textContent = `Exacto (${sizeLabel})`;
    diffVal.textContent = '0';
    if (diffExpl) diffExpl.textContent = `Conteo coincide`;
  }

  // Desglose Unificado de Diferencias de todas las tallas del modelo
  renderUnifiedDifferences(item);

  // Foto y Gestión de Obligatoriedad
  updatePhotoUI(item.photo_url);

  // Historial de Reincidencia
  renderRecurrenceHistory(item);

  // Formulario de Validación Adaptativo según la diferencia (+, -, 0)
  currentSelectedVerdict = item.validation_verdict || '';
  renderVerdictOptions(item);
  document.getElementById('validationNotes').value = item.validation_notes || '';
  
  const statusBadge = document.getElementById('modalStatusBadge');
  if (item.status === 'validada') {
    statusBadge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800';
    statusBadge.textContent = 'Validada';
  } else {
    statusBadge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600';
    statusBadge.textContent = 'Pendiente';
  }

  // Mostrar Modal
  document.getElementById('inspectorModal').classList.remove('hidden');
  initIcons();
}

function renderBarcodeSvg(code) {
  const svgEl = document.getElementById('modalBarcodeSvg');
  const cardEl = document.getElementById('modalBarcodeCard');
  if (!svgEl || !cardEl) return;

  const cleanCode = code ? String(code).trim() : '';
  if (!cleanCode || cleanCode === '-' || cleanCode === '0') {
    cardEl.classList.add('hidden');
    return;
  }

  cardEl.classList.remove('hidden');

  try {
    if (window.JsBarcode) {
      let format = 'CODE128';
      if (/^\d{13}$/.test(cleanCode)) {
        format = 'EAN13';
      } else if (/^\d{8}$/.test(cleanCode)) {
        format = 'EAN8';
      }

      window.JsBarcode(svgEl, cleanCode, {
        format: format,
        width: 1.6,
        height: 36,
        displayValue: true,
        fontSize: 10,
        font: 'monospace',
        textMargin: 1,
        margin: 2,
        background: '#ffffff',
        lineColor: '#0f172a'
      });
    }
  } catch (err) {
    try {
      window.JsBarcode(svgEl, cleanCode, {
        format: 'CODE128',
        width: 1.5,
        height: 36,
        displayValue: true,
        fontSize: 10,
        font: 'monospace',
        margin: 2
      });
    } catch (e2) {
      console.warn('No se pudo renderizar código de barras visual:', e2);
      cardEl.classList.add('hidden');
    }
  }
}

function updatePhotoUI(photoUrl) {
  const imgElem = document.getElementById('modalGarmentImage');
  const placeholder = document.getElementById('modalNoImagePlaceholder');
  const mandatoryAlert = document.getElementById('mandatoryPhotoAlert');
  const photoActions = document.getElementById('modalPhotoActions');
  const btnChange = document.getElementById('btnTriggerPhotoChange');

  if (photoUrl) {
    imgElem.src = photoUrl;
    imgElem.classList.remove('hidden');
    placeholder.classList.add('hidden');
    mandatoryAlert.classList.add('hidden');
    if (photoActions) photoActions.classList.remove('hidden');
    if (btnChange) btnChange.classList.remove('hidden');
  } else {
    imgElem.src = '';
    imgElem.classList.add('hidden');
    placeholder.classList.remove('hidden');
    mandatoryAlert.classList.remove('hidden');
    if (photoActions) photoActions.classList.add('hidden');
    if (btnChange) btnChange.classList.add('hidden');
  }
}

async function handleDeleteModalPhoto() {
  const item = filteredItems[currentItemIndex];
  if (!item || !item.photo_url) return;

  const confirmDelete = confirm(`¿Estás seguro de eliminar la foto de la referencia ${item.reference}?`);
  if (!confirmDelete) return;

  try {
    const res = await fetch(`/api/items/${item.id}/photo`, {
      method: 'DELETE'
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Error al eliminar la foto');
    }

    // Limpiar photo_url en el item actual
    item.photo_url = null;

    // Limpiar en todas las prendas de la auditoría que compartan la misma referencia o base_ref
    const targetRef = item.reference;
    const targetBase = item.base_reference;
    allItems.forEach(i => {
      if (i.reference === targetRef || (targetBase && i.base_reference === targetBase)) {
        i.photo_url = null;
        if (i.sibling_sizes) {
          i.sibling_sizes.forEach(sib => { sib.photo_url = null; });
        }
      }
    });

    if (item.sibling_sizes) {
      item.sibling_sizes.forEach(sib => { sib.photo_url = null; });
    }

    // Actualizar UI
    updatePhotoUI(null);
    renderItems();
    updateKpis();
    if (typeof loadCatalogStats === 'function') {
      loadCatalogStats();
    }

    showToast('Foto eliminada correctamente del catálogo', 'info');
  } catch (err) {
    console.error('Error al eliminar foto:', err);
    showToast(`No se pudo eliminar la foto: ${err.message}`, 'error');
  }
}


let currentAuditGroups = [];
let isRecurrenceExpanded = false;

function formatAuditDateCompact(dateStr, uploadedAt) {
  if (!dateStr && uploadedAt) {
    dateStr = uploadedAt.substring(0, 10);
  }
  if (!dateStr) return 'Sin fecha';
  
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const d = new Date(year, month, day);
      const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
      const dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
      const diaTxt = !isNaN(d.getDay()) ? dias[d.getDay()] : '';
      return `${diaTxt} ${day} ${meses[month]} ${year}`;
    }
  } catch (e) {}
  return dateStr;
}

function buildCompactRecurrenceRow(group, currentSize) {
  const shortDate = formatAuditDateCompact(group.audit_date, group.uploaded_at);
  const curSize = (currentSize || '').trim().toUpperCase();

  // Buscar registro de la talla actual de la prenda
  const currentRec = group.records.find(r => (r.size || '').trim().toUpperCase() === curSize);
  const otherRecs = group.records.filter(r => (r.size || '').trim().toUpperCase() !== curSize);

  let diffBadgeHtml = '';
  if (currentRec) {
    const diff = currentRec.difference || 0;
    if (diff < 0) {
      diffBadgeHtml = `<span class="px-2 py-0.5 rounded text-[11px] font-black bg-red-100 text-red-800 border border-red-200 shrink-0">Faltó ${Math.abs(diff)} en ${currentRec.size}</span>`;
    } else if (diff > 0) {
      diffBadgeHtml = `<span class="px-2 py-0.5 rounded text-[11px] font-black bg-emerald-100 text-emerald-800 border border-emerald-200 shrink-0">Sobró +${diff} en ${currentRec.size}</span>`;
    } else {
      diffBadgeHtml = `<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200 shrink-0 badge-pill">Exacto en ${currentRec.size}</span>`;
    }
  } else if (group.records.length > 0) {
    const totalDiff = group.records.reduce((acc, r) => acc + (r.difference || 0), 0);
    const sign = totalDiff > 0 ? `+${totalDiff}` : `${totalDiff}`;
    const diffClass = totalDiff < 0 ? 'bg-red-100 text-red-800 border-red-200' : (totalDiff > 0 ? 'bg-emerald-100 text-emerald-800 border-emerald-200' : 'bg-slate-100 text-slate-700 border-slate-200');
    diffBadgeHtml = `<span class="px-2 py-0.5 rounded text-[11px] font-bold ${diffClass} border shrink-0 badge-pill">Descuadre ${sign} (${group.records.map(r => r.size).join(', ')})</span>`;
  }

  // Si hay más tallas con diferencia en esa misma fecha
  let otherPillHtml = '';
  if (currentRec && otherRecs.length > 0) {
    const details = otherRecs.map(r => `${r.size}: ${r.difference > 0 ? '+' : ''}${r.difference}`).join(' · ');
    otherPillHtml = `<span class="text-[10px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 truncate hidden xs:inline badge-pill" title="${details}">+${otherRecs.length} ${otherRecs.length === 1 ? 'talla' : 'tallas'}</span>`;
  }

  // Si hay dictamen o notas previas
  const noteRec = group.records.find(r => r.validation_verdict || r.validation_notes);
  const noteHtml = noteRec ? `
    <div class="text-[10px] text-slate-500 flex items-center gap-1 pl-6 pt-0.5 pb-1 truncate italic">
      <i data-lucide="message-square" class="w-2.5 h-2.5 text-slate-400 shrink-0"></i>
      <span>${[noteRec.validation_verdict, noteRec.validation_notes].filter(Boolean).join(' · ')}</span>
    </div>
  ` : '';

  return `
    <div class="px-2.5 py-2 hover:bg-amber-50/40 transition-colors">
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-1.5 min-w-0">
          <span class="text-xs font-black text-slate-800 shrink-0 inline-flex items-center gap-1 font-mono">
            <i data-lucide="calendar" class="w-3 h-3 text-amber-600 shrink-0"></i>
            <span>${shortDate}</span>
          </span>
          <span class="text-[11px] text-slate-400 truncate max-w-[130px] sm:max-w-[220px]" title="${group.audit_name}">
            · ${group.audit_name}
          </span>
        </div>
        <div class="flex items-center gap-1.5 shrink-0">
          ${diffBadgeHtml}
          ${otherPillHtml}
        </div>
      </div>
      ${noteHtml}
    </div>
  `;
}

function renderRecurrenceHistory(item) {
  const topSection = document.getElementById('recurrenceSection');
  const detailedCard = document.getElementById('recurrenceDetailedCard');
  const totalAuditsBadge = document.getElementById('recurrenceTotalAuditsBadge');
  const lastDateBadge = document.getElementById('recurrenceLastDateBadge');
  const datesList = document.getElementById('recurrenceDatesList');
  const btnScroll = document.getElementById('btnScrollToRecurrence');
  const btnToggle = document.getElementById('btnToggleAllRecurrences');
  const btnToggleText = document.getElementById('btnToggleAllRecurrencesText');
  const btnToggleIcon = document.getElementById('btnToggleAllRecurrencesIcon');

  const history = item.history || [];

  if (history.length === 0) {
    if (topSection) topSection.classList.add('hidden');
    if (detailedCard) detailedCard.classList.add('hidden');
    if (datesList) datesList.innerHTML = '';
    return;
  }

  // Agrupar historial por auditoría para presentar claramente cada fecha
  const groups = {};
  history.forEach(h => {
    const key = h.audit_id || h.audit_name || 'prev';
    if (!groups[key]) {
      groups[key] = {
        audit_id: h.audit_id,
        audit_name: h.audit_name,
        audit_date: h.audit_date,
        uploaded_at: h.uploaded_at,
        records: []
      };
    }
    groups[key].records.push(h);
  });

  currentAuditGroups = Object.values(groups);
  isRecurrenceExpanded = false;
  const totalAudits = currentAuditGroups.length;

  // 1. Cabecera del modal (botón scroll suave)
  if (topSection) {
    topSection.classList.remove('hidden');
    if (btnScroll) {
      btnScroll.onclick = () => {
        if (detailedCard) {
          detailedCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
          detailedCard.classList.add('ring-2', 'ring-amber-400', 'bg-amber-100/80');
          setTimeout(() => {
            detailedCard.classList.remove('ring-2', 'ring-amber-400', 'bg-amber-100/80');
          }, 1500);
        }
      };
    }
  }

  // 2. Tarjeta detallada compacta en el cuerpo
  if (detailedCard) {
    detailedCard.classList.remove('hidden');
  }

  if (totalAuditsBadge) {
    totalAuditsBadge.textContent = `${totalAudits} ${totalAudits === 1 ? 'inventario anterior' : 'inventarios anteriores'}`;
  }

  if (lastDateBadge && currentAuditGroups.length > 0) {
    const latestDate = formatAuditDateCompact(currentAuditGroups[0].audit_date, currentAuditGroups[0].uploaded_at);
    lastDateBadge.textContent = `Última: ${latestDate}`;
  }

  // Función interna para renderizar las filas (3 o todas)
  function updateRecurrenceList() {
    if (!datesList) return;

    const rowsToShow = isRecurrenceExpanded ? currentAuditGroups : currentAuditGroups.slice(0, 3);
    
    // Si está expandido y son muchos, limitamos la altura con scroll para no deformar el modal
    if (isRecurrenceExpanded && currentAuditGroups.length > 5) {
      datesList.className = 'bg-white rounded-lg border border-amber-200/80 divide-y divide-slate-100 overflow-y-auto max-h-56 text-xs';
    } else {
      datesList.className = 'bg-white rounded-lg border border-amber-200/80 divide-y divide-slate-100 overflow-hidden text-xs';
    }

    datesList.innerHTML = rowsToShow.map(group => buildCompactRecurrenceRow(group, item.size)).join('');

    // Configurar botón "Ver todas / Ver menos"
    if (btnToggle) {
      if (totalAudits > 3) {
        btnToggle.classList.remove('hidden');
        if (isRecurrenceExpanded) {
          if (btnToggleText) btnToggleText.textContent = `Mostrar solo las 3 más recientes`;
          if (btnToggleIcon) btnToggleIcon.setAttribute('data-lucide', 'chevron-up');
        } else {
          const remaining = totalAudits - 3;
          if (btnToggleText) btnToggleText.textContent = `Ver todas las ${totalAudits} fechas (${remaining} ${remaining === 1 ? 'anterior' : 'anteriores'})`;
          if (btnToggleIcon) btnToggleIcon.setAttribute('data-lucide', 'chevron-down');
        }
      } else {
        btnToggle.classList.add('hidden');
      }
    }

    if (window.lucide) {
      lucide.createIcons();
    }
  }

  if (btnToggle) {
    btnToggle.onclick = () => {
      isRecurrenceExpanded = !isRecurrenceExpanded;
      updateRecurrenceList();
    };
  }

  updateRecurrenceList();
}

function renderUnifiedDifferences(item) {
  const container = document.getElementById('modalUnifiedDifferencesContainer');
  const summaryBanner = document.getElementById('modalUnifiedSummaryBanner');
  const netBadge = document.getElementById('modalNetBalanceBadge');
  if (!container) return;

  const curBaseRef = item.base_reference || item.reference;
  const curGender = item.gender;

  // Filtrar estrictamente hermanos que pertenezcan al mismo modelo y al mismo género (nunca mezclar referencias distintas ni Dama con Caballero)
  let siblings = (item.sibling_sizes && item.sibling_sizes.length > 0)
    ? item.sibling_sizes.filter(s => {
        const sBase = s.base_reference || s.reference;
        const matchRef = (sBase && curBaseRef && sBase === curBaseRef) || s.reference === item.reference;
        const matchGender = !curGender || !s.gender || s.gender === curGender;
        return matchRef && matchGender;
      })
    : [];

  if (siblings.length === 0) {
    siblings = [{
      id: item.id,
      reference: item.reference,
      size: item.size,
      difference: item.difference || 0,
      store_count: item.store_count || 0,
      warehouse_count: item.warehouse_count || 0,
      theoretical_count: item.theoretical_count || 0,
      status: item.status,
      validation_verdict: item.validation_verdict,
      barcode: item.barcode
    }];
  }

  const faltantes = siblings.filter(s => (s.difference || 0) < 0);
  const sobrantes = siblings.filter(s => (s.difference || 0) > 0);
  const totalFaltantes = faltantes.reduce((sum, s) => sum + Math.abs(s.difference || 0), 0);
  const totalSobrantes = sobrantes.reduce((sum, s) => sum + (s.difference || 0), 0);
  const netBalance = totalSobrantes - totalFaltantes;

  // 1. Balance Neto Badge (Sutil)
  if (netBadge) {
    if (totalFaltantes > 0 && totalSobrantes > 0 && totalFaltantes === totalSobrantes) {
      netBadge.className = 'text-[10px] font-black px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300';
      netBadge.innerHTML = '⚖️ Neto: 0 (Compensado)';
    } else if (netBalance < 0) {
      netBadge.className = 'text-[10px] font-black px-2 py-0.5 rounded-full bg-red-100 text-red-800 border border-red-200';
      netBadge.innerHTML = `Neto: -${Math.abs(netBalance)}`;
    } else if (netBalance > 0) {
      netBadge.className = 'text-[10px] font-black px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200';
      netBadge.innerHTML = `Neto: +${netBalance}`;
    } else {
      netBadge.className = 'text-[10px] font-black px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200';
      netBadge.innerHTML = 'Neto: 0';
    }
  }

  // 2. Banner de Trocada (1 sola línea limpia)
  if (summaryBanner) {
    if (totalFaltantes > 0 && totalSobrantes > 0) {
      summaryBanner.classList.remove('hidden');
      if (totalFaltantes === totalSobrantes) {
        summaryBanner.className = 'text-[11px] p-2 rounded-lg border bg-amber-50 border-amber-300 text-amber-950 flex items-center gap-1.5 font-medium';
        summaryBanner.innerHTML = `🔄 <span><strong>Posible Trocada:</strong> Faltan ${totalFaltantes} y sobran ${totalSobrantes} unids en este modelo (Compensado).</span>`;
      } else {
        summaryBanner.className = 'text-[11px] p-2 rounded-lg border bg-orange-50 border-orange-200 text-orange-950 flex items-center gap-1.5 font-medium';
        summaryBanner.innerHTML = `⚠️ <span>Discrepancia mixta: Faltan -${totalFaltantes} y sobran +${totalSobrantes} unids en el modelo.</span>`;
      }
    } else {
      summaryBanner.classList.add('hidden');
    }
  }

  // 3. Renderizar Chips Horizontales de Tallas
  container.innerHTML = siblings.map(sib => {
    const isCurrent = sib.id === item.id;
    const diffVal = sib.difference || 0;
    const totalPhys = (sib.store_count || 0) + (sib.warehouse_count || 0);

    let chipStyle = '';
    let diffTag = '';

    if (diffVal < 0) {
      diffTag = `-${Math.abs(diffVal)}`;
      chipStyle = isCurrent
        ? 'bg-red-600 text-white font-black ring-2 ring-red-400 shadow-xs'
        : 'bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 font-bold';
    } else if (diffVal > 0) {
      diffTag = `+${diffVal}`;
      chipStyle = isCurrent
        ? 'bg-emerald-600 text-white font-black ring-2 ring-emerald-400 shadow-xs'
        : 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 font-bold';
    } else {
      diffTag = '0';
      chipStyle = isCurrent
        ? 'bg-blue-600 text-white font-black ring-2 ring-blue-400 shadow-xs'
        : 'bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100 font-medium';
    }

    const validatedCheck = sib.status === 'validada' ? '✓ ' : '';

    return `
      <button type="button" 
              onclick="jumpToSiblingItem(${sib.id})" 
              class="px-2.5 py-1 rounded-lg text-xs inline-flex items-center gap-1.5 transition-all cursor-pointer ${chipStyle}"
              title="Talla ${sib.size}: Físico ${totalPhys} / Teórico ${sib.theoretical_count}">
        <span>${validatedCheck}Talla ${sib.size}</span>
        <span class="text-[10px] px-1 py-0.5 rounded font-black badge-pill ${isCurrent ? 'bg-white/25 text-white' : 'bg-black/5'}">${diffTag}</span>
      </button>
    `;
  }).join('');
}

function renderVerdictOptions(item) {
  const container = document.getElementById('verdictOptions');
  const label = document.getElementById('verdictOptionsLabel');
  if (!container) return;

  const diff = item.difference || 0;
  let options = [];

  if (diff < 0) {
    if (label) label.textContent = `Motivo del faltante (-${Math.abs(diff)} en Talla ${item.size}):`;
    options = [
      { id: 'Faltante Real', label: 'Faltante Real', icon: '🚨' },
      { id: 'Tag Defectuoso', label: 'Tag Defectuoso', icon: '🏷️' },
      { id: 'Sin Tag', label: 'Sin Tag', icon: '🚫' },
      { id: 'Averías', label: 'Averías', icon: '⚠️' },
      { id: 'Error Conteo', label: 'Error Conteo', icon: '🔢' },
      { id: 'Otro Motivo', label: 'Otro Motivo', icon: '💬' },
    ];
  } else if (diff > 0) {
    if (label) label.textContent = `Motivo del sobrante (+${diff} en Talla ${item.size}):`;
    options = [
      { id: 'Sobrante Real', label: 'Sobrante Real', icon: '📦' },
      { id: 'Doble Tag', label: 'Doble Tag', icon: '🏷️' },
      { id: 'Error Conteo', label: 'Error Conteo', icon: '🔢' },
      { id: 'Tag Defectuoso', label: 'Tag Defectuoso', icon: '⚠️' },
      { id: 'Sin Tag', label: 'Sin Tag', icon: '🚫' },
      { id: 'Averías', label: 'Averías', icon: '🛠️' },
      { id: 'Otro Motivo', label: 'Otro Motivo', icon: '💬' },
    ];
  } else {
    if (label) label.textContent = `Conteo Exacto (0 diferencia en Talla ${item.size}):`;
    options = [
      { id: 'Conteo Correcto', label: 'Conteo Correcto', icon: '✅' },
      { id: 'Ajuste Confirmado', label: 'Ajuste Confirmado', icon: '📋' },
      { id: 'Error Conteo', label: 'Error Conteo', icon: '🔢' },
      { id: 'Otro Motivo', label: 'Otro Motivo', icon: '💬' },
    ];
  }

  // Compatibilidad con registros antiguos
  if (currentSelectedVerdict === 'Mercancía Averiada') currentSelectedVerdict = 'Averías';
  if (currentSelectedVerdict === 'Doble Lectura') currentSelectedVerdict = 'Doble Tag';

  // Si el dictamen previo no pertenece a las opciones válidas y no está vacío, adaptarlo
  const validIds = options.map(o => o.id);
  if (currentSelectedVerdict && !validIds.includes(currentSelectedVerdict)) {
    // Si era un dictamen viejo que ya no existe, dejar que el usuario elija de las nuevas opciones
    currentSelectedVerdict = '';
  }

  container.innerHTML = options.map(opt => {
    const isSelected = (currentSelectedVerdict === opt.id);
    const selectedClass = isSelected
      ? 'bg-blue-600 text-white font-black shadow-xs ring-1 ring-blue-500'
      : 'bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100 font-bold';

    return `
      <button type="button" 
              data-verdict="${opt.id}" 
              class="verdict-btn py-2 px-2.5 rounded-lg text-xs inline-flex items-center justify-center gap-1.5 transition-all touch-target sm:min-w-0 cursor-pointer ${selectedClass}"
              title="${opt.label}">
        <span class="text-xs leading-none shrink-0">${opt.icon}</span>
        <span class="truncate">${opt.label}</span>
      </button>
    `;
  }).join('');
}

function selectVerdict(verdict) {
  currentSelectedVerdict = verdict;
  document.querySelectorAll('#verdictOptions .verdict-btn').forEach(b => {
    if (b.dataset.verdict === currentSelectedVerdict) {
      b.className = 'verdict-btn py-2 px-2.5 rounded-lg text-xs inline-flex items-center justify-center gap-1.5 transition-all touch-target sm:min-w-0 bg-blue-600 text-white font-black shadow-xs ring-1 ring-blue-500 cursor-pointer';
    } else {
      b.className = 'verdict-btn py-2 px-2.5 rounded-lg text-xs inline-flex items-center justify-center gap-1.5 transition-all touch-target sm:min-w-0 bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100 font-bold cursor-pointer';
    }
  });
}

function jumpToSiblingItem(targetId) {
  const targetIndex = filteredItems.findIndex(i => i.id === targetId);
  if (targetIndex !== -1) {
    openInspector(targetIndex);
    return;
  }
  // Si la prenda no está en la vista actual (ej. filtro activo), buscar en allItems
  const itemInAll = allItems.find(i => i.id === targetId);
  if (itemInAll) {
    currentFilter = 'all';
    currentSizeFilter = 'all';
    currentCategoryFilter = 'all';
    const sInput = document.getElementById('searchInput');
    if (sInput) sInput.value = '';
    applyFilters();
    const newIdx = filteredItems.findIndex(i => i.id === targetId);
    if (newIdx !== -1) {
      openInspector(newIdx);
    }
  }
}

function closeInspector() {
  document.getElementById('inspectorModal').classList.add('hidden');
}

// ============================================================================
// GESTIÓN DE FOTOS & SUBIDA UNIVERSAL
// ============================================================================
async function handlePhotoSelected(file) {
  if (!file || currentItemIndex < 0) return;
  const item = filteredItems[currentItemIndex];

  // Optimistic preview inmediata
  const reader = new FileReader();
  reader.onload = (e) => {
    updatePhotoUI(e.target.result);
  };
  reader.readAsDataURL(file);

  showToast('Guardando foto universal para todas las tallas...', 'info');

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`/api/items/${item.id}/photo`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Error al subir la foto');
    const result = await res.json();
    const newPhotoUrl = result.photo_url;

    // Actualizar en el item local
    item.photo_url = newPhotoUrl;

    // Identificadores de referencia base y nombre para propagación
    const baseRef = (item.base_reference || '').trim().toUpperCase();
    const curRef = (item.reference || '').trim().toUpperCase();
    const curName = (item.name || '').trim().toUpperCase();

    // Propagación universal en allItems
    allItems.forEach(i => {
      const iBase = (i.base_reference || '').trim().toUpperCase();
      const iRef = (i.reference || '').trim().toUpperCase();
      const iName = (i.name || '').trim().toUpperCase();

      const matchExact = iRef === curRef;
      const matchBase = (baseRef && (iBase === baseRef || iRef.startsWith(baseRef))) ||
                        (iBase && (curRef.startsWith(iBase)));
      const matchName = curName && iName && curName === iName;

      if (matchExact || matchBase || matchName) {
        i.photo_url = newPhotoUrl;
        if (i.sibling_sizes) {
          i.sibling_sizes.forEach(sib => {
            sib.photo_url = newPhotoUrl;
          });
        }
      }
    });

    // Actualizar también en las tallas hermanas del item abierto
    if (item.sibling_sizes) {
      item.sibling_sizes.forEach(sib => {
        sib.photo_url = newPhotoUrl;
      });
    }

    updatePhotoUI(newPhotoUrl);
    renderUnifiedDifferences(item);
    updateKPIs();
    updateFilterCounts();
    renderItems();
    showToast('¡Foto guardada universalmente para todas las tallas de esta referencia!', 'success');
  } catch (err) {
    console.error(err);
    showToast('Error al guardar la foto en el servidor', 'error');
  }
}

// ============================================================================
// GUARDADO DE VALIDACIÓN & SALTO A LA SIGUIENTE
// ============================================================================
async function saveValidation(andNext = false) {
  if (currentItemIndex < 0) return;
  const item = filteredItems[currentItemIndex];

  // VERIFICACIÓN DE OBLIGATORIEDAD DE FOTO
  if (!item.photo_url) {
    showToast('⚠️ ¡Es obligatorio tomarle foto o subir la imagen antes de validar!', 'warning');
    const alertBox = document.getElementById('mandatoryPhotoAlert');
    if (alertBox) {
      alertBox.classList.remove('hidden');
      alertBox.classList.add('pulse-alert');
      setTimeout(() => alertBox.classList.remove('pulse-alert'), 3000);
    }
    return;
  }

  // Asegurar que haya un dictamen seleccionado
  if (!currentSelectedVerdict) {
    // Si no ha seleccionado uno, sugerir el más coherente según la diferencia
    if (item.difference < 0) {
      currentSelectedVerdict = 'Faltante Real';
    } else if (item.difference > 0) {
      currentSelectedVerdict = 'Sobrante Real';
    } else {
      currentSelectedVerdict = 'Conteo Correcto';
    }
  }

  const notes = document.getElementById('validationNotes').value.trim();

  try {
    const res = await fetch(`/api/items/${item.id}/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        verdict: currentSelectedVerdict,
        notes: notes
      })
    });

    if (!res.ok) throw new Error('Error al guardar la validación');

    // Actualizar datos locales
    item.status = 'validada';
    item.validation_verdict = currentSelectedVerdict;
    item.validation_notes = notes;
    item.validated_at = new Date().toISOString();

    // Actualizar también en hermanos de otros items para mantener sincronía inmediata
    allItems.forEach(i => {
      if (i.sibling_sizes) {
        const sib = i.sibling_sizes.find(s => s.id === item.id);
        if (sib) {
          sib.status = 'validada';
          sib.validation_verdict = currentSelectedVerdict;
          sib.validation_notes = notes;
        }
      }
    });

    updateKPIs();
    updateFilterCounts();
    renderItems();

    showToast('Prenda validada correctamente', 'success');

    // Si se solicitó avanzar a la siguiente pendiente
    if (andNext) {
      goToNextPending();
    } else {
      openInspector(currentItemIndex);
    }

  } catch (err) {
    console.error(err);
    showToast('Error al guardar la validación', 'error');
  }
}

function goToNextPending() {
  // Buscar la siguiente prenda pendiente a partir del índice actual
  let nextIdx = -1;
  for (let i = currentItemIndex + 1; i < filteredItems.length; i++) {
    if (filteredItems[i].status !== 'validada') {
      nextIdx = i;
      break;
    }
  }

  // Si no hay hacia adelante, buscar desde el principio
  if (nextIdx === -1) {
    for (let i = 0; i < currentItemIndex; i++) {
      if (filteredItems[i].status !== 'validada') {
        nextIdx = i;
        break;
      }
    }
  }

  if (nextIdx !== -1) {
    openInspector(nextIdx);
  } else {
    // ¡Todas las prendas de la lista están validadas!
    closeInspector();
    triggerCelebration();
    showToast('🎉 ¡Excelente! Has completado la validación de todas las prendas de este grupo.', 'success');
  }
}

function triggerCelebration() {
  if (window.confetti) {
    window.confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    });
  }
}

// ============================================================================
// EXPORTACIÓN A EXCEL & TABLA PARA CORREO ELECTRÓNICO
// ============================================================================
function downloadValidatedExcel() {
  if (!currentAuditId) {
    showToast('Selecciona primero una auditoría', 'warning');
    return;
  }
  window.open(`/api/export/${currentAuditId}/excel`, '_blank');
}

async function openEmailModal() {
  if (!currentAuditId) {
    showToast('Selecciona primero una auditoría', 'warning');
    return;
  }

  const modal = document.getElementById('emailModal');
  modal.classList.remove('hidden');
  await renderEmailPreview();
}

async function renderEmailPreview() {
  const scope = document.getElementById('emailScopeSelector').value;
  const onlyValidated = scope === 'validated';

  try {
    const res = await fetch(`/api/export/${currentAuditId}/email-html?only_validated=${onlyValidated}`);
    if (!res.ok) throw new Error('Error al generar tabla para correo');
    const html = await res.text();
    
    document.getElementById('emailPreviewContainer').innerHTML = html;
  } catch (err) {
    console.error(err);
    showToast('Error al generar vista previa para correo', 'error');
  }
}

async function copyEmailTableToClipboard() {
  const preview = document.getElementById('emailPreviewContainer');
  if (!preview) return;

  try {
    // Copiar como HTML rico para que pegue en Outlook/Gmail con estilos y colores
    const htmlContent = preview.innerHTML;
    const textContent = preview.innerText;

    if (navigator.clipboard && window.ClipboardItem) {
      const blobHtml = new Blob([htmlContent], { type: 'text/html' });
      const blobText = new Blob([textContent], { type: 'text/plain' });
      const item = new ClipboardItem({
        'text/html': blobHtml,
        'text/plain': blobText
      });
      await navigator.clipboard.write([item]);
    } else {
      // Fallback para navegadores antiguos
      const range = document.createRange();
      range.selectNode(preview);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
      document.execCommand('copy');
      window.getSelection().removeAllRanges();
    }

    showToast('✅ ¡Tabla copiada! Abre tu correo y presiona Ctrl + V para pegarla', 'success');
  } catch (err) {
    console.error(err);
    showToast('Error al copiar la tabla al portapapeles', 'error');
  }
}

// ============================================================================
// MODAL DE HISTORIAL COMPLETO DE INVENTARIOS POR FECHA
// ============================================================================
function openAuditHistoryModal() {
  const modal = document.getElementById('auditHistoryModal');
  if (!modal) return;

  const searchInput = document.getElementById('historySearchInput');
  const dateInput = document.getElementById('historyDateInput');
  const btnClearDate = document.getElementById('btnClearHistoryDate');

  if (searchInput) searchInput.value = historySearchQuery;
  if (dateInput) {
    dateInput.value = historyDateQuery;
    if (btnClearDate) btnClearDate.classList.toggle('hidden', !historyDateQuery);
  }

  updateHistoryChipButtons();
  renderAuditHistoryList();
  modal.classList.remove('hidden');
}

function closeAuditHistoryModal() {
  const modal = document.getElementById('auditHistoryModal');
  if (modal) modal.classList.add('hidden');
}

function updateHistoryChipButtons() {
  const chips = document.querySelectorAll('.history-chip');
  chips.forEach(chip => {
    const filter = chip.dataset.historyFilter;
    if (filter === historyChipFilter) {
      chip.className = 'history-chip active px-2.5 py-1 rounded-lg text-xs font-bold transition-all bg-blue-600 text-white shadow-xs';
    } else {
      chip.className = 'history-chip px-2.5 py-1 rounded-lg text-xs font-bold transition-all bg-white border border-slate-200 text-slate-700 hover:bg-slate-100';
    }
  });
}

function renderAuditHistoryList() {
  const container = document.getElementById('auditHistoryList');
  const countSpan = document.getElementById('auditHistoryCount');
  if (!container) return;

  const q = historySearchQuery.toLowerCase().trim();
  const d = historyDateQuery.trim();
  const now = new Date();
  const currentYearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

  const filtered = allAudits.filter(a => {
    const aDate = a.audit_date || (a.uploaded_at ? a.uploaded_at.substring(0, 10) : '');
    const nameMatch = !q || (a.name && a.name.toLowerCase().includes(q)) || (a.filename && a.filename.toLowerCase().includes(q));
    const dateMatch = !d || (aDate === d);

    let chipMatch = true;
    if (historyChipFilter === 'lunes') {
      chipMatch = getDayOfWeekFromDateStr(aDate) === 1;
    } else if (historyChipFilter === 'miercoles') {
      chipMatch = getDayOfWeekFromDateStr(aDate) === 3;
    } else if (historyChipFilter === 'this_month') {
      chipMatch = aDate.startsWith(currentYearMonth);
    }

    return nameMatch && dateMatch && chipMatch;
  });

  if (countSpan) {
    countSpan.textContent = `${filtered.length} de ${allAudits.length} inventario(s)`;
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center bg-slate-50 border border-slate-200 rounded-xl flex flex-col items-center justify-center">
        <div class="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center mb-2 text-slate-400">
          <i data-lucide="search-x" class="w-5 h-5"></i>
        </div>
        <p class="text-xs font-bold text-slate-700">No se encontraron inventarios</p>
        <p class="text-[11px] text-slate-400 mt-1 max-w-xs">Intenta cambiar la fecha o el texto de búsqueda.</p>
      </div>
    `;
    initIcons();
    return;
  }

  container.innerHTML = filtered.map(a => {
    const aDate = a.audit_date || (a.uploaded_at ? a.uploaded_at.substring(0, 10) : '');
    const isCurrent = a.id === currentAuditId;
    const fullDate = formatAuditDateFull(aDate);
    const dayOfWeek = getDayOfWeekFromDateStr(aDate);
    const isMonOrWed = dayOfWeek === 1 ? 'Lunes de Lectura' : (dayOfWeek === 3 ? 'Miércoles de Lectura' : null);

    let uploadTime = '';
    if (a.uploaded_at && a.uploaded_at.includes(' ')) {
      uploadTime = a.uploaded_at.split(' ')[1].substring(0, 5);
    }

    return `
      <div class="p-3 sm:p-3.5 rounded-xl border transition-all ${
        isCurrent ? 'bg-blue-50/70 border-blue-400 shadow-sm ring-1 ring-blue-400/50' : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-xs'
      } flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-1.5 flex-wrap mb-1">
            <span class="text-[11px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md ${
              isCurrent ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'
            }">
              ${fullDate || 'Fecha sin registrar'}
            </span>
            <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 font-mono">
              #${a.id}${uploadTime ? ' · ' + uploadTime : ''}
            </span>
            ${isMonOrWed ? `<span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">${isMonOrWed}</span>` : ''}
            ${isCurrent ? '<span class="text-[10px] font-black px-2 py-0.5 rounded bg-blue-100 text-blue-800">EN PANTALLA</span>' : ''}
          </div>

          <h4 class="text-xs sm:text-sm font-black text-slate-900 truncate">${a.name}</h4>
          
          <div class="flex items-center gap-3 text-[11px] text-slate-400 mt-1 flex-wrap">
            <span class="flex items-center gap-1 font-semibold text-slate-600">
              <i data-lucide="layers" class="w-3.5 h-3.5 text-slate-400"></i>
              ${a.total_items} referencias
            </span>
            <span class="flex items-center gap-1 truncate font-mono text-[10px] text-slate-500">
              <i data-lucide="file-spreadsheet" class="w-3.5 h-3.5 text-slate-400"></i>
              ${a.filename || 'excel'}
            </span>
          </div>
        </div>

        <div class="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
          <a href="/api/audits/${a.id}/download-original" download class="p-1.5 rounded-lg text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 border border-slate-200 hover:border-emerald-200 transition-colors flex items-center gap-1 text-xs" title="Descargar documento Excel original de este inventario">
            <i data-lucide="download" class="w-3.5 h-3.5"></i>
            <span class="hidden md:inline font-semibold">Excel</span>
          </a>
          <button type="button" onclick="selectAuditFromHistory(${a.id})" class="px-3 py-1.5 rounded-lg text-xs font-black transition-all ${
            isCurrent
              ? 'bg-blue-600 text-white shadow-xs cursor-default'
              : 'bg-slate-900 hover:bg-blue-600 active:bg-blue-700 text-white shadow-xs'
          } flex items-center gap-1.5">
            <i data-lucide="${isCurrent ? 'check' : 'arrow-right'}" class="w-3.5 h-3.5"></i>
            ${isCurrent ? 'Activo' : 'Cargar'}
          </button>
          <button type="button" onclick="deleteAuditFromHistory(${a.id})" class="px-2.5 py-1.5 rounded-lg text-red-600 hover:text-white bg-red-50 hover:bg-red-600 border border-red-200 hover:border-red-600 text-xs font-bold transition-colors flex items-center gap-1 shadow-xs" title="Eliminar este archivo de inventario">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            <span class="hidden xs:inline">Eliminar</span>
          </button>
        </div>

      </div>
    `;
  }).join('');

  initIcons();
}

async function selectAuditFromHistory(auditId) {
  const audit = allAudits.find(a => a.id === auditId);
  closeAuditHistoryModal();
  if (!audit) return;

  const auditDate = audit.audit_date || (audit.uploaded_at ? audit.uploaded_at.substring(0, 10) : '');
  applyAuditDateFilter(auditDate, auditId);
  showToast(`Inventario "${audit.name}" cargado`, 'success');
}

// ============================================================================
// MODAL DE CONFIRMACIÓN ESTILIZADO (REEMPLAZA CONFIRM NATIVO)
// ============================================================================
let confirmModalResolver = null;

function showCustomConfirm({
  title = '¿Eliminar este inventario?',
  targetName = '',
  targetMeta = '',
  message = 'Esta acción borrará definitivamente este archivo y todas sus prendas registradas de la base de datos.',
  acceptText = 'Eliminar',
  cancelText = 'Cancelar',
  isDanger = true,
  icon = 'trash-2'
}) {
  return new Promise((resolve) => {
    confirmModalResolver = resolve;
    const modal = document.getElementById('confirmActionModal');
    if (!modal) {
      resolve(confirm(`${title}\n\n${targetName} ${targetMeta}\n\n${message}`));
      return;
    }

    const titleEl = document.getElementById('confirmModalTitle');
    const nameEl = document.getElementById('confirmModalTargetName');
    const metaEl = document.getElementById('confirmModalTargetMeta');
    const msgEl = document.getElementById('confirmModalMessage');
    const acceptBtn = document.getElementById('btnConfirmAccept');
    const acceptTextEl = document.getElementById('confirmModalAcceptText');
    const cancelBtn = document.getElementById('btnConfirmCancel');
    const iconWrapper = document.getElementById('confirmModalIconWrapper');
    const iconEl = document.getElementById('confirmModalIcon');
    const targetBox = document.getElementById('confirmModalTargetBox');

    if (titleEl) titleEl.textContent = title;
    
    if (targetName) {
      if (targetBox) targetBox.classList.remove('hidden');
      if (nameEl) nameEl.textContent = targetName;
      if (metaEl) metaEl.innerHTML = targetMeta;
    } else if (targetBox) {
      targetBox.classList.add('hidden');
    }

    if (msgEl) msgEl.textContent = message;
    if (acceptTextEl) acceptTextEl.textContent = acceptText;
    if (cancelBtn) cancelBtn.textContent = cancelText;

    if (iconEl) iconEl.setAttribute('data-lucide', icon);

    if (isDanger) {
      if (iconWrapper) iconWrapper.className = 'w-12 h-12 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mb-3 shadow-xs';
      if (acceptBtn) acceptBtn.className = 'py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 active:bg-red-800 text-white font-bold text-xs shadow-md transition-colors flex items-center justify-center gap-1.5 touch-target';
    } else {
      if (iconWrapper) iconWrapper.className = 'w-12 h-12 rounded-2xl bg-blue-100 text-blue-600 flex items-center justify-center mb-3 shadow-xs';
      if (acceptBtn) acceptBtn.className = 'py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-xs shadow-md transition-colors flex items-center justify-center gap-1.5 touch-target';
    }

    modal.classList.remove('hidden');
    initIcons();
  });
}

function closeConfirmModal(result) {
  const modal = document.getElementById('confirmActionModal');
  if (modal) modal.classList.add('hidden');
  if (confirmModalResolver) {
    confirmModalResolver(result);
    confirmModalResolver = null;
  }
}

async function deleteAuditFromHistory(auditId) {
  const audit = allAudits.find(a => a.id === auditId);
  const auditName = audit ? audit.name : `Inventario #${auditId}`;
  const totalItems = audit ? audit.total_items : 0;
  
  const confirmed = await showCustomConfirm({
    title: '¿Eliminar este inventario?',
    targetName: `"${auditName}"`,
    targetMeta: `<span>${totalItems} prendas</span> <span>•</span> <span class="font-mono text-[10px] bg-slate-200/90 px-1.5 py-0.5 rounded text-slate-700">ID #${auditId}</span>`,
    message: 'Esta acción borrará definitivamente este archivo y todas sus prendas registradas de la base de datos.',
    acceptText: 'Eliminar',
    cancelText: 'Cancelar',
    isDanger: true,
    icon: 'trash-2'
  });

  if (!confirmed) return;

  try {
    const res = await fetch(`/api/audits/${auditId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Error al eliminar');
    
    showToast(`Inventario "${auditName}" eliminado exitosamente`, 'success');
    if (currentAuditId === auditId) {
      currentAuditId = null;
    }
    await loadAudits();
    await loadCatalogStats();
    if (catalogItems.length > 0) await loadCatalog();
    renderAuditHistoryList();
    if (currentMainTab === 'files') renderFilesSection();
  } catch (err) {
    console.error(err);
    showToast('Error al eliminar el inventario', 'error');
  }
}


// ============================================================================
// SUBIDA DE NUEVO EXCEL
// ============================================================================
async function handleExcelUpload(e) {
  e.preventDefault();
  const fileInput = document.getElementById('excelFileInput');
  const auditNameInput = document.getElementById('auditNameInput');
  const auditDateInput = document.getElementById('uploadAuditDate');
  const statusMsg = document.getElementById('uploadStatusMessage');

  if (!fileInput.files || fileInput.files.length === 0) {
    showToast('Por favor selecciona un archivo Excel (.xlsx o .xls)', 'warning');
    return;
  }

  const file = fileInput.files[0];
  const auditName = auditNameInput.value.trim();
  const auditDate = auditDateInput ? auditDateInput.value.trim() : '';

  statusMsg.className = 'text-xs p-3 rounded-lg bg-blue-50 text-blue-700 block';
  statusMsg.innerHTML = '<div class="flex items-center gap-2"><i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Procesando referencias del Excel...</div>';
  initIcons();

  const formData = new FormData();
  formData.append('file', file);
  if (auditName) {
    formData.append('audit_name', auditName);
  }
  if (auditDate) {
    formData.append('audit_date', auditDate);
  }

  try {
    const res = await fetch('/api/audits/upload', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || 'Error al procesar el archivo');
    }

    const result = await res.json();
    currentAuditId = result.audit_id;

    statusMsg.className = 'text-xs p-3 rounded-lg bg-emerald-50 text-emerald-800 block font-bold';
    const recCount = result.recurrent_count || 0;
    const recTxt = recCount > 0 ? ` (🔥 ${recCount} prendas repetidas de otros inventarios)` : '';
    statusMsg.textContent = `¡Listo! Se cargaron ${result.items_count} referencias guardadas en historial${recTxt}.`;

    setTimeout(async () => {
      document.getElementById('uploadModal').classList.add('hidden');
      document.getElementById('uploadForm').reset();
      document.getElementById('dropZoneFileName').textContent = 'Arrastra tu Excel aquí o haz clic para seleccionar';
      statusMsg.classList.add('hidden');
      if (auditDate) {
        selectedAuditDate = auditDate;
      }
      await loadAudits(result.audit_id);
      await loadCatalogStats();
      if (catalogItems.length > 0) await loadCatalog();
      const toastTxt = recCount > 0
        ? `Auditoría guardada: ${result.items_count} prendas (${recCount} repetidas)`
        : `Auditoría guardada con ${result.items_count} referencias`;
      showToast(toastTxt, 'success');
    }, 1400);

  } catch (err) {
    console.error(err);
    statusMsg.className = 'text-xs p-3 rounded-lg bg-red-50 text-red-700 block font-bold';
    statusMsg.textContent = `Error: ${err.message}`;
  }
}

// ============================================================================
// ELIMINACIÓN DE AUDITORÍA
// ============================================================================
async function deleteCurrentAudit() {
  if (!currentAuditId) return;
  const audit = audits.find(a => a.id === currentAuditId);
  const name = audit ? audit.name : 'esta auditoría';
  const totalItems = audit ? audit.total_items : 0;

  const confirmed = await showCustomConfirm({
    title: '¿Eliminar esta auditoría?',
    targetName: `"${name}"`,
    targetMeta: `<span>${totalItems} prendas</span> <span>•</span> <span class="font-mono text-[10px] bg-slate-200/90 px-1.5 py-0.5 rounded text-slate-700">ID #${currentAuditId}</span>`,
    message: 'Esta acción borrará definitivamente este archivo de la base de datos. Las fotos del catálogo maestro se conservarán.',
    acceptText: 'Eliminar',
    cancelText: 'Cancelar',
    isDanger: true,
    icon: 'trash-2'
  });

  if (!confirmed) return;

  try {
    const res = await fetch(`/api/audits/${currentAuditId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Error al eliminar');
    
    showToast('Auditoría eliminada', 'info');
    currentAuditId = null;
    await loadAudits();
  } catch (err) {
    console.error(err);
    showToast('Error al eliminar la auditoría', 'error');
  }
}


// ============================================================================
// MODAL MÓVIL & QR
// ============================================================================
let currentQRMode = 'cloud'; // 'cloud' o 'local'

function getActiveMobileUrl() {
  const currentOrigin = window.location.origin;
  const isLocalhost = currentOrigin.includes('localhost') || currentOrigin.includes('127.0.0.1');

  if (currentQRMode === 'cloud') {
    if (!isLocalhost && (currentOrigin.startsWith('https://') || currentOrigin.includes('trycloudflare.com') || currentOrigin.includes('.loca.lt'))) {
      return currentOrigin;
    }
    if (networkInfo && networkInfo.public_url) {
      return networkInfo.public_url;
    }
    if (networkInfo && networkInfo.mobile_url && networkInfo.mobile_url.startsWith('https://')) {
      return networkInfo.mobile_url;
    }
  }

  // Modo local Wi-Fi
  if (networkInfo && networkInfo.local_ip) {
    return `http://${networkInfo.local_ip}:${networkInfo.port || 8000}`;
  }
  if (networkInfo && networkInfo.mobile_url) {
    return networkInfo.mobile_url;
  }
  return currentOrigin;
}

function renderQRCode() {
  const container = document.getElementById('qrcodeContainer');
  const mobileUrlText = document.getElementById('mobileUrlText');
  const btnCloud = document.getElementById('btnQRModeCloud');
  const btnLocal = document.getElementById('btnQRModeLocal');
  const qrHelpNote = document.getElementById('qrHelpNote');
  if (!container) return;

  container.innerHTML = '';
  const targetUrl = getActiveMobileUrl();

  if (mobileUrlText) {
    mobileUrlText.textContent = targetUrl || 'URL no disponible';
  }

  if (btnCloud && btnLocal) {
    if (currentQRMode === 'cloud') {
      btnCloud.className = 'flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all bg-blue-600 text-white shadow-xs flex items-center justify-center gap-1';
      btnLocal.className = 'flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all text-slate-600 hover:text-slate-900 flex items-center justify-center gap-1';
      if (qrHelpNote) {
        qrHelpNote.innerHTML = '💡 <strong class="text-blue-600 font-semibold">En la Nube</strong> funciona con cualquier celular (datos o Wi-Fi) y permite usar la cámara sin bloqueos.';
      }
    } else {
      btnLocal.className = 'flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all bg-blue-600 text-white shadow-xs flex items-center justify-center gap-1';
      btnCloud.className = 'flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all text-slate-600 hover:text-slate-900 flex items-center justify-center gap-1';
      if (qrHelpNote) {
        qrHelpNote.innerHTML = '⚠️ <strong class="text-amber-600 font-semibold">Wi-Fi Local</strong> requiere que el celular esté en la misma red y que el Firewall no bloquee el puerto 8000.';
      }
    }
  }

  if (targetUrl && window.QRCode) {
    new QRCode(container, {
      text: targetUrl,
      width: 170,
      height: 170,
      colorDark: '#0f172a',
      colorLight: '#ffffff',
      correctLevel: QRCode.CorrectLevel.M
    });
  } else {
    container.innerHTML = '<span class="text-xs text-slate-400">Generando QR...</span>';
  }

  initIcons();
}

function openMobileQRModal() {
  const modal = document.getElementById('mobileQRModal');
  if (!modal) return;
  modal.classList.remove('hidden');
  renderQRCode();
}


// ============================================================================
// EVENT LISTENERS & VINCULACIÓN
// ============================================================================
function setupEventListeners() {
  // Control del Panel Desplegable de Filtros (Icono de la Lupa)
  const btnToggleFilters = document.getElementById('btnToggleFilters');
  if (btnToggleFilters) {
    btnToggleFilters.addEventListener('click', () => toggleFilterDrawer());
  }

  const btnCloseDrawer = document.getElementById('btnCloseFilterDrawer');
  if (btnCloseDrawer) {
    btnCloseDrawer.addEventListener('click', () => toggleFilterDrawer(false));
  }

  const btnResetAll = document.getElementById('btnResetAllFilters');
  if (btnResetAll) {
    btnResetAll.addEventListener('click', clearAllFilters);
  }

  const btnQuickClear = document.getElementById('btnQuickClearFilters');
  if (btnQuickClear) {
    btnQuickClear.addEventListener('click', clearAllFilters);
  }

  // Atajo global para abrir panel de filtros con Ctrl+F o '/' y cerrarlo con Escape
  window.addEventListener('keydown', (e) => {
    const confirmModal = document.getElementById('confirmActionModal');
    if (confirmModal && !confirmModal.classList.contains('hidden')) {
      if (e.key === 'Escape') closeConfirmModal(false);
      if (e.key === 'Enter') closeConfirmModal(true);
      return;
    }

    const inspector = document.getElementById('inspectorModal');
    const uploadModal = document.getElementById('uploadModal');
    const emailModal = document.getElementById('emailModal');
    const mobileModal = document.getElementById('mobileQRModal');
    const auditHistoryModal = document.getElementById('auditHistoryModal');

    const isModalOpen = (inspector && !inspector.classList.contains('hidden')) ||
                        (uploadModal && !uploadModal.classList.contains('hidden')) ||
                        (emailModal && !emailModal.classList.contains('hidden')) ||
                        (mobileModal && !mobileModal.classList.contains('hidden')) ||
                        (auditHistoryModal && !auditHistoryModal.classList.contains('hidden'));

    if (isModalOpen) {
      if (e.key === 'Escape' && auditHistoryModal && !auditHistoryModal.classList.contains('hidden')) {
        closeAuditHistoryModal();
      }
      return;
    }

    if ((e.ctrlKey && (e.key === 'f' || e.key === 'F')) || 
        (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA')) {
      e.preventDefault();
      toggleFilterDrawer(true);
    } else if (e.key === 'Escape') {
      const drawer = document.getElementById('filterDrawer');
      if (drawer && !drawer.classList.contains('hidden')) {
        toggleFilterDrawer(false);
      }
    }
  });

  // Filtro de fecha en cabecera
  const auditDateFilter = document.getElementById('auditDateFilter');
  if (auditDateFilter) {
    auditDateFilter.addEventListener('change', (e) => {
      applyAuditDateFilter(e.target.value);
    });
  }

  const btnClearDateFilter = document.getElementById('btnClearDateFilter');
  if (btnClearDateFilter) {
    btnClearDateFilter.addEventListener('click', () => {
      applyAuditDateFilter('');
    });
  }

  // Selector de Auditoría
  const auditSelector = document.getElementById('auditSelector');
  if (auditSelector) {
    auditSelector.addEventListener('change', (e) => {
      currentAuditId = parseInt(e.target.value);
      loadAuditDetails(currentAuditId);
    });
  }


  // Modal Historial de Inventarios
  const btnOpenAuditHistory = document.getElementById('btnOpenAuditHistory');
  if (btnOpenAuditHistory) {
    btnOpenAuditHistory.addEventListener('click', openAuditHistoryModal);
  }

  const btnCloseAuditHistory = document.getElementById('btnCloseAuditHistory');
  if (btnCloseAuditHistory) {
    btnCloseAuditHistory.addEventListener('click', closeAuditHistoryModal);
  }

  const btnCloseAuditHistoryBottom = document.getElementById('btnCloseAuditHistoryBottom');
  if (btnCloseAuditHistoryBottom) {
    btnCloseAuditHistoryBottom.addEventListener('click', closeAuditHistoryModal);
  }

  const historySearchInput = document.getElementById('historySearchInput');
  if (historySearchInput) {
    historySearchInput.addEventListener('input', (e) => {
      historySearchQuery = e.target.value;
      renderAuditHistoryList();
    });
  }

  const historyDateInput = document.getElementById('historyDateInput');
  const btnClearHistoryDate = document.getElementById('btnClearHistoryDate');
  if (historyDateInput) {
    historyDateInput.addEventListener('change', (e) => {
      historyDateQuery = e.target.value;
      if (btnClearHistoryDate) btnClearHistoryDate.classList.toggle('hidden', !historyDateQuery);
      renderAuditHistoryList();
    });
  }

  if (btnClearHistoryDate) {
    btnClearHistoryDate.addEventListener('click', () => {
      historyDateQuery = '';
      if (historyDateInput) historyDateInput.value = '';
      btnClearHistoryDate.classList.add('hidden');
      renderAuditHistoryList();
    });
  }

  // Chips de filtro rápido en modal historial
  document.querySelectorAll('.history-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      historyChipFilter = chip.dataset.historyFilter || 'all';
      updateHistoryChipButtons();
      renderAuditHistoryList();
    });
  });

  // Búsqueda en tiempo real
  const searchInput = document.getElementById('searchInput');
  const btnClearSearch = document.getElementById('btnClearSearch');

  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value;
    btnClearSearch.classList.toggle('hidden', !searchQuery);
    applyFilters();
  });

  btnClearSearch.addEventListener('click', () => {
    searchInput.value = '';
    searchQuery = '';
    btnClearSearch.classList.add('hidden');
    applyFilters();
  });

// Función global para filtrar por Género (disponible para listener y atributo onchange)
window.selectGenderFilter = function(val) {
  currentGender = val || 'all';
  const gf = document.getElementById('genderFilter');
  if (gf && gf.value !== currentGender) {
    gf.value = currentGender;
  }
  populateCategories();
  applyFilters();
};

  // Selector de Género / Departamento Oficial (28 Dama / 45 Caballero)
  const genderFilterElem = document.getElementById('genderFilter');
  if (genderFilterElem) {
    genderFilterElem.addEventListener('change', (e) => {
      window.selectGenderFilter(e.target.value);
    });
  }

  // Selector de Categoría / Tipo de Prenda
  document.getElementById('categoryFilter').addEventListener('change', (e) => {
    currentCategory = e.target.value;
    applyFilters();
  });

  // Selector de Talla
  const sizeFilterElem = document.getElementById('sizeFilter');
  if (sizeFilterElem) {
    sizeFilterElem.addEventListener('change', (e) => {
      currentSizeFilter = e.target.value;
      renderSizeBreakdown();
      applyFilters();
    });
  }

  // Botón Resetear Filtro de Tallas
  const btnResetSize = document.getElementById('btnResetSizeFilter');
  if (btnResetSize) {
    btnResetSize.addEventListener('click', () => {
      currentSizeFilter = 'all';
      if (sizeFilterElem) sizeFilterElem.value = 'all';
      renderSizeBreakdown();
      applyFilters();
    });
  }

  // Selector de Estado / Tipo de Diferencia (Menú Retráctil)
  const statusFilterElem = document.getElementById('statusFilter');
  if (statusFilterElem) {
    statusFilterElem.addEventListener('change', (e) => {
      currentFilter = e.target.value;
      applyFilters();
    });
  }

  // Atajos rápidos al tocar tarjetas de KPI
  const kpiFaltantes = document.getElementById('kpiFaltantesCard');
  if (kpiFaltantes) {
    kpiFaltantes.addEventListener('click', () => {
      currentFilter = currentFilter === 'faltantes' ? 'all' : 'faltantes';
      if (statusFilterElem) statusFilterElem.value = currentFilter;
      applyFilters();
    });
  }

  const kpiSobrantes = document.getElementById('kpiSobrantesCard');
  if (kpiSobrantes) {
    kpiSobrantes.addEventListener('click', () => {
      currentFilter = currentFilter === 'sobrantes' ? 'all' : 'sobrantes';
      if (statusFilterElem) statusFilterElem.value = currentFilter;
      applyFilters();
    });
  }

  const kpiRecurrent = document.getElementById('kpiRecurrentCard');
  if (kpiRecurrent) {
    kpiRecurrent.addEventListener('click', () => {
      currentFilter = currentFilter === 'reincidentes' ? 'all' : 'reincidentes';
      if (statusFilterElem) statusFilterElem.value = currentFilter;
      applyFilters();
    });
  }

  const kpiPhoto = document.getElementById('kpiPhotoCard');
  if (kpiPhoto) {
    kpiPhoto.addEventListener('click', () => {
      currentFilter = currentFilter === 'sin_foto' ? 'all' : 'sin_foto';
      if (statusFilterElem) statusFilterElem.value = currentFilter;
      applyFilters();
    });
  }

  // Alternar Vistas (si existen los botones en el DOM)
  const btnCards = document.getElementById('btnViewCards');
  const btnTable = document.getElementById('btnViewTable');
  const cardsContainer = document.getElementById('cardsContainer');
  const tableContainer = document.getElementById('tableContainer');

  if (btnCards && cardsContainer && tableContainer) {
    btnCards.addEventListener('click', () => {
      viewMode = 'cards';
      btnCards.className = 'px-2.5 py-1 text-xs font-semibold rounded bg-white text-slate-800 shadow-xs flex items-center gap-1.5 transition-all';
      if (btnTable) btnTable.className = 'px-2.5 py-1 text-xs font-semibold rounded text-slate-500 hover:text-slate-800 flex items-center gap-1.5 transition-all';
      cardsContainer.classList.remove('hidden');
      tableContainer.classList.add('hidden');
      renderItems();
    });
  }

  if (btnTable && cardsContainer && tableContainer) {
    btnTable.addEventListener('click', () => {
      viewMode = 'table';
      btnTable.className = 'px-2.5 py-1 text-xs font-semibold rounded bg-white text-slate-800 shadow-xs flex items-center gap-1.5 transition-all';
      if (btnCards) btnCards.className = 'px-2.5 py-1 text-xs font-semibold rounded text-slate-500 hover:text-slate-800 flex items-center gap-1.5 transition-all';
      cardsContainer.classList.add('hidden');
      tableContainer.classList.remove('hidden');
      renderItems();
    });
  }

  // Modal Inspector: Navegación
  document.getElementById('btnCloseInspector').addEventListener('click', closeInspector);
  document.getElementById('btnModalPrev').addEventListener('click', () => {
    if (currentItemIndex > 0) openInspector(currentItemIndex - 1);
  });
  document.getElementById('btnModalNext').addEventListener('click', () => {
    if (currentItemIndex < filteredItems.length - 1) openInspector(currentItemIndex + 1);
  });

  // Atajos de teclado en el Inspector
  window.addEventListener('keydown', (e) => {
    const inspector = document.getElementById('inspectorModal');
    if (inspector.classList.contains('hidden')) return;

    if (e.key === 'Escape') {
      closeInspector();
    } else if (e.key === 'ArrowLeft' && currentItemIndex > 0) {
      openInspector(currentItemIndex - 1);
    } else if (e.key === 'ArrowRight' && currentItemIndex < filteredItems.length - 1) {
      openInspector(currentItemIndex + 1);
    }
  });

  // Copiar código de barras (botón o clic en el código de barras visual)
  const copyBarcodeHandler = () => {
    const barcode = document.getElementById('modalBarcode').textContent;
    if (barcode && barcode !== '-') {
      navigator.clipboard.writeText(barcode);
      showToast(`Código ${barcode} copiado al portapapeles`, 'info');
    }
  };
  document.getElementById('btnCopyBarcode').addEventListener('click', copyBarcodeHandler);
  const barcodeCard = document.getElementById('modalBarcodeCard');
  if (barcodeCard) barcodeCard.addEventListener('click', copyBarcodeHandler);

  // Dictamen botones (delegación para botones generados dinámicamente)
  const verdictOptionsContainer = document.getElementById('verdictOptions');
  if (verdictOptionsContainer) {
    verdictOptionsContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('.verdict-btn');
      if (btn && btn.dataset.verdict) {
        selectVerdict(btn.dataset.verdict);
      }
    });
  }

  // Botones de Validación (Desktop & Mobile)
  document.getElementById('btnSaveValidationOnly').addEventListener('click', () => saveValidation(false));
  document.getElementById('btnSaveAndNext').addEventListener('click', () => saveValidation(true));
  const btnSaveMobile = document.getElementById('btnSaveValidationOnlyMobile');
  if (btnSaveMobile) btnSaveMobile.addEventListener('click', () => saveValidation(false));
  const btnSaveNextMobile = document.getElementById('btnSaveAndNextMobile');
  if (btnSaveNextMobile) btnSaveNextMobile.addEventListener('click', () => saveValidation(true));

  // Fotos: Cámara y Archivo
  const cameraInput = document.getElementById('cameraInput');
  const fileInput = document.getElementById('fileInput');

  document.getElementById('btnCaptureCamera').addEventListener('click', () => cameraInput.click());
  document.getElementById('btnUploadFile').addEventListener('click', () => fileInput.click());
  document.getElementById('btnTriggerPhotoChange').addEventListener('click', () => cameraInput.click());
  const btnDeletePhoto = document.getElementById('btnDeletePhoto');
  if (btnDeletePhoto) {
    btnDeletePhoto.addEventListener('click', handleDeleteModalPhoto);
  }

  cameraInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) handlePhotoSelected(e.target.files[0]);
  });
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) handlePhotoSelected(e.target.files[0]);
  });

  // Modal Subir Excel
  const uploadModal = document.getElementById('uploadModal');
  document.getElementById('btnOpenUpload').addEventListener('click', () => {
    const today = new Date().toISOString().split('T')[0];
    const uploadAuditDate = document.getElementById('uploadAuditDate');
    if (uploadAuditDate && !uploadAuditDate.value) {
      uploadAuditDate.value = today;
    }
    uploadModal.classList.remove('hidden');
  });
  document.getElementById('btnCloseUpload').addEventListener('click', () => uploadModal.classList.add('hidden'));
  document.getElementById('btnCancelUpload').addEventListener('click', () => uploadModal.classList.add('hidden'));
  document.getElementById('uploadForm').addEventListener('submit', handleExcelUpload);

  const dropZone = document.getElementById('dropZone');
  const excelFileInput = document.getElementById('excelFileInput');
  const dropZoneFileName = document.getElementById('dropZoneFileName');

  dropZone.addEventListener('click', () => excelFileInput.click());
  excelFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      dropZoneFileName.textContent = e.target.files[0].name;
    }
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('border-blue-500', 'bg-blue-50/50');
  });
  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('border-blue-500', 'bg-blue-50/50');
  });
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-blue-500', 'bg-blue-50/50');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      excelFileInput.files = e.dataTransfer.files;
      dropZoneFileName.textContent = e.dataTransfer.files[0].name;
    }
  });

  // Modal Correo
  const emailModal = document.getElementById('emailModal');
  document.getElementById('btnOpenEmailModal').addEventListener('click', openEmailModal);
  document.getElementById('btnCloseEmailModal').addEventListener('click', () => emailModal.classList.add('hidden'));
  document.getElementById('emailScopeSelector').addEventListener('change', renderEmailPreview);
  document.getElementById('btnCopyEmailTable').addEventListener('click', copyEmailTableToClipboard);

  // Descargar Excel
  document.getElementById('btnDownloadExcel').addEventListener('click', downloadValidatedExcel);

  // Eliminar Auditoría (si existe el botón en la interfaz)
  const btnDeleteAudit = document.getElementById('btnDeleteAudit');
  if (btnDeleteAudit) {
    btnDeleteAudit.addEventListener('click', deleteCurrentAudit);
  }

  // Modal Móvil QR
  const mobileQRModal = document.getElementById('mobileQRModal');
  const btnOpenMobileQR = document.getElementById('btnOpenMobileQR');
  if (btnOpenMobileQR) {
    btnOpenMobileQR.addEventListener('click', openMobileQRModal);
  }

  const btnCloseMobileQR = document.getElementById('btnCloseMobileQR');
  if (btnCloseMobileQR && mobileQRModal) {
    btnCloseMobileQR.addEventListener('click', () => mobileQRModal.classList.add('hidden'));
  }

  const btnQRModeCloud = document.getElementById('btnQRModeCloud');
  if (btnQRModeCloud) {
    btnQRModeCloud.addEventListener('click', () => {
      currentQRMode = 'cloud';
      renderQRCode();
    });
  }

  const btnQRModeLocal = document.getElementById('btnQRModeLocal');
  if (btnQRModeLocal) {
    btnQRModeLocal.addEventListener('click', () => {
      currentQRMode = 'local';
      renderQRCode();
    });
  }

  const btnCopyMobileUrl = document.getElementById('btnCopyMobileUrl');
  if (btnCopyMobileUrl) {
    btnCopyMobileUrl.addEventListener('click', () => {
      const url = getActiveMobileUrl();
      if (url) {
        navigator.clipboard.writeText(url).then(() => {
          showToast('Enlace copiado al portapapeles', 'success');
        }).catch(() => {
          showToast(`Enlace: ${url}`, 'info');
        });
      }
    });
  }

  // Modal de Confirmación Estilizado
  const btnConfirmCancel = document.getElementById('btnConfirmCancel');
  if (btnConfirmCancel) {
    btnConfirmCancel.addEventListener('click', () => closeConfirmModal(false));
  }
  const btnConfirmAccept = document.getElementById('btnConfirmAccept');
  if (btnConfirmAccept) {
    btnConfirmAccept.addEventListener('click', () => closeConfirmModal(true));
  }
  const confirmActionModal = document.getElementById('confirmActionModal');
  if (confirmActionModal) {
    confirmActionModal.addEventListener('click', (e) => {
      if (e.target === confirmActionModal) closeConfirmModal(false);
    });
  }

  // --------------------------------------------------------------------------
  // EVENT LISTENERS DEL CATÁLOGO DE REFERENCIAS
  // --------------------------------------------------------------------------
  const catalogSearchInput = document.getElementById('catalogSearchInput');
  const btnClearCatalogSearch = document.getElementById('btnClearCatalogSearch');
  if (catalogSearchInput) {
    catalogSearchInput.addEventListener('input', (e) => {
      catalogSearchQuery = e.target.value;
      if (btnClearCatalogSearch) btnClearCatalogSearch.classList.toggle('hidden', !catalogSearchQuery);
      applyCatalogFilters();
    });
  }

  if (btnClearCatalogSearch) {
    btnClearCatalogSearch.addEventListener('click', () => {
      catalogSearchQuery = '';
      if (catalogSearchInput) catalogSearchInput.value = '';
      btnClearCatalogSearch.classList.add('hidden');
      applyCatalogFilters();
    });
  }

  const btnCatalogGrid = document.getElementById('btnCatalogViewGrid');
  const btnCatalogTable = document.getElementById('btnCatalogViewTable');
  if (btnCatalogGrid && btnCatalogTable) {
    btnCatalogGrid.addEventListener('click', () => {
      catalogViewMode = 'grid';
      btnCatalogGrid.className = 'p-1.5 rounded-lg text-xs font-bold transition-all bg-white text-slate-900 shadow-2xs';
      btnCatalogTable.className = 'p-1.5 rounded-lg text-xs font-bold transition-all text-slate-500 hover:text-slate-900';
      applyCatalogFilters();
    });

    btnCatalogTable.addEventListener('click', () => {
      catalogViewMode = 'table';
      btnCatalogTable.className = 'p-1.5 rounded-lg text-xs font-bold transition-all bg-white text-slate-900 shadow-2xs';
      btnCatalogGrid.className = 'p-1.5 rounded-lg text-xs font-bold transition-all text-slate-500 hover:text-slate-900';
      applyCatalogFilters();
    });
  }

  const catGenderFilter = document.getElementById('catalogGenderFilter');
  if (catGenderFilter) {
    catGenderFilter.addEventListener('change', (e) => {
      catalogGenderFilter = e.target.value;
      applyCatalogFilters();
    });
  }

  const catTypeFilter = document.getElementById('catalogTypeFilter');
  if (catTypeFilter) {
    catTypeFilter.addEventListener('change', (e) => {
      catalogTypeFilter = e.target.value;
      applyCatalogFilters();
    });
  }

  const catPhotoFilter = document.getElementById('catalogPhotoFilter');
  if (catPhotoFilter) {
    catPhotoFilter.addEventListener('change', (e) => {
      catalogPhotoFilter = e.target.value;
      applyCatalogFilters();
    });
  }

  // --------------------------------------------------------------------------
  // EVENT LISTENERS DE LA SECCIÓN ARCHIVOS EXCEL
  // --------------------------------------------------------------------------
  const btnFilesUploadNew = document.getElementById('btnFilesUploadNew');
  if (btnFilesUploadNew) {
    btnFilesUploadNew.addEventListener('click', () => {
      const today = new Date().toISOString().split('T')[0];
      const uploadAuditDate = document.getElementById('uploadAuditDate');
      if (uploadAuditDate && !uploadAuditDate.value) {
        uploadAuditDate.value = today;
      }
      document.getElementById('uploadModal').classList.remove('hidden');
    });
  }

  const filesSearchInput = document.getElementById('filesSearchInput');
  if (filesSearchInput) {
    filesSearchInput.addEventListener('input', (e) => {
      filesSearchQuery = e.target.value;
      renderFilesSection();
    });
  }

  document.querySelectorAll('.files-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      filesFilter = chip.dataset.filesFilter || 'all';
      document.querySelectorAll('.files-chip').forEach(c => {
        const isActive = (c.dataset.filesFilter || 'all') === filesFilter;
        c.className = isActive
          ? 'files-chip active px-3 py-1 rounded-lg text-xs font-bold transition-all bg-emerald-600 text-white shadow-xs'
          : 'files-chip px-3 py-1 rounded-lg text-xs font-bold transition-all bg-white border border-slate-200 text-slate-700 hover:bg-slate-100';
      });
      renderFilesSection();
    });
  });

}

// ============================================================================
// HELPERS GENERALES
// ============================================================================
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function copyToClipboard(text, label = 'Código') {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    showToast(`${label} copiado: ${text}`, 'info');
  }).catch(() => {
    showToast(`${label}: ${text}`, 'info');
  });
}

// ============================================================================
// CONTROL DE PESTAÑAS PRINCIPALES (AUDITORÍA / CATÁLOGO / ARCHIVOS)
// ============================================================================
function initTabs() {
  const tabAudit = document.getElementById('tabBtnAudit');
  const tabCatalog = document.getElementById('tabBtnCatalog');
  const tabFiles = document.getElementById('tabBtnFiles');

  if (tabAudit) tabAudit.addEventListener('click', () => switchTab('audit'));
  if (tabCatalog) tabCatalog.addEventListener('click', () => switchTab('catalog'));
  if (tabFiles) tabFiles.addEventListener('click', () => switchTab('files'));
}

function switchTab(tabName) {
  currentMainTab = tabName;

  const tabAudit = document.getElementById('tabBtnAudit');
  const tabCatalog = document.getElementById('tabBtnCatalog');
  const tabFiles = document.getElementById('tabBtnFiles');

  const secAudit = document.getElementById('sectionAudit');
  const secCatalog = document.getElementById('sectionCatalog');
  const secFiles = document.getElementById('sectionFiles');
  const auditSelectorBar = document.getElementById('auditSelectorBar');

  const baseInactive = 'tab-nav-btn py-1.5 px-3 rounded-lg text-xs font-bold transition-all inline-flex items-center justify-center gap-1.5 shrink-0 text-slate-300 hover:text-white hover:bg-slate-800';

  if (tabAudit) {
    tabAudit.className = tabName === 'audit'
      ? 'tab-nav-btn active py-1.5 px-3 rounded-lg text-xs font-bold transition-all inline-flex items-center justify-center gap-1.5 shrink-0 bg-blue-600 text-white shadow-xs'
      : baseInactive;
  }
  if (tabCatalog) {
    tabCatalog.className = tabName === 'catalog'
      ? 'tab-nav-btn active py-1.5 px-3 rounded-lg text-xs font-bold transition-all inline-flex items-center justify-center gap-1.5 shrink-0 bg-amber-600 text-white shadow-xs'
      : baseInactive;
  }
  if (tabFiles) {
    tabFiles.className = tabName === 'files'
      ? 'tab-nav-btn active py-1.5 px-3 rounded-lg text-xs font-bold transition-all inline-flex items-center justify-center gap-1.5 shrink-0 bg-emerald-600 text-white shadow-xs'
      : baseInactive;
  }

  // Actualizar badges de pestañas con alto contraste
  const tabCatBadge = document.getElementById('tabCatalogBadge');
  const tabFilBadge = document.getElementById('tabFilesBadge');
  if (tabCatBadge) {
    tabCatBadge.className = tabName === 'catalog'
      ? 'ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-black bg-white/20 text-white border border-white/30 badge-pill'
      : 'ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-400/30 badge-pill';
  }
  if (tabFilBadge) {
    tabFilBadge.className = tabName === 'files'
      ? 'ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-black bg-white/20 text-white border border-white/30 badge-pill'
      : 'ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 badge-pill';
  }

  if (secAudit) secAudit.classList.toggle('hidden', tabName !== 'audit');
  if (auditSelectorBar) auditSelectorBar.classList.toggle('hidden', tabName !== 'audit');
  if (secCatalog) secCatalog.classList.toggle('hidden', tabName !== 'catalog');
  if (secFiles) secFiles.classList.toggle('hidden', tabName !== 'files');

  if (tabName === 'catalog') {
    if (catalogItems.length === 0) {
      loadCatalog();
    } else {
      applyCatalogFilters();
    }
  } else if (tabName === 'files') {
    renderFilesSection();
  }

  initIcons();
}

// ============================================================================
// CATÁLOGO MAESTRO DE REFERENCIAS (VISUALIZACIÓN DESCRIPTIVA SIN DIFERENCIAS)
// ============================================================================
async function loadCatalogStats() {
  try {
    const res = await fetch('/api/catalog/stats');
    if (!res.ok) return;
    catalogStats = await res.json();

    const badge = document.getElementById('tabCatalogBadge');
    if (badge) {
      badge.textContent = catalogStats.total_models || '0';
    }

    const typeSelect = document.getElementById('catalogTypeFilter');
    if (typeSelect && catalogStats.garment_types) {
      const currentVal = typeSelect.value;
      typeSelect.innerHTML = '<option value="all">Todas las prendas</option>';
      catalogStats.garment_types.forEach(gt => {
        const opt = document.createElement('option');
        opt.value = gt.type;
        opt.textContent = `${gt.type} (${gt.count})`;
        typeSelect.appendChild(opt);
      });
      if (currentVal && typeSelect.querySelector(`option[value="${currentVal}"]`)) {
        typeSelect.value = currentVal;
      }
    }
  } catch (err) {
    console.error('Error al cargar estadísticas del catálogo:', err);
  }
}

async function loadCatalog() {
  try {
    const res = await fetch('/api/catalog');
    if (!res.ok) throw new Error('Error al cargar catálogo');
    const data = await res.json();
    catalogItems = data.items || [];
    applyCatalogFilters();
  } catch (err) {
    console.error(err);
    showToast('Error al cargar el catálogo de prendas', 'error');
  }
}

function applyCatalogFilters() {
  const q = catalogSearchQuery.trim().toLowerCase();

  filteredCatalogItems = catalogItems.filter(item => {
    // 1. Filtro Género
    if (catalogGenderFilter !== 'all') {
      const g = String(item.gender || '').trim().toLowerCase();
      if (catalogGenderFilter.toLowerCase() !== g) return false;
    }

    // 2. Filtro Tipo de Prenda
    if (catalogTypeFilter !== 'all') {
      const t = String(item.garment_type || item.category || '').trim();
      if (t !== catalogTypeFilter) return false;
    }

    // 3. Filtro Foto
    if (catalogPhotoFilter === 'with_photo') {
      if (!item.photo_url) return false;
    } else if (catalogPhotoFilter === 'without_photo') {
      if (item.photo_url) return false;
    }

    // 4. Búsqueda textual
    if (q) {
      const matchRef = String(item.master_ref || '').toLowerCase().includes(q) ||
                       String(item.reference || '').toLowerCase().includes(q);
      const matchName = String(item.name || '').toLowerCase().includes(q);
      const matchType = String(item.garment_type || '').toLowerCase().includes(q);
      const matchSizes = Array.isArray(item.sizes) && item.sizes.some(s => String(s).toLowerCase().includes(q));
      const matchColors = Array.isArray(item.colors) && item.colors.some(c => String(c).toLowerCase().includes(q));
      const matchBarcodes = Array.isArray(item.barcodes) && item.barcodes.some(b => String(b).toLowerCase().includes(q));

      if (!matchRef && !matchName && !matchType && !matchSizes && !matchColors && !matchBarcodes) {
        return false;
      }
    }

    return true;
  });

  const countText = document.getElementById('catalogCountText');
  if (countText) {
    countText.textContent = `${filteredCatalogItems.length} de ${catalogItems.length}`;
  }

  const emptyState = document.getElementById('catalogEmptyState');
  const gridContainer = document.getElementById('catalogGridContainer');
  const tableContainer = document.getElementById('catalogTableContainer');

  if (filteredCatalogItems.length === 0) {
    if (emptyState) emptyState.classList.remove('hidden');
    if (gridContainer) gridContainer.classList.add('hidden');
    if (tableContainer) tableContainer.classList.add('hidden');
  } else {
    if (emptyState) emptyState.classList.add('hidden');
    if (catalogViewMode === 'grid') {
      if (gridContainer) {
        gridContainer.classList.remove('hidden');
        renderCatalogGrid(filteredCatalogItems);
      }
      if (tableContainer) tableContainer.classList.add('hidden');
    } else {
      if (tableContainer) {
        tableContainer.classList.remove('hidden');
        renderCatalogTable(filteredCatalogItems);
      }
      if (gridContainer) gridContainer.classList.add('hidden');
    }
  }

  initIcons();
}

function renderCatalogGrid(items) {
  const container = document.getElementById('catalogGridContainer');
  if (!container) return;

  container.innerHTML = items.map(item => {
    const primaryBarcode = (item.barcodes && item.barcodes.length > 0) ? item.barcodes[0] : null;
    const sizesHtml = (item.sizes && item.sizes.length > 0)
      ? item.sizes.map(sz => `<span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 text-[10px] font-black border border-slate-200">${escapeHtml(sz)}</span>`).join('')
      : '<span class="text-[11px] text-slate-400 italic">Sin tallas</span>';

    const colorsText = (item.colors && item.colors.length > 0)
      ? item.colors.slice(0, 3).join(', ') + (item.colors.length > 3 ? ` (+${item.colors.length - 3})` : '')
      : 'No registrado';

    let genderBadge = '';
    if (item.gender === 'Dama') {
      genderBadge = '<span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-pink-50 text-pink-700 border border-pink-200 badge-pill">👗 Dama (28)</span>';
    } else if (item.gender === 'Caballero') {
      genderBadge = '<span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-blue-50 text-blue-700 border border-blue-200 badge-pill">👔 Caballero (45)</span>';
    } else {
      genderBadge = '<span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 text-slate-700 badge-pill">General</span>';
    }

    const garmentTypeBadge = `<span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200 badge-pill">${escapeHtml(item.garment_type || 'Prenda')}</span>`;

    const imageSection = item.photo_url
      ? `<div class="relative w-full h-44 sm:h-48 bg-slate-100 flex items-center justify-center overflow-hidden group cursor-pointer" onclick="zoomCatalogPhoto('${item.photo_url}', '${escapeHtml(item.name)}', '${escapeHtml(item.master_ref)}')">
           <img src="${item.photo_url}" alt="${escapeHtml(item.name)}" class="w-full h-full object-contain p-2 group-hover:scale-105 transition-transform duration-200" loading="lazy">
           <div class="absolute top-2 right-2 flex items-center gap-1">
             <button type="button" onclick="event.stopPropagation(); triggerCatalogUploadPhoto('${escapeHtml(item.master_ref)}');" class="bg-slate-900/75 hover:bg-slate-900 text-white p-1.5 rounded-lg shadow-sm backdrop-blur-xs transition-colors" title="Cambiar foto universal">
               <i data-lucide="camera" class="w-3.5 h-3.5"></i>
             </button>
             <button type="button" onclick="event.stopPropagation(); deleteReferencePhoto('${escapeHtml(item.master_ref)}');" class="bg-red-600/85 hover:bg-red-700 text-white p-1.5 rounded-lg shadow-sm backdrop-blur-xs transition-colors" title="Eliminar foto incorrecta del catálogo">
               <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
             </button>
           </div>
         </div>`
      : `<div class="w-full h-44 sm:h-48 bg-slate-100 border-b border-slate-200/80 flex flex-col items-center justify-center p-3 text-center">
           <div class="w-11 h-11 rounded-full bg-slate-200 text-slate-400 flex items-center justify-center mb-1.5">
             <i data-lucide="camera" class="w-5 h-5"></i>
           </div>
           <span class="text-xs font-bold text-slate-600">Sin foto registrada</span>
           <button type="button" onclick="triggerCatalogUploadPhoto('${escapeHtml(item.master_ref)}')" class="mt-2.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-white text-xs font-bold rounded-lg shadow-xs inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer">
             <i data-lucide="camera" class="w-3.5 h-3.5 shrink-0"></i>
             <span>Subir Foto</span>
           </button>
         </div>`;

    return `
      <div class="bg-white rounded-2xl border border-slate-200/90 shadow-xs hover:shadow-md transition-all overflow-hidden flex flex-col justify-between">
        <div>
          ${imageSection}

          <div class="p-3.5 flex flex-col gap-2.5">
            <!-- Chips de Género y Tipo -->
            <div class="flex items-center gap-1.5 flex-wrap">
              ${genderBadge}
              ${garmentTypeBadge}
            </div>

            <!-- Referencia y Nombre -->
            <div>
              <span class="font-mono text-xs font-black text-slate-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-200/80 inline-block badge-pill">
                ${escapeHtml(item.master_ref)}
              </span>
              <h4 class="text-xs sm:text-sm font-bold text-slate-800 line-clamp-2 leading-snug mt-1" title="${escapeHtml(item.name)}">
                ${escapeHtml(item.name || 'Sin descripción')}
              </h4>
            </div>

            <!-- Tallas Disponibles -->
            <div class="pt-0.5">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Tallas:</span>
              <div class="flex flex-wrap gap-1 items-center">
                ${sizesHtml}
              </div>
            </div>

            <!-- Color -->
            <div class="text-[11px] text-slate-600 flex items-center gap-1.5">
              <span class="text-slate-400 font-medium">Color:</span>
              <span class="font-semibold text-slate-700 truncate" title="${escapeHtml(colorsText)}">${escapeHtml(colorsText)}</span>
            </div>

            <!-- Código EAN si existe -->
            ${primaryBarcode ? `
              <div class="flex items-center justify-between text-[11px] font-mono text-slate-500 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200/60">
                <span class="truncate">EAN: ${escapeHtml(primaryBarcode)}</span>
                <button type="button" onclick="copyToClipboard('${escapeHtml(primaryBarcode)}', 'Código EAN')" class="text-slate-400 hover:text-blue-600 p-1 rounded inline-flex items-center justify-center transition-colors shrink-0 cursor-pointer" title="Copiar código de barras">
                  <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                </button>
              </div>
            ` : ''}

            <!-- Conteo de apariciones en inventarios -->
            <div class="text-[10px] text-slate-400 flex items-center gap-1 font-medium pt-0.5">
              <i data-lucide="history" class="w-3 h-3 text-slate-400 shrink-0"></i>
              <span>Visto en ${item.audit_appearances || 1} inventarios</span>
            </div>
          </div>
        </div>

        <!-- Botón Inferior: Abrir en Auditoría -->
        <div class="p-3 pt-0">
          <button type="button" onclick="searchCatalogItemInAudit('${escapeHtml(item.master_ref)}')" class="w-full py-2.5 px-3 bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200/80 hover:border-blue-200 rounded-xl text-xs font-bold transition-all inline-flex items-center justify-center gap-2 shadow-2xs cursor-pointer">
            <i data-lucide="clipboard-check" class="w-4 h-4 text-blue-600 shrink-0"></i>
            <span>Consultar en Auditoría</span>
          </button>
        </div>

      </div>
    `;
  }).join('');
}

function renderCatalogTable(items) {
  const tbody = document.getElementById('catalogTableBody');
  if (!tbody) return;

  tbody.innerHTML = items.map(item => {
    const primaryBarcode = (item.barcodes && item.barcodes.length > 0) ? item.barcodes[0] : '-';
    const sizesHtml = (item.sizes && item.sizes.length > 0)
      ? item.sizes.map(sz => `<span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 text-[10px] font-black border border-slate-200 mr-1 badge-pill">${escapeHtml(sz)}</span>`).join('')
      : '<span class="text-slate-400 italic text-[11px]">-</span>';

    const photoCol = item.photo_url
      ? `<div class="w-10 h-10 rounded-lg bg-slate-100 overflow-hidden border border-slate-200 cursor-pointer shrink-0" onclick="zoomCatalogPhoto('${item.photo_url}', '${escapeHtml(item.name)}', '${escapeHtml(item.master_ref)}')">
           <img src="${item.photo_url}" alt="${escapeHtml(item.name)}" class="w-full h-full object-cover">
         </div>`
      : `<button type="button" onclick="triggerCatalogUploadPhoto('${escapeHtml(item.master_ref)}')" class="w-10 h-10 rounded-lg bg-slate-100 hover:bg-amber-50 border border-slate-200 hover:border-amber-300 text-slate-400 hover:text-amber-600 inline-flex items-center justify-center transition-colors shrink-0 cursor-pointer" title="Subir foto">
           <i data-lucide="camera" class="w-4 h-4"></i>
         </button>`;

    return `
      <tr class="hover:bg-slate-50/80 transition-colors">
        <td class="py-2.5 px-3 align-middle">${photoCol}</td>
        <td class="py-2.5 px-3 align-middle font-mono font-black text-slate-900 text-xs">${escapeHtml(item.master_ref)}</td>
        <td class="py-2.5 px-3 align-middle font-bold text-slate-800 max-w-xs truncate" title="${escapeHtml(item.name)}">${escapeHtml(item.name || 'Sin nombre')}</td>
        <td class="py-2.5 px-2 align-middle">
          <div class="flex items-center gap-1 flex-wrap">
            <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 badge-pill">${escapeHtml(item.gender || 'General')}</span>
            <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 badge-pill">${escapeHtml(item.garment_type || '')}</span>
          </div>
        </td>
        <td class="py-2.5 px-2 align-middle"><div class="flex items-center flex-wrap gap-1">${sizesHtml}</div></td>
        <td class="py-2.5 px-2 align-middle">
          <div class="flex items-center gap-1 font-mono text-[11px] text-slate-600">
            <span>${escapeHtml(primaryBarcode)}</span>
            ${primaryBarcode !== '-' ? `<button type="button" onclick="copyToClipboard('${primaryBarcode}', 'Código EAN')" class="text-slate-400 hover:text-blue-600 p-0.5 cursor-pointer inline-flex items-center justify-center" title="Copiar EAN"><i data-lucide="copy" class="w-3 h-3"></i></button>` : ''}
          </div>
        </td>
        <td class="py-2.5 px-3 align-middle text-center">
          <button type="button" onclick="searchCatalogItemInAudit('${escapeHtml(item.master_ref)}')" class="px-2.5 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-xs font-bold transition-colors inline-flex items-center justify-center gap-1.5 whitespace-nowrap cursor-pointer">
            <i data-lucide="clipboard-check" class="w-3.5 h-3.5 shrink-0"></i>
            <span>Auditar</span>
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function searchCatalogItemInAudit(ref) {
  switchTab('audit');
  const searchInput = document.getElementById('searchInput');
  const btnClearSearch = document.getElementById('btnClearSearch');
  if (searchInput) {
    searchInput.value = ref;
    searchQuery = ref;
    if (btnClearSearch) btnClearSearch.classList.remove('hidden');
    applyFilters();
  }
  showToast(`Filtrando referencia ${ref} en auditoría`, 'info');
}

function triggerCatalogUploadPhoto(ref) {
  catalogPhotoUploadRef = ref;
  let fileInput = document.getElementById('catalogPhotoUploadInput');
  if (!fileInput) {
    fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'catalogPhotoUploadInput';
    fileInput.accept = 'image/*';
    fileInput.className = 'hidden';
    fileInput.addEventListener('change', handleCatalogPhotoFileChange);
    document.body.appendChild(fileInput);
  }
  fileInput.value = '';
  fileInput.click();
}

async function handleCatalogPhotoFileChange(e) {
  if (!e.target.files || !e.target.files[0] || !catalogPhotoUploadRef) return;
  const file = e.target.files[0];
  const ref = catalogPhotoUploadRef;
  const formData = new FormData();
  formData.append('file', file);

  try {
    showToast(`Subiendo foto para referencia ${ref}...`, 'info');
    const res = await fetch(`/api/references/${encodeURIComponent(ref)}/photo`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error('Error al subir la foto');
    const data = await res.json();
    showToast('Foto asignada universalmente al catálogo', 'success');

    // Actualizar en el catálogo local
    catalogItems.forEach(i => {
      if (i.master_ref === ref || i.reference === ref) {
        i.photo_url = data.photo_url;
      }
    });

    // Actualizar en allItems si está en la auditoría activa
    allItems.forEach(i => {
      if (i.reference === ref || i.base_reference === ref) {
        i.photo_url = data.photo_url;
      }
    });

    applyCatalogFilters();
    loadCatalogStats();
    if (currentMainTab === 'audit') {
      renderItems();
    }
  } catch (err) {
    console.error(err);
    showToast('Error al guardar la foto en el servidor', 'error');
  }
}

async function deleteReferencePhoto(reference) {
  if (!reference) return;

  const cleanRef = String(reference).trim();
  const confirmDelete = confirm(`¿Estás seguro de que deseas eliminar la foto de la referencia ${cleanRef}?`);
  if (!confirmDelete) return;

  try {
    const res = await fetch(`/api/references/${encodeURIComponent(cleanRef)}/photo`, {
      method: 'DELETE'
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Error al eliminar la foto');
    }

    // Actualizar en catálogo local
    catalogItems.forEach(item => {
      if (item.master_ref === cleanRef || item.reference === cleanRef || item.base_reference === cleanRef) {
        item.photo_url = null;
      }
    });

    // Actualizar en allItems de la auditoría si coincide
    allItems.forEach(i => {
      if (i.reference === cleanRef || i.base_reference === cleanRef) {
        i.photo_url = null;
        if (i.sibling_sizes) {
          i.sibling_sizes.forEach(sib => { sib.photo_url = null; });
        }
      }
    });

    // Cerrar modal de zoom si está abierto
    const zoomModal = document.getElementById('catalogZoomModal');
    if (zoomModal) zoomModal.classList.add('hidden');

    // Refrescar vistas
    applyCatalogFilters();
    loadCatalogStats();
    if (currentMainTab === 'audit') {
      renderItems();
      updateKpis();
    }

    showToast(`Foto de ${cleanRef} eliminada del catálogo`, 'info');
  } catch (err) {
    console.error('Error al eliminar foto de referencia:', err);
    showToast(`No se pudo eliminar la foto: ${err.message}`, 'error');
  }
}
window.deleteReferencePhoto = deleteReferencePhoto;

function zoomCatalogPhoto(photoUrl, title, ref) {
  if (!photoUrl) return;
  let zoomModal = document.getElementById('catalogZoomModal');
  if (!zoomModal) {
    zoomModal = document.createElement('div');
    zoomModal.id = 'catalogZoomModal';
    zoomModal.className = 'fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-xs animate-fade-in cursor-zoom-out';
    zoomModal.onclick = (e) => {
      if (e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
        zoomModal.classList.add('hidden');
      }
    };
    document.body.appendChild(zoomModal);
  }

  zoomModal.innerHTML = `
    <div class="relative max-w-xl w-full max-h-[90vh] bg-white rounded-2xl overflow-hidden shadow-2xl flex flex-col cursor-default" onclick="event.stopPropagation()">
      <div class="p-3.5 bg-slate-900 text-white flex items-center justify-between">
        <div class="min-w-0 pr-2">
          <div class="font-mono text-xs text-amber-400 font-black">${escapeHtml(ref)}</div>
          <div class="text-xs sm:text-sm font-bold truncate">${escapeHtml(title)}</div>
        </div>
        <button type="button" onclick="document.getElementById('catalogZoomModal').classList.add('hidden')" class="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer">
          <i data-lucide="x" class="w-5 h-5"></i>
        </button>
      </div>
      <div class="p-4 bg-slate-100 flex items-center justify-center overflow-auto max-h-[70vh]">
        <img src="${photoUrl}" alt="${escapeHtml(title)}" class="max-h-[65vh] w-auto object-contain rounded-lg shadow-sm">
      </div>
      <div class="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between gap-2 flex-wrap">
        <div class="flex items-center gap-2">
          <button type="button" onclick="triggerCatalogUploadPhoto('${escapeHtml(ref)}'); document.getElementById('catalogZoomModal').classList.add('hidden');" class="px-3 py-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer">
            <i data-lucide="camera" class="w-3.5 h-3.5"></i>
            <span>Cambiar Foto</span>
          </button>
          <button type="button" onclick="deleteReferencePhoto('${escapeHtml(ref)}');" class="px-3 py-1.5 rounded-lg bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer" title="Eliminar foto incorrecta">
            <i data-lucide="trash-2" class="w-3.5 h-3.5 text-red-600"></i>
            <span>Eliminar Foto</span>
          </button>
        </div>
        <button type="button" onclick="searchCatalogItemInAudit('${escapeHtml(ref)}'); document.getElementById('catalogZoomModal').classList.add('hidden');" class="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer">
          <i data-lucide="clipboard-check" class="w-3.5 h-3.5"></i>
          <span>Buscar en Auditoría</span>
        </button>
      </div>
    </div>
  `;
  zoomModal.classList.remove('hidden');
  initIcons();
}

// ============================================================================
// SECCIÓN ARCHIVOS EXCEL (INVENTARIOS CARGADOS)
// ============================================================================
function renderFilesSection() {
  const container = document.getElementById('filesListContainer');
  const emptyState = document.getElementById('filesEmptyState');
  if (!container) return;

  const sq = filesSearchQuery.trim().toLowerCase();

  const filtered = allAudits.filter(audit => {
    const aDate = audit.audit_date || (audit.uploaded_at ? audit.uploaded_at.substring(0, 10) : '');
    const dayOfWeek = getDayOfWeekFromDateStr(aDate);

    if (filesFilter === 'lunes') {
      if (dayOfWeek !== 1) return false;
    } else if (filesFilter === 'miercoles') {
      if (dayOfWeek !== 3) return false;
    } else if (filesFilter === 'this_month') {
      if (!aDate) return false;
      const today = new Date();
      const yr = today.getFullYear();
      const mo = String(today.getMonth() + 1).padStart(2, '0');
      if (!aDate.startsWith(`${yr}-${mo}`)) return false;
    }

    if (sq) {
      const matchName = String(audit.name || '').toLowerCase().includes(sq);
      const matchFile = String(audit.filename || '').toLowerCase().includes(sq);
      const matchDate = String(aDate).toLowerCase().includes(sq);
      if (!matchName && !matchFile && !matchDate) return false;
    }

    return true;
  });

  if (filtered.length === 0) {
    container.classList.add('hidden');
    if (emptyState) emptyState.classList.remove('hidden');
    return;
  }

  container.classList.remove('hidden');
  if (emptyState) emptyState.classList.add('hidden');

  container.innerHTML = filtered.map(audit => {
    const aDate = audit.audit_date || (audit.uploaded_at ? audit.uploaded_at.substring(0, 10) : '');
    const dateFormatted = formatAuditDateFull(aDate);
    const isCurrent = audit.id === currentAuditId;

    return `
      <div class="bg-white rounded-2xl p-4 sm:p-5 border ${
        isCurrent ? 'border-blue-400 bg-blue-50/20 ring-1 ring-blue-300' : 'border-slate-200/90'
      } shadow-xs hover:shadow-md transition-all flex flex-col justify-between gap-3.5">
        
        <div>
          <!-- Cabecera de la Tarjeta de Archivo -->
          <div class="flex items-start justify-between gap-2">
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200/80 text-emerald-600 flex items-center justify-center shrink-0">
                <i data-lucide="file-spreadsheet" class="w-5 h-5"></i>
              </div>
              <div class="min-w-0">
                <h3 class="text-xs sm:text-sm font-black text-slate-900 truncate" title="${escapeHtml(audit.name)}">
                  ${escapeHtml(audit.name)}
                </h3>
                <span class="text-[11px] font-semibold text-slate-500 block truncate">
                  ${dateFormatted || 'Fecha sin registrar'}
                </span>
              </div>
            </div>
            <span class="font-mono text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 shrink-0">
              #${audit.id}
            </span>
          </div>

          <!-- Métricas de la lectura -->
          <div class="grid grid-cols-3 gap-1.5 mt-3 pt-3 border-t border-slate-100 text-center">
            <div class="bg-slate-50 p-2 rounded-xl border border-slate-100">
              <span class="text-[10px] text-slate-400 font-bold block uppercase">Total</span>
              <span class="text-xs sm:text-sm font-black text-slate-900 font-mono">${audit.total_items}</span>
            </div>
            <div class="bg-red-50/70 p-2 rounded-xl border border-red-100">
              <span class="text-[10px] text-red-600 font-bold block uppercase">Faltantes</span>
              <span class="text-xs sm:text-sm font-black text-red-700 font-mono">${audit.total_faltantes || 0}</span>
            </div>
            <div class="bg-blue-50/70 p-2 rounded-xl border border-blue-100">
              <span class="text-[10px] text-blue-600 font-bold block uppercase">Sobrantes</span>
              <span class="text-xs sm:text-sm font-black text-blue-700 font-mono">${audit.total_sobrantes || 0}</span>
            </div>
          </div>

          <!-- Nombre de archivo original -->
          <div class="mt-2.5 text-[11px] text-slate-400 truncate flex items-center gap-1 font-mono">
            <i data-lucide="paperclip" class="w-3 h-3 shrink-0"></i>
            <span class="truncate">${escapeHtml(audit.filename || 'inventario.xlsx')}</span>
          </div>
        </div>

        <!-- Acciones Directas del Archivo -->
        <div class="flex items-center gap-1.5 pt-2.5 border-t border-slate-100">
          <a href="/api/audits/${audit.id}/download-original" download class="flex-1 py-2 px-2.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 active:bg-emerald-200 text-emerald-800 text-xs font-bold border border-emerald-200/80 transition-colors inline-flex items-center justify-center gap-1.5 shadow-2xs whitespace-nowrap" title="Descargar archivo Excel original subido">
            <i data-lucide="download" class="w-3.5 h-3.5 text-emerald-600 shrink-0"></i>
            <span>Descargar .xlsx</span>
          </a>

          <button type="button" onclick="selectAuditAndSwitchToAuditTab(${audit.id})" class="flex-1 py-2 px-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-bold transition-colors inline-flex items-center justify-center gap-1.5 shadow-2xs whitespace-nowrap cursor-pointer" title="Abrir y conciliar en pestaña Auditoría">
            <i data-lucide="clipboard-check" class="w-3.5 h-3.5 shrink-0"></i>
            <span>Auditar</span>
          </button>

          <button type="button" onclick="deleteAuditFromHistory(${audit.id})" class="w-9 h-9 rounded-xl bg-slate-100 hover:bg-red-50 text-slate-400 hover:text-red-600 border border-slate-200 hover:border-red-200 transition-colors shrink-0 inline-flex items-center justify-center cursor-pointer" title="Eliminar este archivo de inventario">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
          </button>
        </div>

      </div>
    `;
  }).join('');

  initIcons();
}

async function selectAuditAndSwitchToAuditTab(auditId) {
  switchTab('audit');
  await selectAuditFromHistory(auditId);
}

// Exponer funciones en window para que estén disponibles en atributos HTML onclick
window.switchTab = switchTab;
window.zoomCatalogPhoto = zoomCatalogPhoto;
window.triggerCatalogUploadPhoto = triggerCatalogUploadPhoto;
window.searchCatalogItemInAudit = searchCatalogItemInAudit;
window.selectAuditAndSwitchToAuditTab = selectAuditAndSwitchToAuditTab;
window.copyToClipboard = copyToClipboard;


// ============================================================================
// TOAST NOTIFICACIONES
// ============================================================================
let toastTimeout = null;
function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  const toastIcon = document.getElementById('toastIcon');
  const toastMessage = document.getElementById('toastMessage');

  clearTimeout(toastTimeout);

  let iconName = 'info';
  let bgColor = 'bg-slate-900';

  if (type === 'success') {
    iconName = 'check-circle';
    bgColor = 'bg-emerald-800';
  } else if (type === 'error') {
    iconName = 'alert-octagon';
    bgColor = 'bg-red-800';
  } else if (type === 'warning') {
    iconName = 'alert-triangle';
    bgColor = 'bg-amber-800';
  }

  toast.className = `fixed bottom-5 right-5 z-50 transform transition-all duration-300 ${bgColor} text-white text-xs font-medium px-4 py-3 rounded-xl shadow-xl flex items-center gap-2 translate-y-0 opacity-100`;
  toastIcon.innerHTML = `<i data-lucide="${iconName}" class="w-4 h-4"></i>`;
  toastMessage.textContent = message;

  initIcons();

  toastTimeout = setTimeout(() => {
    toast.classList.add('translate-y-20', 'opacity-0');
  }, 4000);
}

// ============================================================================
// SOPORTE PWA, SERVICE WORKER E INSTALACIÓN EN DISPOSITIVOS MÓVILES
// ============================================================================
function initPwaSupport() {
  // 1. Registro del Service Worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then((reg) => {
        console.log('[FARO PWA] Service Worker registrado correctamente:', reg.scope);
      })
      .catch((err) => {
        console.warn('[FARO PWA] Fallo al registrar Service Worker:', err);
      });
  }

  // 2. Control de estado Online / Offline
  function updateOnlineStatus() {
    const banner = document.getElementById('offlineBanner');
    if (banner) {
      banner.classList.toggle('hidden', navigator.onLine);
    }
  }

  window.addEventListener('online', () => {
    updateOnlineStatus();
    showToast('Conexión restablecida en línea', 'success');
  });

  window.addEventListener('offline', () => {
    updateOnlineStatus();
    showToast('Estás navegando sin conexión', 'warning');
  });

  updateOnlineStatus();

  // 3. Manejo de Instalación de la PWA
  let deferredPrompt = null;
  const btnInstall = document.getElementById('btnInstallPWA');
  const pwaModal = document.getElementById('pwaInstallModal');
  const btnClosePwa = document.getElementById('btnClosePwaModal');

  if (btnClosePwa && pwaModal) {
    btnClosePwa.onclick = () => pwaModal.classList.add('hidden');
  }

  // Para Android, Chrome, Edge y navegadores Chromium
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (btnInstall) {
      btnInstall.classList.remove('hidden');
      btnInstall.onclick = async () => {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log('[FARO PWA] Respuesta de instalación del usuario:', outcome);
        deferredPrompt = null;
        btnInstall.classList.add('hidden');
      };
    }
  });

  window.addEventListener('appinstalled', () => {
    if (btnInstall) btnInstall.classList.add('hidden');
    deferredPrompt = null;
    showToast('¡FARO instalada con éxito en tu pantalla de inicio!', 'success');
  });

  // Para iOS Safari (iPhone / iPad donde no se dispara beforeinstallprompt)
  const isIos = /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase());
  const isStandalone = window.navigator.standalone || window.matchMedia('(display-mode: standalone)').matches;

  if (isIos && !isStandalone) {
    if (btnInstall) {
      btnInstall.classList.remove('hidden');
      btnInstall.onclick = () => {
        if (pwaModal) pwaModal.classList.remove('hidden');
      };
    }
  }
}

