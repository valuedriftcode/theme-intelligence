import React, { useState, useEffect, useCallback } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, ZAxis, Customized,
} from 'recharts';
import { getSectorsRRG, getThemeRRG, getThemes, getThemeRRGBaskets, getCountriesRRG, getTickerNames } from '../api/client';

const CENTER = 100; // Standard JdK RRG centers at 100 (ratio-to-SMA)

const SECTOR_NAMES = {
  XLK: 'Technology', XLF: 'Financials', XLE: 'Energy',
  XLV: 'Healthcare', XLI: 'Industrials', XLP: 'Consumer Staples',
  XLU: 'Utilities', XLB: 'Materials', XLC: 'Communications',
  XLRE: 'Real Estate', XLY: 'Consumer Disc.',
};

const COUNTRY_NAMES = {
  // Americas
  SPY: 'United States', EWC: 'Canada', EWZ: 'Brazil',
  EWW: 'Mexico', ARGT: 'Argentina', ECH: 'Chile', EPU: 'Peru',
  // Europe
  EWU: 'United Kingdom', EWG: 'Germany', EWQ: 'France',
  EWI: 'Italy', EWP: 'Spain', EWN: 'Netherlands', EWL: 'Switzerland',
  EWD: 'Sweden', EWO: 'Austria', EWK: 'Belgium', EDEN: 'Denmark',
  EIRL: 'Ireland', EPOL: 'Poland',
  // Asia-Pacific
  EWJ: 'Japan', EWY: 'South Korea', EWT: 'Taiwan', FXI: 'China',
  INDA: 'India', EWH: 'Hong Kong', EWS: 'Singapore', EWM: 'Malaysia',
  THD: 'Thailand', VNM: 'Vietnam', ENZL: 'New Zealand', EWA: 'Australia',
  // Middle East & Africa
  EIS: 'Israel', KSA: 'Saudi Arabia', QAT: 'Qatar', UAE: 'UAE',
  EZA: 'South Africa',
};

const TICKER_COLORS = [
  '#00ff88', '#ff6b6b', '#4ecdc4', '#f7b731', '#45b7d1',
  '#5f27cd', '#ff9ff3', '#54a0ff', '#00d2d3', '#feca57',
  '#ff6348', '#7bed9f', '#a29bfe',
];

const BASKET_COLORS = [
  '#ffaa00', '#ff55ff', '#55ffff', '#ff8844',
];

const METHODOLOGY_TEXT = {
  rrg: `Relative Rotation Graphs (RRG) visualize relative strength and momentum vs. SPY.

Parameters: Weekly data, 14-week lookback, 5-week trail.

RS-Ratio (X-axis): RS-Line as % of its 14-week moving average. >100 = outperforming SPY, <100 = underperforming.

RS-Momentum (Y-axis): RS-Ratio as % of its 14-week moving average. >100 = improving, <100 = deteriorating.

Quadrants rotate clockwise: Leading → Weakening → Lagging → Improving.`,
  sectors: `11 S&P 500 GICS sector SPDR ETFs vs. SPY:
XLK (Technology), XLF (Financials), XLE (Energy), XLV (Healthcare), XLI (Industrials), XLP (Consumer Staples), XLU (Utilities), XLB (Materials), XLC (Communications), XLRE (Real Estate), XLY (Consumer Discretionary).`,
  countries: `37 single-country ETFs vs. ACWI (global benchmark).

Covers Americas, Europe, Asia-Pacific, Middle East & Africa. Each country's relative strength is measured against the MSCI All Country World Index (ACWI) — the global market average.

Hover over any point to see the country name and current readings.`,
  baskets: `Theme baskets (◆) show each custom theme's aggregate RRG position.

Equal-weighted average of constituent tickers' RS-Ratio and RS-Momentum. Trail history is also averaged across constituents.`,
};

