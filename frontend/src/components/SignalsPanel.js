import React, { useState, useEffect } from 'react';
import { getSignals } from '../api/client';

const SIGNAL_STYLES = {
  large_move_up:    { label: 'Big Move Up',      color: '#00ff88', bg: '#1a3a1a' },
  large_move_down:  { label: 'Big Move Down',    color: '#ff4444', bg: '#3a1a1a' },
  near_52w_high:    { label: 'Near 52W High',    color: '#4488ff', bg: '#1a2a3a' },
  near_52w_low:     { label: 'Near 52W Low',     color: '#ffaa44', bg: '#3a2a1a' },
  rsi_overbought:   { label: 'RSI Overbought',   color: '#ffff44', bg: '#3a3a1a' },
  rsi_oversold:     { label: 'RSI Oversold',     color: '#aa44ff', bg: '#2a1a3a' },
  golden_cross:     { label: 'Golden Cross',     color: '#00ff88', bg: '#1a3a1a' },
  death_cross:      { label: 'Death Cross',      color: '#ff4444', bg: '#3a1a1a' },
  price_above_50sma:{ label: 'Above 50 SMA',     color: '#4ecdc4', bg: '#1a2a2a' },
  price_below_50sma:{ label: 'Below 50 SMA',     color: '#ff6b6b', bg: '#3a1a2a' },
  rrg_transition:   { label: 'RRG Transition',   color: '#ff9ff3', bg: '#3a1a3a' },
};

const SignalsPanel = ({ onTickerClick, isExpanded, onToggleExpand }) => {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState('significance');
  const [sortDir, setSortDir] = useState('desc');

  useEffect(() => {
    loadSignals();
    const interval = setInterval(loadSignals, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const loadSignals = async () => {
    try {
      const data = await getSignals();
      setSignals(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load signals', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = [...signals].sort((a, b) => {
    const av = a[sortKey] || '';
    const bv = b[sortKey] || '';
    const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const SortHeader = ({ label, field, width }) => (
    <th
      onClick={() => handleSort(field)}
      style={{
        padding: '10px 12px', backgroundColor: '#0a0a0a', color: '#888',
        fontSize: '11px', fontWeight: 'bold', textAlign: 'left',
        cursor: 'pointer', userSelect: 'none', borderBottom: '1px solid #2a2a2a',
        width,
      }}
    >
      {label} {sortKey === field && (sortDir === 'asc' ? '↑' : '↓')}
    </th>
  );

  return (
    <div style={{
      backgroundColor: '#1a1a1a', padding: '16px', borderRadius: '8px',
      border: '1px solid #2a2a2a',
      ...(isExpanded ? { flex: 1, display: 'flex', flexDirection: 'column' } : {}),
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{ color: '#fff', margin: 0, fontSize: '16px' }}>
          Signals
        </h3>
        {onToggleExpand && (
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
        )}
      </div>

      {loading ? (
        <div style={{ color: '#888', padding: '20px', textAlign: 'center' }}>Loading...</div>
      ) : sorted.length === 0 ? (
        <div style={{ color: '#888', padding: '20px', textAlign: 'center' }}>No signals</div>
      ) : (
        <div style={{ overflowX: 'auto', overflowY: 'auto', ...(isExpanded ? { flex: 1 } : { maxHeight: '280px' }) }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr>
                <SortHeader label="Ticker" field="ticker" width="80px" />
                <SortHeader label="Theme" field="theme" width="140px" />
                <SortHeader label="Signal" field="type" width="140px" />
                <SortHeader label="Details" field="details" />
                <SortHeader label="Score" field="significance" width="60px" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((sig, i) => {
                const style = SIGNAL_STYLES[sig.type] || { label: sig.type, color: '#888', bg: '#1a1a1a' };
                return (
                  <tr key={i} style={{
                    backgroundColor: i % 2 === 0 ? '#0a0a0a' : '#121212',
                    borderBottom: '1px solid #1a1a1a',
                  }}>
                    <td
                      style={{ padding: '10px 12px', color: '#00ff88', fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => onTickerClick && onTickerClick(sig.ticker)}
                    >
                      {sig.ticker}
                    </td>
                    <td style={{ padding: '10px 12px', color: '#aaa', fontSize: '12px' }}>
                      {sig.theme || '--'}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '3px 10px', backgroundColor: style.bg, color: style.color,
                        borderRadius: '12px', fontSize: '11px', fontWeight: 'bold',
                        border: `1px solid ${style.color}33`,
                      }}>
                        {style.label}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', color: '#888', fontSize: '12px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {sig.details || '--'}
                    </td>
                    <td style={{ padding: '10px 12px', color: '#ffaa44', fontWeight: 'bold', textAlign: 'center' }}>
                      {sig.significance?.toFixed(1)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default SignalsPanel;
