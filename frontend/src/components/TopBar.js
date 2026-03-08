import React, { useState, useEffect } from 'react';
import { getMarketOverview } from '../api/client';

const TopBar = () => {
  const [indices, setIndices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      setError(null);
      const data = await getMarketOverview();
      setIndices(data);
    } catch (err) {
      console.error('Market data fetch failed', err);
      setError('Market data unavailable');
      setIndices([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '12px 20px',
      backgroundColor: '#0a0a0a',
      borderBottom: '1px solid #2a2a2a',
    }}>
      <div style={{
        fontSize: '22px',
        fontWeight: 'bold',
        letterSpacing: '1px',
        color: '#00ff88',
      }}>
        THEME INTELLIGENCE
      </div>

      <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        {loading ? (
          <div style={{ color: '#888', fontSize: '13px' }}>Loading market data...</div>
        ) : error ? (
          <div style={{ color: '#ff4444', fontSize: '13px' }}>{error}</div>
        ) : (
          indices.map((idx) => {
            const pct = idx.change_pct || 0;
            const color = pct > 0 ? '#00ff88' : pct < 0 ? '#ff4444' : '#888';
            return (
              <div key={idx.symbol || idx.name} style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-end',
                padding: '4px 12px',
                backgroundColor: '#1a1a1a',
                border: '1px solid #2a2a2a',
                borderRadius: '4px',
                minWidth: '90px',
              }}>
                <div style={{ fontSize: '11px', color: '#888', fontWeight: 'bold' }}>{idx.symbol}</div>
                <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#fff' }}>
                  {typeof idx.price === 'number' ? `$${idx.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '--'}
                </div>
                <div style={{ fontSize: '11px', color, fontWeight: 'bold' }}>
                  {pct > 0 ? '+' : ''}{pct.toFixed(2)}%
                  {idx.last_update && (
                    <span style={{ color: '#555', fontWeight: 'normal', marginLeft: '4px' }}>
                      {idx.last_update}
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default TopBar;
