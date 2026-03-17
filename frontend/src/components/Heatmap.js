import React, { useState, useEffect, useCallback } from 'react';
import { getHeatmap } from '../api/client';

const PERIODS = [
  { key: '1d', label: '1D' },
  { key: '1w', label: '1W' },
  { key: '1mo', label: '1M' },
  { key: '3mo', label: '3M' },
  { key: '1y', label: '1Y' },
];

// Color scale: deep red → red → neutral → green → deep green
function getColor(pct) {
  if (pct === null || pct === undefined) return '#333';
  const clamped = Math.max(-10, Math.min(10, pct));
  if (clamped > 0) {
    const intensity = Math.min(clamped / 5, 1);
    const r = Math.round(20 - 20 * intensity);
    const g = Math.round(60 + 140 * intensity);
    const b = Math.round(30 - 10 * intensity);
    return `rgb(${r}, ${g}, ${b})`;
  } else if (clamped < 0) {
    const intensity = Math.min(Math.abs(clamped) / 5, 1);
    const r = Math.round(60 + 140 * intensity);
    const g = Math.round(30 - 20 * intensity);
    const b = Math.round(30 - 10 * intensity);
    return `rgb(${r}, ${g}, ${b})`;
  }
  return '#2a2a2a';
}

function getTextColor(pct) {
  const abs = Math.abs(pct || 0);
  return abs > 3 ? '#fff' : '#ccc';
}

// Custom treemap layout using squarify-like algorithm
function squarify(items, x, y, w, h) {
  if (!items.length || w <= 0 || h <= 0) return [];

  const total = items.reduce((s, it) => s + it.weight, 0);
  if (total <= 0) return [];

  const rects = [];

  function layoutRow(row, rowTotal, x, y, w, h, isHorizontal) {
    let offset = 0;
    const span = isHorizontal ? w : h;
    const thickness = rowTotal / total * (isHorizontal ? h : w);

    row.forEach(item => {
      const frac = item.weight / rowTotal;
      const len = frac * span;
      if (isHorizontal) {
        rects.push({ ...item, x: x + offset, y: y, w: len, h: thickness });
      } else {
        rects.push({ ...item, x: x, y: y + offset, w: thickness, h: len });
      }
      offset += len;
    });

    return isHorizontal
      ? { x, y: y + thickness, w, h: h - thickness }
      : { x: x + thickness, y, w: w - thickness, h };
  }

  // Simple strip layout: split items into rows greedily
  let remaining = { x, y, w, h };
  let i = 0;
  const sorted = [...items].sort((a, b) => b.weight - a.weight);

  while (i < sorted.length && remaining.w > 0 && remaining.h > 0) {
    const isHorizontal = remaining.w >= remaining.h;
    const row = [];
    let rowTotal = 0;
    const targetRowArea = total * 0.3; // fill roughly 30% per row

    while (i < sorted.length) {
      row.push(sorted[i]);
      rowTotal += sorted[i].weight;
      i++;
      if (rowTotal >= targetRowArea && i < sorted.length) break;
    }

    remaining = layoutRow(row, rowTotal, remaining.x, remaining.y, remaining.w, remaining.h, isHorizontal);
  }

  return rects;
}