const InfoTooltip = ({ text }) => {
  const [show, setShow] = useState(false);
  return (
    <span style={{ position: 'relative', display: 'inline-block', marginLeft: '6px' }}>
      <span
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#2a2a2a',
          color: '#888', fontSize: '10px', cursor: 'help', border: '1px solid #444',
          fontWeight: 'bold', userSelect: 'none',
        }}
      >
        i
      </span>
      {show && (
        <div style={{
          position: 'absolute', top: '24px', left: '50%', transform: 'translateX(-50%)',
          width: '340px', padding: '12px 14px', backgroundColor: '#0a0a0a',
          border: '1px solid #3a3a3a', borderRadius: '6px', color: '#ccc',
          fontSize: '11px', lineHeight: '1.5', whiteSpace: 'pre-wrap', zIndex: 100,
          boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
        }}>
          {text}
        </div>
      )}
    </span>
  );
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  const quadrant = d.rsRatio >= CENTER
    ? (d.rsMomentum >= CENTER ? 'Leading' : 'Weakening')
    : (d.rsMomentum >= CENTER ? 'Improving' : 'Lagging');
  const sectorName = SECTOR_NAMES[d.ticker] || COUNTRY_NAMES[d.ticker] || d.companyName;
  const latestDate = d.history && d.history.length > 0 ? d.history[d.history.length - 1].date : null;
  return (
    <div style={{
      backgroundColor: '#0a0a0a', border: '1px solid #2a2a2a',
      padding: '10px 14px', borderRadius: '6px', color: '#fff', fontSize: '13px',
    }}>
      <div style={{ fontWeight: 'bold', color: d.isBasket ? '#ffaa00' : '#00ff88', marginBottom: '4px' }}>
        {d.ticker}{d.isBasket ? ' (theme basket)' : sectorName ? ` — ${sectorName}` : ''}
      </div>
      <div>RS-Ratio: {d.rsRatio?.toFixed(2)}</div>
      <div>RS-Momentum: {d.rsMomentum?.toFixed(2)}</div>
      <div style={{ color: '#888', marginTop: '4px', fontSize: '11px' }}>
        Quadrant: {quadrant}
        {latestDate && <span style={{ marginLeft: '8px' }}>Week of {latestDate}</span>}
      </div>
    </div>
  );
};

const QuadrantLayer = (props) => {
  const { xAxisMap, yAxisMap } = props;
  if (!xAxisMap || !yAxisMap) return null;
  const xAxis = Object.values(xAxisMap)[0];
  const yAxis = Object.values(yAxisMap)[0];
  if (!xAxis || !yAxis || !xAxis.scale || !yAxis.scale) return null;

  const cx = xAxis.scale(CENTER);
  const cy = yAxis.scale(CENTER);
  const l = xAxis.x;
  const t = yAxis.y;
  const r = l + xAxis.width;
  const b = t + yAxis.height;

  return (
    <g>
      <rect x={cx} y={t} width={r - cx} height={cy - t} fill="rgba(0,180,80,0.03)" />
      <rect x={cx} y={cy} width={r - cx} height={b - cy} fill="rgba(200,180,0,0.03)" />
      <rect x={l} y={cy} width={cx - l} height={b - cy} fill="rgba(200,50,50,0.03)" />
      <rect x={l} y={t} width={cx - l} height={cy - t} fill="rgba(50,100,200,0.03)" />
      <text x={r - 8} y={t + 18} textAnchor="end" fill="#00aa66" fontSize={11} fontWeight="bold" opacity={0.35}>LEADING</text>
      <text x={r - 8} y={b - 8} textAnchor="end" fill="#bbaa00" fontSize={11} fontWeight="bold" opacity={0.35}>WEAKENING</text>
      <text x={l + 8} y={b - 8} textAnchor="start" fill="#aa4444" fontSize={11} fontWeight="bold" opacity={0.35}>LAGGING</text>
      <text x={l + 8} y={t + 18} textAnchor="start" fill="#4488aa" fontSize={11} fontWeight="bold" opacity={0.35}>IMPROVING</text>
    </g>
  );
};

