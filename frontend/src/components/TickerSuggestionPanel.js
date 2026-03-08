import React, { useState, useEffect } from 'react';
import { suggestTickers, updateTheme } from '../api/client';

const TickerSuggestionPanel = ({ theme, onClose, onTickersAdded }) => {
  const [suggestions, setSuggestions] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSuggestions();
  }, [theme.id]);

  const loadSuggestions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await suggestTickers(theme.id, 10);
      setSuggestions(data);
    } catch (err) {
      console.error('Failed to load suggestions', err);
      setError('Failed to find suggestions. The stock universe may still be loading.');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (ticker) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(ticker)) next.delete(ticker);
      else next.add(ticker);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === suggestions.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(suggestions.map(s => s.ticker)));
    }
  };

  const handleDismiss = (ticker) => {
    setSuggestions(prev => prev.filter(s => s.ticker !== ticker));
    setSelected(prev => {
      const next = new Set(prev);
      next.delete(ticker);
      return next;
    });
  };

  const handleAddSelected = async () => {
    if (selected.size === 0) return;
    setAdding(true);
    try {
      const newTickers = [...theme.tickers, ...Array.from(selected)];
      await updateTheme(theme.id, { tickers: newTickers });
      onTickersAdded();
      onClose();
    } catch (err) {
      setError('Failed to add tickers');
      setAdding(false);
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.7)', zIndex: 1000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: '#0a0a0a', border: '1px solid #2a2a2a',
          borderRadius: '8px', width: '640px', maxHeight: '80vh',
          display: 'flex', flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #2a2a2a',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <h3 style={{ color: '#fff', margin: 0, fontSize: '16px' }}>
              Suggest Tickers for{' '}
              <span style={{ color: '#00ff88' }}>{theme.name}</span>
            </h3>
            <div style={{ color: '#666', fontSize: '12px', marginTop: '4px' }}>
              Based on industry & sector matching across {'>'}8,000 stocks
            </div>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: '#888', fontSize: '20px',
            cursor: 'pointer', padding: '4px',
          }}>×</button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '12px 20px' }}>
          {loading ? (
            <div style={{ color: '#888', textAlign: 'center', padding: '40px 0' }}>
              <div style={{ fontSize: '14px', marginBottom: '8px' }}>Finding related stocks...</div>
              <div style={{ fontSize: '11px', color: '#555' }}>
                This may take a moment on first run while data is cached
              </div>
            </div>
          ) : error ? (
            <div style={{ color: '#ff4444', textAlign: 'center', padding: '40px 0' }}>
              {error}
            </div>
          ) : suggestions.length === 0 ? (
            <div style={{ color: '#888', textAlign: 'center', padding: '40px 0' }}>
              No suggestions found. Try adding more tickers to the theme first.
            </div>
          ) : (
            <>
              {/* Select all toggle */}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                marginBottom: '8px', padding: '4px 0',
              }}>
                <button onClick={selectAll} style={{
                  background: 'none', border: 'none', color: '#5f27cd',
                  fontSize: '12px', cursor: 'pointer', padding: 0,
                }}>
                  {selected.size === suggestions.length ? 'Deselect All' : 'Select All'}
                </button>
                <span style={{ color: '#555', fontSize: '11px' }}>
                  {suggestions.length} suggestions
                </span>
              </div>

              {/* Suggestion rows */}
              {suggestions.map((s) => {
                const isSelected = selected.has(s.ticker);
                return (
                  <div key={s.ticker} style={{
                    display: 'flex', alignItems: 'center', gap: '12px',
                    padding: '10px 12px', marginBottom: '4px',
                    backgroundColor: isSelected ? '#1a2a1a' : '#111',
                    border: `1px solid ${isSelected ? '#00ff8844' : '#1a1a1a'}`,
                    borderRadius: '6px', cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                    onClick={() => toggleSelect(s.ticker)}
                  >
                    {/* Checkbox */}
                    <div style={{
                      width: '18px', height: '18px', borderRadius: '3px',
                      border: `2px solid ${isSelected ? '#00ff88' : '#444'}`,
                      backgroundColor: isSelected ? '#00ff88' : 'transparent',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0, transition: 'all 0.15s',
                    }}>
                      {isSelected && <span style={{ color: '#000', fontSize: '12px', fontWeight: 'bold' }}>✓</span>}
                    </div>

                    {/* Info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '2px' }}>
                        <span style={{ color: '#00ff88', fontWeight: 'bold', fontSize: '14px' }}>
                          {s.ticker}
                        </span>
                        <span style={{ color: '#aaa', fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {s.company_name}
                        </span>
                        {s.country && s.country !== 'US' && (
                          <span style={{
                            color: '#888', fontSize: '10px', padding: '1px 5px',
                            backgroundColor: '#2a2a2a', borderRadius: '3px',
                          }}>
                            {s.country}
                          </span>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: '#666' }}>
                        <span>{s.industry || s.sector}</span>
                        <span>{s.market_cap}</span>
                      </div>
                      <div style={{ fontSize: '10px', color: '#555', marginTop: '2px', fontStyle: 'italic' }}>
                        {s.rationale}
                      </div>
                    </div>

                    {/* Confidence */}
                    <div style={{ flexShrink: 0, textAlign: 'right' }}>
                      <div style={{
                        width: '40px', height: '4px', backgroundColor: '#2a2a2a',
                        borderRadius: '2px', overflow: 'hidden',
                      }}>
                        <div style={{
                          width: `${(s.confidence || 0) * 100}%`, height: '100%',
                          backgroundColor: s.confidence > 0.6 ? '#00ff88' : s.confidence > 0.3 ? '#f7b731' : '#888',
                        }} />
                      </div>
                    </div>

                    {/* Dismiss */}
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDismiss(s.ticker); }}
                      style={{
                        background: 'none', border: 'none', color: '#444',
                        fontSize: '14px', cursor: 'pointer', padding: '2px 4px',
                        flexShrink: 0,
                      }}
                      title="Dismiss"
                    >×</button>
                  </div>
                );
              })}
            </>
          )}
        </div>

        {/* Footer */}
        {suggestions.length > 0 && !loading && (
          <div style={{
            padding: '12px 20px', borderTop: '1px solid #2a2a2a',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ color: '#666', fontSize: '12px' }}>
              {selected.size} selected
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={onClose} style={{
                padding: '8px 16px', backgroundColor: '#2a2a2a', color: '#aaa',
                border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px',
              }}>
                Cancel
              </button>
              <button
                onClick={handleAddSelected}
                disabled={selected.size === 0 || adding}
                style={{
                  padding: '8px 20px', borderRadius: '4px', border: 'none',
                  cursor: selected.size === 0 || adding ? 'not-allowed' : 'pointer',
                  fontSize: '13px', fontWeight: 'bold',
                  backgroundColor: selected.size > 0 ? '#00ff88' : '#2a2a2a',
                  color: selected.size > 0 ? '#000' : '#555',
                  opacity: adding ? 0.6 : 1,
                }}
              >
                {adding ? 'Adding...' : `Add ${selected.size} Ticker${selected.size !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TickerSuggestionPanel;