const Heatmap = ({ isExpanded, onToggleExpand, onTickerClick }) => {
  const [data, setData] = useState(null);
  const [period, setPeriod] = useState('1d');
  const [viewThemeId, setViewThemeId] = useState(null); // null = all themes
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoveredTicker, setHoveredTicker] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await getHeatmap(period, viewThemeId);
      setData(result);
    } catch (e) {
      setError('Failed to load heatmap data');
    } finally {
      setLoading(false);
    }
  }, [period, viewThemeId]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleMouseMove = useCallback((e, ticker) => {
    setHoveredTicker(ticker);
    setTooltipPos({ x: e.clientX, y: e.clientY });
  }, []);

  const handleMouseLeave = useCallback(() => {
    setHoveredTicker(null);
  }, []);

  const themes = data?.data || [];
  const containerHeight = isExpanded ? window.innerHeight - 120 : 480;

  // Build treemap data
  const renderAllThemes = () => {
    if (!themes.length) return <div style={{ color: '#888', textAlign: 'center', padding: '80px 0' }}>No theme data available</div>;

    const totalWidth = 100; // percentage
    const totalHeight = containerHeight;

    // Each theme gets area proportional to ticker count
    const themeItems = themes.map(t => ({
      ...t,
      weight: t.tickers.length,
    }));

    const themeRects = squarify(themeItems, 0, 0, totalWidth, totalHeight);

    return (
      <div style={{ position: 'relative', width: '100%', height: totalHeight, overflow: 'hidden' }}>
        {themeRects.map((theme, ti) => {
          // Layout tickers within this theme's rect
          const tickerItems = theme.tickers.map(t => ({
            ...t,
            weight: 1, // equal weight within theme
          }));

          const tickerRects = squarify(tickerItems, 0, 0, theme.w, theme.h);

          return (
            <div key={theme.id} style={{
              position: 'absolute',
              left: `${theme.x}%`,
              top: theme.y,
              width: `${theme.w}%`,
              height: theme.h,
              border: '1px solid #000',
            }}>
              {/* Theme label */}
              {theme.h > 30 && theme.w > 8 && (
                <div
                  onClick={() => setViewThemeId(theme.id)}
                  style={{
                    position: 'absolute',
                    top: 0, left: 0, right: 0,
                    zIndex: 10,
                    padding: '2px 4px',
                    fontSize: '10px',
                    fontWeight: 'bold',
                    color: '#fff',
                    textShadow: '0 0 4px #000, 0 0 8px #000',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    pointerEvents: 'auto',
                  }}
                >
                  {theme.name} ({theme.avg_change_pct > 0 ? '+' : ''}{theme.avg_change_pct}%)
                </div>
              )}
              {/* Ticker cells */}
              {tickerRects.map((t, i) => (
                <div
                  key={t.ticker}
                  onClick={() => onTickerClick?.(t.ticker)}
                  onMouseMove={(e) => handleMouseMove(e, t)}
                  onMouseLeave={handleMouseLeave}
                  style={{
                    position: 'absolute',
                    left: `${(t.x / theme.w) * 100}%`,
                    top: t.y,
                    width: `${(t.w / theme.w) * 100}%`,
                    height: t.h,
                    backgroundColor: getColor(t.change_pct),
                    border: '1px solid rgba(0,0,0,0.3)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    overflow: 'hidden',
                    transition: 'filter 0.15s',
                    filter: hoveredTicker?.ticker === t.ticker ? 'brightness(1.3)' : 'none',
                  }}
                >
                  {t.h > 25 && (t.w / theme.w) * 100 > 12 && (
                    <>
                      <div style={{
                        fontSize: t.h > 50 ? '12px' : '9px',
                        fontWeight: 'bold',
                        color: getTextColor(t.change_pct),
                        lineHeight: 1.2,
                      }}>
                        {t.ticker}
                      </div>
                      {t.h > 40 && (
                        <div style={{
                          fontSize: t.h > 50 ? '11px' : '8px',
                          color: getTextColor(t.change_pct),
                          opacity: 0.9,
                        }}>
                          {t.change_pct > 0 ? '+' : ''}{t.change_pct}%
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    );
  };

  // Single theme view — bigger cells, more detail
  const renderSingleTheme = () => {
    const theme = themes[0];
    if (!theme) return <div style={{ color: '#888', textAlign: 'center', padding: '80px 0' }}>No data for this theme</div>;

    const totalHeight = containerHeight;
    const tickerItems = theme.tickers.map(t => ({
      ...t,
      weight: 1,
    }));

    const tickerRects = squarify(tickerItems, 0, 0, 100, totalHeight);

    return (
      <div style={{ position: 'relative', width: '100%', height: totalHeight, overflow: 'hidden' }}>
        {tickerRects.map((t) => (
          <div
            key={t.ticker}
            onClick={() => onTickerClick?.(t.ticker)}
            onMouseMove={(e) => handleMouseMove(e, t)}
            onMouseLeave={handleMouseLeave}
            style={{
              position: 'absolute',
              left: `${t.x}%`,
              top: t.y,
              width: `${t.w}%`,
              height: t.h,
              backgroundColor: getColor(t.change_pct),
              border: '1px solid rgba(0,0,0,0.4)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              overflow: 'hidden',
              transition: 'filter 0.15s',
              filter: hoveredTicker?.ticker === t.ticker ? 'brightness(1.3)' : 'none',
            }}
          >
            <div style={{ fontSize: '14px', fontWeight: 'bold', color: getTextColor(t.change_pct) }}>
              {t.ticker}
            </div>
            <div style={{ fontSize: '11px', color: getTextColor(t.change_pct), opacity: 0.8, marginTop: '2px' }}>
              {t.name !== t.ticker ? t.name : ''}
            </div>
            <div style={{ fontSize: '16px', fontWeight: 'bold', color: getTextColor(t.change_pct), marginTop: '4px' }}>
              {t.change_pct > 0 ? '+' : ''}{t.change_pct}%
            </div>
            <div style={{ fontSize: '10px', color: '#aaa', marginTop: '2px' }}>
              ${t.price}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{
      backgroundColor: '#111',
      borderRadius: '8px',
      padding: '16px',
      border: '1px solid #222',
      flex: isExpanded ? 1 : undefined,
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: 0 }}>Heatmap</h2>

        <button
          onClick={onToggleExpand}
          style={{
            background: 'none', border: 'none', color: '#888', cursor: 'pointer',
            fontSize: '16px', padding: '2px 6px',
          }}
          title={isExpanded ? 'Exit fullscreen' : 'Fullscreen'}
        >&#x26F6;</button>

        {/* Period selector */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {PERIODS.map(p => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              style={{
                padding: '4px 10px', borderRadius: '4px', cursor: 'pointer',
                fontSize: '11px', fontWeight: period === p.key ? 'bold' : 'normal',
                backgroundColor: period === p.key ? '#00ff88' : '#1a1a1a',
                color: period === p.key ? '#000' : '#888',
                border: `1px solid ${period === p.key ? '#00ff88' : '#333'}`,
              }}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* View selector */}
        <div style={{ display: 'flex', gap: '4px', marginLeft: 'auto' }}>
          <button
            onClick={() => setViewThemeId(null)}
            style={{
              padding: '4px 10px', borderRadius: '4px', cursor: 'pointer',
              fontSize: '11px', fontWeight: !viewThemeId ? 'bold' : 'normal',
              backgroundColor: !viewThemeId ? '#4488ff' : '#1a1a1a',
              color: !viewThemeId ? '#fff' : '#888',
              border: `1px solid ${!viewThemeId ? '#4488ff' : '#333'}`,
            }}
          >
            All Themes
          </button>
          {data?.data?.length > 0 && viewThemeId && (
            <span style={{ color: '#aaa', fontSize: '12px', alignSelf: 'center' }}>
              {themes[0]?.name}
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ color: '#888', textAlign: 'center', padding: '80px 0' }}>Loading heatmap...</div>
      ) : error ? (
        <div style={{ color: '#ff4444', textAlign: 'center', padding: '80px 0' }}>{error}</div>
      ) : viewThemeId ? (
        renderSingleTheme()
      ) : (
        renderAllThemes()
      )}

      {/* Tooltip */}
      {hoveredTicker && (
        <div style={{
          position: 'fixed',
          left: tooltipPos.x + 12,
          top: tooltipPos.y - 40,
          backgroundColor: '#1a1a1a',
          border: '1px solid #444',
          borderRadius: '6px',
          padding: '8px 12px',
          fontSize: '12px',
          zIndex: 9999,
          pointerEvents: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          whiteSpace: 'nowrap',
        }}>
          <div style={{ fontWeight: 'bold', color: '#fff' }}>
            {hoveredTicker.ticker}
            {hoveredTicker.name && hoveredTicker.name !== hoveredTicker.ticker && (
              <span style={{ fontWeight: 'normal', color: '#aaa', marginLeft: '6px' }}>{hoveredTicker.name}</span>
            )}
          </div>
          <div style={{ color: hoveredTicker.change_pct >= 0 ? '#00ff88' : '#ff4444', marginTop: '2px' }}>
            {hoveredTicker.change_pct > 0 ? '+' : ''}{hoveredTicker.change_pct}%
            <span style={{ color: '#888', marginLeft: '8px' }}>${hoveredTicker.price}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default Heatmap;