const TrailLayer = ({ chartData, hoveredTicker }) => (props) => {
  const { xAxisMap, yAxisMap } = props;
  if (!xAxisMap || !yAxisMap) return null;
  const xAxis = Object.values(xAxisMap)[0];
  const yAxis = Object.values(yAxisMap)[0];
  if (!xAxis || !yAxis || !xAxis.scale || !yAxis.scale) return null;

  const hasHover = hoveredTicker != null;

  return (
    <g>
      {chartData.map((item, idx) => {
        if (!item.history || item.history.length < 2) return null;
        const isHovered = item.ticker === hoveredTicker;
        const color = item.isBasket
          ? BASKET_COLORS[idx % BASKET_COLORS.length]
          : TICKER_COLORS[idx % TICKER_COLORS.length];
        const pts = item.history.map(h => ({
          x: xAxis.scale(h.rsRatio), y: yAxis.scale(h.rsMomentum), date: h.date,
        }));

        // Faded tails by default; hovered item pops to full brightness
        const trailOpacityBase = hasHover ? (isHovered ? 0.5 : 0.06) : 0.1;
        const trailOpacityEnd = hasHover ? (isHovered ? 0.9 : 0.1) : 0.2;
        const dotOpacityBase = hasHover ? (isHovered ? 0.6 : 0.08) : 0.1;
        const dotOpacityEnd = hasHover ? (isHovered ? 1.0 : 0.12) : 0.25;

        return (
          <g key={`trail-${item.ticker}`}>
            {pts.slice(0, -1).map((p, i) => {
              const frac = i / (pts.length - 1);
              const opacity = trailOpacityBase + frac * (trailOpacityEnd - trailOpacityBase);
              return (
                <line key={i} x1={p.x} y1={p.y} x2={pts[i+1].x} y2={pts[i+1].y}
                  stroke={color} strokeWidth={isHovered ? 3 : (item.isBasket ? 2.5 : 2)}
                  opacity={opacity} />
              );
            })}
            {pts.slice(0, -1).map((p, i) => {
              const frac = i / (pts.length - 1);
              const opacity = dotOpacityBase + frac * (dotOpacityEnd - dotOpacityBase);
              return (
                <g key={`d${i}`}>
                  <circle cx={p.x} cy={p.y}
                    r={isHovered ? 4 : Math.max(2, 3.5 - (pts.length - 1 - i) * 0.4)}
                    fill={color} fillOpacity={opacity}
                    stroke={isHovered ? '#fff' : 'none'} strokeWidth={isHovered ? 0.5 : 0}
                  />
                  {isHovered && p.date && (
                    <text x={p.x} y={p.y - 8} textAnchor="middle"
                      fill="#ccc" fontSize={9} fontWeight="bold"
                      style={{ pointerEvents: 'none' }}
                    >
                      {p.date.slice(5)}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        );
      })}
    </g>
  );
};

const ExpandButton = ({ isExpanded, onToggleExpand }) => (
  <button
    onClick={onToggleExpand}
    title={isExpanded ? 'Exit full window' : 'Full window'}
    style={{
      background: 'none', border: '1px solid #3a3a3a', color: '#888',
      cursor: 'pointer', padding: '4px 8px', borderRadius: '4px', fontSize: '14px',
      lineHeight: 1, display: 'flex', alignItems: 'center',
    }}
  >
    {isExpanded ? '\u2715' : '\u26F6'}
  </button>
);

const RRGChart = ({ selectedTheme, isExpanded, onToggleExpand }) => {
  const [viewMode, setViewMode] = useState('sectors');
  const [themes, setThemes] = useState([]);
  const [selectedThemeId, setSelectedThemeId] = useState('');
  const [chartData, setChartData] = useState([]);
  const [basketData, setBasketData] = useState([]);
  const [showSectors, setShowSectors] = useState(true);
  const [showCountries, setShowCountries] = useState(true);
  const [showBaskets, setShowBaskets] = useState(true);
  const [zoomQuadrant, setZoomQuadrant] = useState(null);
  const [hoveredTicker, setHoveredTicker] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getThemes().then(setThemes).catch(console.error);
    loadSectors();
    const interval = setInterval(() => {
      if (viewMode === 'sectors') loadSectors();
      else if (viewMode === 'countries') loadCountries();
      else if (selectedThemeId) loadTheme(selectedThemeId);
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // When a theme is clicked in ThemeManager, switch RRG to show its stocks
  useEffect(() => {
    if (selectedTheme && selectedTheme.id) {
      setViewMode('theme');
      setSelectedThemeId(String(selectedTheme.id));
    }
  }, [selectedTheme]);

  useEffect(() => {
    setZoomQuadrant(null);
    if (viewMode === 'sectors') loadSectors();
    else if (viewMode === 'countries') loadCountries();
    else if (selectedThemeId) loadTheme(selectedThemeId);
  }, [viewMode, selectedThemeId]);

  const loadSectors = async () => {
    try {
      setLoading(true); setError(null);
      const [sectors, baskets] = await Promise.all([
        getSectorsRRG(),
        getThemeRRGBaskets().catch(() => []),
      ]);
      setChartData(sectors);
      setBasketData(baskets);
    } catch (e) { setError('Failed to load sectors'); }
    finally { setLoading(false); }
  };

  const loadCountries = async () => {
    try {
      setLoading(true); setError(null);
      const [countries, baskets] = await Promise.all([
        getCountriesRRG(),
        getThemeRRGBaskets().catch(() => []),
      ]);
      setChartData(countries);
      setBasketData(baskets);
    } catch (e) { setError('Failed to load countries'); }
    finally { setLoading(false); }
  };

  const loadTheme = async (id) => {
    try {
      setLoading(true); setError(null);
      const data = await getThemeRRG(id);
      // Fetch company names for theme tickers
      const tickers = data.map(d => d.ticker);
      const names = await getTickerNames(tickers).catch(() => ({}));
      setChartData(data.map(d => ({ ...d, companyName: names[d.ticker] })));
      setBasketData([]);
    } catch (e) { setError('Failed to load theme'); }
    finally { setLoading(false); }
  };

  const handleDotHover = useCallback((ticker) => setHoveredTicker(ticker), []);
  const handleDotLeave = useCallback(() => setHoveredTicker(null), []);

  // Combine visible data based on toggles
  const visiblePrimary = (viewMode === 'sectors' && !showSectors) ? [] :
                          (viewMode === 'countries' && !showCountries) ? [] :
                          chartData;
  const visibleBaskets = (showBaskets && (viewMode === 'sectors' || viewMode === 'countries')) ? basketData : [];
  const allData = [...visiblePrimary, ...visibleBaskets];

  // For axis range: symmetric around CENTER so crosshairs are always visually centered
  const axisData = [...chartData, ...basketData];
  const allR = axisData.flatMap(d => [d.rsRatio, ...(d.history||[]).map(h=>h.rsRatio)]).filter(v => v != null && isFinite(v));
  const allM = axisData.flatMap(d => [d.rsMomentum, ...(d.history||[]).map(h=>h.rsMomentum)]).filter(v => v != null && isFinite(v));
  const pad = 2;
  const xSpread = allR.length ? Math.max(CENTER - Math.floor(Math.min(...allR) - pad), Math.ceil(Math.max(...allR) + pad) - CENTER, 10) : 15;
  const ySpread = allM.length ? Math.max(CENTER - Math.floor(Math.min(...allM) - pad), Math.ceil(Math.max(...allM) + pad) - CENTER, 10) : 15;
  const fullXMin = CENTER - xSpread, fullXMax = CENTER + xSpread;
  const fullYMin = CENTER - ySpread, fullYMax = CENTER + ySpread;

  // Apply quadrant zoom if active
  let xMin = fullXMin, xMax = fullXMax, yMin = fullYMin, yMax = fullYMax;
  if (zoomQuadrant === 'leading')    { xMin = CENTER - 1; yMin = CENTER - 1; }
  if (zoomQuadrant === 'weakening')  { xMin = CENTER - 1; yMax = CENTER + 1; }
  if (zoomQuadrant === 'lagging')    { xMax = CENTER + 1; yMax = CENTER + 1; }
  if (zoomQuadrant === 'improving')  { xMax = CENTER + 1; yMin = CENTER - 1; }

  // Add color to each item
  const sectorCount = visiblePrimary.length;
  const scatterData = allData.map((d, i) => ({
    ...d,
    color: d.isBasket
      ? BASKET_COLORS[(i - sectorCount) % BASKET_COLORS.length]
      : TICKER_COLORS[i % TICKER_COLORS.length],
  }));

  const manyDots = allData.length > 15;

  const renderDot = (props) => {
    const { cx, cy, payload } = props;
    if (!cx || !cy) return null;
    const isHovered = payload.ticker === hoveredTicker;
    const hasHover = hoveredTicker != null;
    const dimmed = hasHover && !isHovered;

    if (payload.isBasket) {
      const s = isHovered ? 10 : 8;
      return (
        <g
          onMouseEnter={() => handleDotHover(payload.ticker)}
          onMouseLeave={handleDotLeave}
          style={{ cursor: 'pointer' }}
        >
          <polygon
            points={`${cx},${cy-s} ${cx+s},${cy} ${cx},${cy+s} ${cx-s},${cy}`}
            fill={payload.color} fillOpacity={dimmed ? 0.25 : 0.85}
            stroke={isHovered ? '#fff' : '#fff'} strokeWidth={isHovered ? 2 : 1.5}
          />
          <text x={cx} y={cy - s - 6} textAnchor="middle" fill="#ffaa00"
            fontSize={isHovered ? 11 : 10} fontWeight="bold"
            opacity={dimmed ? 0.3 : 1}
          >
            {payload.ticker}
          </text>
        </g>
      );
    }

    const dotR = isHovered ? 9 : (manyDots ? 5 : 7);
    const friendlyName = SECTOR_NAMES[payload.ticker] || COUNTRY_NAMES[payload.ticker] || payload.companyName;

    return (
      <g
        onMouseEnter={() => handleDotHover(payload.ticker)}
        onMouseLeave={handleDotLeave}
        style={{ cursor: 'pointer' }}
      >
        <circle cx={cx} cy={cy} r={dotR}
          fill={payload.color} fillOpacity={dimmed ? 0.2 : 0.85}
          stroke={isHovered ? '#fff' : '#fff'} strokeWidth={isHovered ? 2 : 1.5} />
        <text x={cx} y={cy - (manyDots ? 10 : 13)} textAnchor="middle" fill="#fff"
          fontSize={10} fontWeight="bold" opacity={dimmed ? 0.15 : (manyDots && !isHovered ? 0.7 : 1)}
        >
          {payload.ticker}
        </text>
        {isHovered && friendlyName && (
          <text x={cx} y={cy + 20} textAnchor="middle" fill="#aaa"
            fontSize={9} fontWeight="normal"
          >
            {friendlyName}
          </text>
        )}
      </g>
    );
  };

  const TrailRenderer = TrailLayer({ chartData: allData, hoveredTicker });

  return (
    <div style={{
      backgroundColor: '#1a1a1a', padding: '20px', borderRadius: '8px',
      border: '1px solid #2a2a2a',
      ...(isExpanded ? { flex: 1, display: 'flex', flexDirection: 'column' } : {}),
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h2 style={{ color: '#fff', margin: 0, fontSize: '18px' }}>Relative Rotation Graph</h2>
          <InfoTooltip text={METHODOLOGY_TEXT.rrg} />
          {onToggleExpand && <ExpandButton isExpanded={isExpanded} onToggleExpand={onToggleExpand} />}
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {(viewMode === 'sectors' || viewMode === 'countries') && (
            <>
              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#888', fontSize: '11px', cursor: 'pointer' }}>
                <input
                  type="checkbox" checked={showBaskets}
                  onChange={(e) => setShowBaskets(e.target.checked)}
                  style={{ accentColor: '#ffaa00' }}
                />
                Theme baskets
                <InfoTooltip text={METHODOLOGY_TEXT.baskets} />
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#888', fontSize: '11px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={viewMode === 'sectors' ? showSectors : showCountries}
                  onChange={(e) => viewMode === 'sectors' ? setShowSectors(e.target.checked) : setShowCountries(e.target.checked)}
                  style={{ accentColor: '#00ff88' }}
                />
                {viewMode === 'sectors' ? 'Sectors' : 'Countries'}
                <InfoTooltip text={viewMode === 'sectors' ? METHODOLOGY_TEXT.sectors : METHODOLOGY_TEXT.countries} />
              </label>
            </>
          )}
          <button onClick={() => setViewMode('sectors')}
            style={{
              padding: '6px 14px', borderRadius: '4px', border: 'none', cursor: 'pointer', fontSize: '13px',
              fontWeight: viewMode === 'sectors' ? 'bold' : 'normal',
              backgroundColor: viewMode === 'sectors' ? '#00ff88' : '#2a2a2a',
              color: viewMode === 'sectors' ? '#000' : '#aaa',
            }}>
            Sectors
          </button>
          <button onClick={() => setViewMode('countries')}
            style={{
              padding: '6px 14px', borderRadius: '4px', border: 'none', cursor: 'pointer', fontSize: '13px',
              fontWeight: viewMode === 'countries' ? 'bold' : 'normal',
              backgroundColor: viewMode === 'countries' ? '#00ff88' : '#2a2a2a',
              color: viewMode === 'countries' ? '#000' : '#aaa',
            }}>
            Countries
          </button>
          <select
            value={viewMode === 'theme' ? selectedThemeId : ''}
            onChange={(e) => { if (e.target.value) { setViewMode('theme'); setSelectedThemeId(e.target.value); } }}
            style={{
              padding: '6px 12px', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px',
              backgroundColor: viewMode === 'theme' ? '#00ff88' : '#2a2a2a',
              color: viewMode === 'theme' ? '#000' : '#aaa',
            }}>
            <option value="">Theme View...</option>
            {themes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
      </div>

      {/* Chart */}
      {loading ? (
        <div style={{ color: '#888', textAlign: 'center', padding: '80px 0' }}>Loading RRG data...</div>
      ) : error ? (
        <div style={{ color: '#ff4444', textAlign: 'center', padding: '80px 0' }}>{error}</div>
      ) : (
        <ResponsiveContainer width="100%" height={isExpanded ? window.innerHeight - 180 : 480}>
          <ScatterChart margin={{ top: 20, right: 30, bottom: 30, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222" />
            <XAxis type="number" dataKey="rsRatio" name="RS-Ratio" domain={[xMin, xMax]}
              allowDataOverflow={true}
              stroke="#555" tick={{ fill: '#888', fontSize: 11 }}
              label={{ value: 'RS-Ratio \u2192', position: 'insideBottomRight', offset: -5, fill: '#666', fontSize: 12 }} />
            <YAxis type="number" dataKey="rsMomentum" name="RS-Momentum" domain={[yMin, yMax]}
              allowDataOverflow={true}
              stroke="#555" tick={{ fill: '#888', fontSize: 11 }}
              label={{ value: 'RS-Momentum \u2192', angle: -90, position: 'insideLeft', offset: 10, fill: '#666', fontSize: 12 }} />
            <ZAxis range={[100, 100]} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine x={CENTER} stroke="#444" strokeWidth={2} />
            <ReferenceLine y={CENTER} stroke="#444" strokeWidth={2} />
            <Customized component={QuadrantLayer} />
            <Customized component={TrailRenderer} />
            <Scatter data={scatterData} shape={renderDot} />
          </ScatterChart>
        </ResponsiveContainer>
      )}

      {/* Quadrant zoom */}
      <div style={{ display: 'flex', gap: '6px', marginTop: '10px', alignItems: 'center' }}>
        <span style={{ color: '#555', fontSize: '11px', marginRight: '4px' }}>Zoom:</span>
        {[
          { key: null, label: 'All' },
          { key: 'leading', label: 'Leading', color: '#00aa66' },
          { key: 'weakening', label: 'Weakening', color: '#bbaa00' },
          { key: 'lagging', label: 'Lagging', color: '#aa4444' },
          { key: 'improving', label: 'Improving', color: '#4488aa' },
        ].map(q => (
          <button key={q.label}
            onClick={() => setZoomQuadrant(zoomQuadrant === q.key ? null : q.key)}
            style={{
              padding: '3px 10px', borderRadius: '3px', border: 'none', cursor: 'pointer',
              fontSize: '11px', fontWeight: zoomQuadrant === q.key ? 'bold' : 'normal',
              backgroundColor: zoomQuadrant === q.key ? (q.color || '#00ff88') : '#1a1a1a',
              color: zoomQuadrant === q.key ? '#000' : (q.color || '#888'),
              border: `1px solid ${zoomQuadrant === q.key ? (q.color || '#00ff88') : '#333'}`,
            }}>
            {q.label}
          </button>
        ))}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '24px', marginTop: '8px', fontSize: '12px', color: '#888', flexWrap: 'wrap' }}>
        {[
          { label: 'Leading', color: 'rgba(0,180,80,0.3)' },
          { label: 'Weakening', color: 'rgba(200,180,0,0.3)' },
          { label: 'Lagging', color: 'rgba(200,50,50,0.3)' },
          { label: 'Improving', color: 'rgba(50,100,200,0.3)' },
        ].map(q => (
          <div key={q.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '14px', height: '14px', backgroundColor: q.color, borderRadius: '2px' }} />
            <span>{q.label}</span>
          </div>
        ))}
        {showBaskets && (viewMode === 'sectors' || viewMode === 'countries') && basketData.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '14px', height: '14px', backgroundColor: '#ffaa00', transform: 'rotate(45deg)', borderRadius: '1px' }} />
            <span>Theme basket</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default RRGChart;
