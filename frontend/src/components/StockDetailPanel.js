import React, { useState, useEffect } from 'react';
import { getStockResearch, updateStockResearch, addResearchNote, refreshStockAnalysis } from '../api/client';

const STATUS_STYLES = {
  active:    { label: 'Active',    color: '#00ff88', bg: '#1a3a1a' },
  watchlist: { label: 'Watchlist', color: '#4488ff', bg: '#1a2a3a' },
  dormant:   { label: 'Dormant',   color: '#888888', bg: '#2a2a2a' },
};

const StockDetailPanel = ({ ticker, onClose }) => {
  const [research, setResearch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [noteInput, setNoteInput] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});
  const [catalystInput, setCatalystInput] = useState('');
  const [riskInput, setRiskInput] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (ticker) loadResearch();
  }, [ticker]);

  const loadResearch = async () => {
    try {
      setLoading(true);
      const data = await getStockResearch(ticker);
      setResearch(data);
      setEditData({
        status: data.status || 'active',
        buy_target: data.buy_target || '',
        sell_target: data.sell_target || '',
        stop_loss: data.stop_loss || '',
        position_size: data.position_size || '',
        notes: data.notes || '',
        catalysts: data.catalysts || [],
        risks: data.risks || [],
      });
    } catch (err) {
      console.error('Failed to load research', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const payload = {
        ...editData,
        buy_target: editData.buy_target ? parseFloat(editData.buy_target) : null,
        sell_target: editData.sell_target ? parseFloat(editData.sell_target) : null,
        stop_loss: editData.stop_loss ? parseFloat(editData.stop_loss) : null,
      };
      await updateStockResearch(ticker, payload);
      await loadResearch();
      setEditMode(false);
    } catch (err) {
      console.error('Failed to save', err);
    } finally {
      setSaving(false);
    }
  };

  const handleAddNote = async () => {
    if (!noteInput.trim()) return;
    try {
      await addResearchNote(ticker, noteInput.trim());
      setNoteInput('');
      await loadResearch();
    } catch (err) {
      console.error('Failed to add note', err);
    }
  };

  const addCatalyst = () => {
    if (catalystInput.trim() && !editData.catalysts.includes(catalystInput.trim())) {
      setEditData({
        ...editData,
        catalysts: [...editData.catalysts, catalystInput.trim()],
      });
      setCatalystInput('');
    }
  };

  const removeCatalyst = (c) => {
    setEditData({
      ...editData,
      catalysts: editData.catalysts.filter((x) => x !== c),
    });
  };

  const addRisk = () => {
    if (riskInput.trim() && !editData.risks.includes(riskInput.trim())) {
      setEditData({
        ...editData,
        risks: [...editData.risks, riskInput.trim()],
      });
      setRiskInput('');
    }
  };

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      const data = await refreshStockAnalysis(ticker);
      setResearch(data);
      setEditData({
        status: data.status || 'active',
        buy_target: data.buy_target || '',
        sell_target: data.sell_target || '',
        stop_loss: data.stop_loss || '',
        position_size: data.position_size || '',
        notes: data.notes || '',
        catalysts: data.catalysts || [],
        risks: data.risks || [],
      });
    } catch (err) {
      console.error('Failed to refresh analysis', err);
    } finally {
      setRefreshing(false);
    }
  };

  const removeRisk = (r) => {
    setEditData({
      ...editData,
      risks: editData.risks.filter((x) => x !== r),
    });
  };

  if (!ticker) return null;

  const statusStyle = STATUS_STYLES[research?.status] || STATUS_STYLES.active;

  return (
    <div
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex',
        justifyContent: 'flex-end', zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '560px', maxWidth: '90vw', height: '100%',
          backgroundColor: '#0a0a0a', borderLeft: '1px solid #2a2a2a',
          overflowY: 'auto', padding: '24px',
          animation: 'slideIn 0.2s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {loading ? (
          <div style={{ color: '#888', padding: '40px', textAlign: 'center' }}>
            Loading...
          </div>
        ) : (
          <>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <h2 style={{ color: '#00ff88', margin: '0 0 6px 0', fontSize: '24px' }}>
                  {ticker}
                </h2>
                {research?.themes?.length > 0 && (
                  <div style={{ color: '#888', fontSize: '12px' }}>
                    {research.themes.join(' / ')}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  title="Re-analyze with latest market data"
                  style={{
                    padding: '4px 10px', backgroundColor: '#2a2a4a', color: '#ff9ff3',
                    border: '1px solid #4a2a4a', borderRadius: '4px', cursor: 'pointer',
                    fontSize: '11px', fontWeight: 'bold', opacity: refreshing ? 0.5 : 1,
                  }}
                >
                  {refreshing ? 'Analyzing...' : 'Refresh Analysis'}
                </button>
                <span style={{
                  padding: '4px 12px', borderRadius: '12px', fontSize: '11px',
                  fontWeight: 'bold', color: statusStyle.color, backgroundColor: statusStyle.bg,
                  border: `1px solid ${statusStyle.color}33`,
                }}>
                  {statusStyle.label}
                </span>
                <button
                  onClick={onClose}
                  style={{
                    background: 'none', border: 'none', color: '#888',
                    fontSize: '24px', cursor: 'pointer', padding: '0 4px',
                  }}
                >
                  x
                </button>
              </div>
            </div>

            {/* Price Levels */}
            <div style={{
              backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a',
              borderRadius: '6px', padding: '14px', marginBottom: '16px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <h4 style={{ color: '#fff', margin: 0, fontSize: '14px' }}>Price Levels</h4>
                {!editMode && (
                  <button onClick={() => setEditMode(true)} style={{
                    padding: '3px 10px', backgroundColor: '#2a2a4a', color: '#88ff88',
                    border: '1px solid #2a4a2a', borderRadius: '3px', cursor: 'pointer', fontSize: '11px',
                  }}>Edit</button>
                )}
              </div>

              {editMode ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                  {[
                    { key: 'buy_target', label: 'Buy Target', color: '#00ff88' },
                    { key: 'sell_target', label: 'Sell Target', color: '#4488ff' },
                    { key: 'stop_loss', label: 'Stop Loss', color: '#ff4444' },
                  ].map(({ key, label, color }) => (
                    <div key={key}>
                      <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>
                        {label}
                      </label>
                      <input
                        type="number" step="0.01"
                        value={editData[key]}
                        onChange={(e) => setEditData({ ...editData, [key]: e.target.value })}
                        style={{
                          width: '100%', padding: '6px 8px', backgroundColor: '#0a0a0a',
                          border: `1px solid ${color}44`, borderRadius: '4px', color,
                          fontSize: '14px', fontWeight: 'bold', boxSizing: 'border-box',
                        }}
                        placeholder="$0.00"
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                  {[
                    { label: 'Buy Target', val: research?.buy_target, color: '#00ff88' },
                    { label: 'Sell Target', val: research?.sell_target, color: '#4488ff' },
                    { label: 'Stop Loss', val: research?.stop_loss, color: '#ff4444' },
                  ].map(({ label, val, color }) => (
                    <div key={label}>
                      <div style={{ fontSize: '11px', color: '#888', marginBottom: '2px' }}>{label}</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold', color: val ? color : '#444' }}>
                        {val ? `$${parseFloat(val).toFixed(2)}` : '--'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Status & Position Size (edit mode) */}
            {editMode && (
              <div style={{
                backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a',
                borderRadius: '6px', padding: '14px', marginBottom: '16px',
              }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>Status</label>
                    <select
                      value={editData.status}
                      onChange={(e) => setEditData({ ...editData, status: e.target.value })}
                      style={{
                        width: '100%', padding: '6px 8px', backgroundColor: '#0a0a0a',
                        border: '1px solid #2a2a2a', borderRadius: '4px', color: '#fff', fontSize: '13px',
                      }}
                    >
                      <option value="active">Active</option>
                      <option value="watchlist">Watchlist</option>
                      <option value="dormant">Dormant</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', color: '#888', display: 'block', marginBottom: '4px' }}>Position Size</label>
                    <input
                      value={editData.position_size}
                      onChange={(e) => setEditData({ ...editData, position_size: e.target.value })}
                      placeholder="e.g. 3% of portfolio"
                      style={{
                        width: '100%', padding: '6px 8px', backgroundColor: '#0a0a0a',
                        border: '1px solid #2a2a2a', borderRadius: '4px', color: '#fff', fontSize: '13px',
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Catalysts & Risks */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
              {/* Catalysts */}
              <div style={{
                backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a',
                borderRadius: '6px', padding: '14px',
              }}>
                <h4 style={{ color: '#00ff88', margin: '0 0 8px 0', fontSize: '13px' }}>Catalysts</h4>
                {editMode && (
                  <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
                    <input
                      value={catalystInput}
                      onChange={(e) => setCatalystInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCatalyst(); } }}
                      placeholder="Add catalyst"
                      style={{
                        flex: 1, padding: '4px 8px', backgroundColor: '#0a0a0a',
                        border: '1px solid #2a2a2a', borderRadius: '4px', color: '#fff', fontSize: '12px',
                      }}
                    />
                    <button onClick={addCatalyst} style={{
                      padding: '4px 8px', backgroundColor: '#00ff88', color: '#000',
                      border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold',
                    }}>+</button>
                  </div>
                )}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {(editMode ? editData.catalysts : (research?.catalysts || [])).map((c, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '4px 8px', backgroundColor: '#0a0a0a', borderRadius: '4px',
                      fontSize: '12px', color: '#aaa',
                    }}>
                      <span>{c}</span>
                      {editMode && (
                        <button onClick={() => removeCatalyst(c)} style={{
                          background: 'none', border: 'none', color: '#ff4444',
                          cursor: 'pointer', fontSize: '14px', padding: 0,
                        }}>x</button>
                      )}
                    </div>
                  ))}
                  {(editMode ? editData.catalysts : (research?.catalysts || [])).length === 0 && (
                    <div style={{ color: '#444', fontSize: '12px' }}>None yet</div>
                  )}
                </div>
              </div>

              {/* Risks */}
              <div style={{
                backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a',
                borderRadius: '6px', padding: '14px',
              }}>
                <h4 style={{ color: '#ff4444', margin: '0 0 8px 0', fontSize: '13px' }}>Risks</h4>
                {editMode && (
                  <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
                    <input
                      value={riskInput}
                      onChange={(e) => setRiskInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addRisk(); } }}
                      placeholder="Add risk"
                      style={{
                        flex: 1, padding: '4px 8px', backgroundColor: '#0a0a0a',
                        border: '1px solid #2a2a2a', borderRadius: '4px', color: '#fff', fontSize: '12px',
                      }}
                    />
                    <button onClick={addRisk} style={{
                      padding: '4px 8px', backgroundColor: '#ff4444', color: '#fff',
                      border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold',
                    }}>+</button>
                  </div>
                )}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {(editMode ? editData.risks : (research?.risks || [])).map((r, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '4px 8px', backgroundColor: '#0a0a0a', borderRadius: '4px',
                      fontSize: '12px', color: '#aaa',
                    }}>
                      <span>{r}</span>
                      {editMode && (
                        <button onClick={() => removeRisk(r)} style={{
                          background: 'none', border: 'none', color: '#ff4444',
                          cursor: 'pointer', fontSize: '14px', padding: 0,
                        }}>x</button>
                      )}
                    </div>
                  ))}
                  {(editMode ? editData.risks : (research?.risks || [])).length === 0 && (
                    <div style={{ color: '#444', fontSize: '12px' }}>None yet</div>
                  )}
                </div>
              </div>
            </div>

            {/* Save / Cancel for edit mode */}
            {editMode && (
              <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                <button
                  onClick={handleSave} disabled={saving}
                  style={{
                    flex: 1, padding: '10px', backgroundColor: '#00ff88', color: '#000',
                    border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold',
                  }}
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
                <button
                  onClick={() => { setEditMode(false); loadResearch(); }}
                  style={{
                    padding: '10px 20px', backgroundColor: '#2a2a2a', color: '#fff',
                    border: 'none', borderRadius: '4px', cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
              </div>
            )}

            {/* Research Notes (view mode) */}
            {!editMode && research?.notes && (
              <div style={{
                backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a',
                borderRadius: '6px', padding: '14px', marginBottom: '16px',
              }}>
                <h4 style={{ color: '#fff', margin: '0 0 8px 0', fontSize: '14px' }}>Notes</h4>
                <p style={{ color: '#aaa', fontSize: '13px', lineHeight: '1.5', margin: 0, whiteSpace: 'pre-wrap' }}>
                  {research.notes}
                </p>
              </div>
            )}

            {/* Notes textarea in edit mode */}
            {editMode && (
              <div style={{
                backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a',
                borderRadius: '6px', padding: '14px', marginBottom: '16px',
              }}>
                <h4 style={{ color: '#fff', margin: '0 0 8px 0', fontSize: '14px' }}>Notes</h4>
                <textarea
                  value={editData.notes}
                  onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                  placeholder="Research notes, thesis, key observations..."
                  style={{
                    width: '100%', minHeight: '100px', padding: '10px',
                    backgroundColor: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: '4px',
                    color: '#fff', fontSize: '13px', fontFamily: 'inherit', boxSizing: 'border-box',
                    resize: 'vertical',
                  }}
                />
              </div>
            )}

            {/* Quick Add Note */}
            <div style={{
              backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a',
              borderRadius: '6px', padding: '14px', marginBottom: '16px',
            }}>
              <h4 style={{ color: '#fff', margin: '0 0 8px 0', fontSize: '14px' }}>Add Entry</h4>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  value={noteInput}
                  onChange={(e) => setNoteInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleAddNote(); }}
                  placeholder="Quick note, observation, or update..."
                  style={{
                    flex: 1, padding: '8px 10px', backgroundColor: '#0a0a0a',
                    border: '1px solid #2a2a2a', borderRadius: '4px', color: '#fff', fontSize: '13px',
                  }}
                />
                <button onClick={handleAddNote} style={{
                  padding: '8px 16px', backgroundColor: '#00ff88', color: '#000',
                  border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px',
                }}>Add</button>
              </div>
            </div>

            {/* Research Entry Log */}
            <div style={{
              backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a',
              borderRadius: '6px', padding: '14px',
            }}>
              <h4 style={{ color: '#fff', margin: '0 0 12px 0', fontSize: '14px' }}>
                Research Log
              </h4>
              {(!research?.recent_entries || research.recent_entries.length === 0) ? (
                <div style={{ color: '#444', fontSize: '12px' }}>No entries yet</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {research.recent_entries.map((entry) => {
                    const typeColors = {
                      note: '#888', buy_signal: '#00ff88', sell_signal: '#ff4444',
                      thesis_update: '#4488ff', ai_analysis: '#ff9ff3',
                    };
                    return (
                      <div key={entry.id} style={{
                        padding: '10px 12px', backgroundColor: '#0a0a0a',
                        borderRadius: '4px', borderLeft: `3px solid ${typeColors[entry.entry_type] || '#888'}`,
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{
                            fontSize: '10px', fontWeight: 'bold', textTransform: 'uppercase',
                            color: typeColors[entry.entry_type] || '#888',
                          }}>
                            {entry.entry_type?.replace('_', ' ')}
                          </span>
                          <span style={{ fontSize: '10px', color: '#555' }}>
                            {entry.created_at ? new Date(entry.created_at).toLocaleDateString() : ''}
                          </span>
                        </div>
                        <p style={{ color: '#ccc', fontSize: '12px', lineHeight: '1.4', margin: 0 }}>
                          {entry.content}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default StockDetailPanel;
