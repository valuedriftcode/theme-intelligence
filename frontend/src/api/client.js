import axios from 'axios';

const API_BASE_URL = 'http://localhost:5001/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Transform RRG API response into chart-ready array
function transformRRGData(rrg) {
  // rrg is { TICKER: { current: {rs_ratio, rs_momentum}, history: [...] }, ... }
  return Object.entries(rrg).map(([ticker, data]) => ({
    ticker,
    rsRatio: data.current.rs_ratio,
    rsMomentum: data.current.rs_momentum,
    history: (data.history || []).map(h => ({
      date: h.date,
      rsRatio: h.rs_ratio,
      rsMomentum: h.rs_momentum,
    })),
  }));
}

// Market overview
export const getMarketOverview = async () => {
  const response = await client.get('/market/overview');
  if (response.data.status === 'error') {
    throw new Error(response.data.error || 'Market data unavailable');
  }
  return response.data.data?.indices || [];
};

// Sectors RRG -> returns chart-ready array
export const getSectorsRRG = async () => {
  const response = await client.get('/sectors/rrg');
  return transformRRGData(response.data.data || {});
};

// Countries RRG -> returns chart-ready array
export const getCountriesRRG = async () => {
  const response = await client.get('/countries/rrg');
  return transformRRGData(response.data.data || {});
};

// All themes
export const getThemes = async () => {
  const response = await client.get('/themes');
  return response.data.data || [];
};

// Theme RRG -> returns chart-ready array
export const getThemeRRG = async (themeId) => {
  const response = await client.get(`/themes/${themeId}/rrg`);
  return transformRRGData(response.data.rrg_data || {});
};

// Theme RRG baskets (equal-weighted)
export const getThemeRRGBaskets = async () => {
  const response = await client.get('/themes/rrg-baskets');
  return Object.entries(response.data.data || {}).map(([name, data]) => ({
    ticker: name,
    rsRatio: data.current.rs_ratio,
    rsMomentum: data.current.rs_momentum,
    isBasket: true,
    history: (data.history || []).map(h => ({
      date: h.date,
      rsRatio: h.rs_ratio,
      rsMomentum: h.rs_momentum,
    })),
  }));
};

// Create theme
export const createTheme = async (themeData) => {
  const response = await client.post('/themes', themeData);
  return response.data.data;
};

// Update theme
export const updateTheme = async (themeId, themeData) => {
  const response = await client.put(`/themes/${themeId}`, themeData);
  return response.data.data;
};

// Delete theme
export const deleteTheme = async (themeId) => {
  const response = await client.delete(`/themes/${themeId}`);
  return response.data;
};

// Suggest tickers for a theme (longer timeout for first-run info fetching)
export const suggestTickers = async (themeId, count = 8) => {
  const response = await client.post(
    `/themes/${themeId}/suggest-tickers`,
    { count },
    { timeout: 60000 }
  );
  return response.data.data || [];
};

// Signals
export const getSignals = async () => {
  const response = await client.get('/signals');
  return response.data.data || [];
};

// Stock Research
export const getStockResearch = async (ticker) => {
  const response = await client.get(`/stocks/${ticker}/research`);
  return response.data.data;
};

export const updateStockResearch = async (ticker, data) => {
  const response = await client.put(`/stocks/${ticker}/research`, data);
  return response.data.data;
};

export const addResearchNote = async (ticker, content, entryType = 'note') => {
  const response = await client.post(`/stocks/${ticker}/notes`, {
    content,
    entry_type: entryType,
  });
  return response.data.data;
};

export const refreshStockAnalysis = async (ticker) => {
  const response = await client.post(`/stocks/${ticker}/refresh`);
  return response.data.data;
};

export const getStocksByStatus = async (status = 'watchlist') => {
  const response = await client.get(`/stocks/watchlist?status=${status}`);
  return response.data.data || [];
};

export const searchResearch = async (query) => {
  const response = await client.get(`/stocks/search?q=${encodeURIComponent(query)}`);
  return response.data.data || [];
};

// Heatmap
export const getHeatmap = async (period = '1d', themeId = null) => {
  const params = { period };
  if (themeId) params.theme_id = themeId;
  const response = await client.get('/heatmap', { params, timeout: 60000 });
  return response.data;
};

// Ticker name lookup
export const getTickerNames = async (tickers) => {
  const response = await client.post('/tickers/names', { tickers });
  return response.data.data || {};
};

export default client;
