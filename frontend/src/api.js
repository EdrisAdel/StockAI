const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function json(res) {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export async function askQuestion(question) {
  return json(
    await fetch(`${API}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    })
  );
}

export async function getDailyMovers(n = 10) {
  return json(await fetch(`${API}/movers?n=${n}`));
}

export async function getPreset(name, n = 50) {
  return json(await fetch(`${API}/presets/${name}?n=${n}`));
}

export async function getStockDetail(ticker, period = "1M") {
  return json(await fetch(`${API}/stock/${ticker}/detail?period=${period}`));
}

export async function manualScreen(filters = [], sectors = [], sortBy = "ret_20d", sortOrder = "desc", n = 50) {
  return json(
    await fetch(`${API}/screen/manual`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filters, sectors, sort_by: sortBy, sort_order: sortOrder, n }),
    })
  );
}
