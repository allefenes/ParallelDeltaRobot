// Arayüz metinleri: /i18n/<dil>.json kataloğu; eksik anahtar anahtarın kendisine düşer.
let catalog = {};

export async function loadCatalog(lang = "tr") {
  try {
    const res = await fetch(`/i18n/${lang}.json`, { cache: "no-cache" });
    if (res.ok) catalog = await res.json();
  } catch {
    catalog = {};
  }
}

export function has(key) {
  return Object.prototype.hasOwnProperty.call(catalog, key);
}

// t("anahtar", {ad: değer}) -> metin; {ad} yer tutucuları doldurulur.
export function t(key, params = {}) {
  const text = Object.prototype.hasOwnProperty.call(catalog, key) ? catalog[key] : key;
  return text.replace(/\{([a-zA-Z0-9_]+)\}/g, (m, name) =>
    Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : m,
  );
}

// data-i18n (metin), data-i18n-placeholder, data-i18n-title, data-i18n-aria-label özniteliklerini doldurur.
export function applyI18n(root = document) {
  for (const el of root.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  const attrs = { i18nPlaceholder: "placeholder", i18nTitle: "title", i18nAriaLabel: "aria-label" };
  for (const [ds, attr] of Object.entries(attrs)) {
    const sel = "[data-" + ds.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase()) + "]";
    for (const el of root.querySelectorAll(sel)) el.setAttribute(attr, t(el.dataset[ds]));
  }
}
