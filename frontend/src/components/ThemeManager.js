import React, { useState, useEffect } from 'react';
import { getThemes, createTheme, updateTheme, deleteTheme, getTickerNames } from '../api/client';
import ThemeForm from './ThemeForm';
import TickerSuggestionPanel from './TickerSuggestionPanel';

const ThemeManager = ({ onThemeSelect, onTickerClick, isExpanded, onToggleExpand }) => {
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingTheme, setEditingTheme] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [suggestingTheme, setSuggestingTheme] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [compact, setCompact] = useState(false);
  const [tickerNames, setTickerNames] = useState({});

  useEffect(() => {
    loadThemes();
  }, []);

  // Fetch company names whenever themes change
  useEffect(() => {
    const allTickers = [...new Set(themes.flatMap(t => t.tickers || []))];
    const missing = allTickers.filter(t => !tickerNames[t]);
    if (missing.length > 0) {
      getTickerNames(missing).then(names => {
        setTickerNames(prev => ({ ...prev, ...names }));
      }).catch(() => {});
    }
  }, [themes]);

  const loadThemes = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getThemes();
      setThemes(Array.isArray(data) ? data : []);
    } catch (err) {
      setError('Failed to load themes');
      setThemes([]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewTheme = () => {
    setEditingTheme(null);
    setShowForm(true);
  };

  const handleEditTheme = (theme) => {
    setEditingTheme(theme);
    setShowForm(true);
  };

  const handleSaveTheme = async (formData) => {
    try {
      if (editingTheme) {
        await updateTheme(editingTheme.id, formData);
      } else {
        await createTheme(formData);
      }
      await loadThemes();
      setShowForm(false);
      setEditingTheme(null);
    } catch (err) {
      setError('Failed to save theme');
    }
  };

  const handleDeleteTheme = async (themeId) => {
    try {
      await deleteTheme(themeId);
      await loadThemes();
      setDeleteConfirm(null);
    } catch (err) {
      setError('Failed to delete theme');
    }
  };

  const filteredThemes = themes.filter((theme) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (theme.name || '').toLowerCase().includes(q) ||
      (theme.thesis || '').toLowerCase().includes(q) ||
      (theme.tickers || []).some((t) => t.toLowerCase().includes(q)) ||
      (theme.tags || []).some((t) => t.toLowerCase().includes(q))
    );
  });

  const getTagColor = (tag) => {
    const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd', '#00d2d3'];
    const hash = tag.charCodeAt(0) + tag.charCodeAt(tag.length - 1);
    return colors[hash % colors.length];
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#1a1a1a',
        padding: '20px',
        borderRadius: '8px',
        border: '1px solid #2a2a2a',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
        }}
      >
        <h2 style={{ color: '#ffffff', margin: 0 }}>
          Themes
          {themes.length > 0 && (
            <span style={{ color: '#555', fontSize: '13px', fontWeight: 'normal', marginLeft: '8px' }}>
              {searchQuery ? `${filteredThemes.length}/` : ''}{themes.length}
            </span>
          )}
        </h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={() => setCompact(!compact)}
            title={compact ? 'Expanded view' : 'Compact view'}
            style={{
              padding: '6px 10px',
              backgroundColor: '#2a2a2a',
              color: compact ? '#00ff88' : '#888',
              border: `1px solid ${compact ? '#00ff8844' : '#333'}`,
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
            }}
          >
            {compact ? '▤' : '▦'}
          </button>
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
          <button
            onClick={handleNewTheme}
            style={{
              padding: '8px 16px',
              backgroundColor: '#00ff88',
              color: '#000',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '14px',
            }}
          >
            + New Theme
          </button>
        </div>
      </div>

      {/* Search bar — shown when 5+ themes */}
      {themes.length >= 5 && (
        <div style={{ marginBottom: '12px' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search themes, tickers, tags..."
            style={{
              width: '100%',
              padding: '8px 12px',
              backgroundColor: '#0a0a0a',
              color: '#fff',
              border: '1px solid #333',
              borderRadius: '4px',
              fontSize: '13px',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
      )}

      {error && (
        <div
          style={{
            backgroundColor: '#3a1a1a',
            color: '#ff6b6b',
            padding: '12px',
            borderRadius: '4px',
            marginBottom: '12px',
            fontSize: '12px',
          }}
        >
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ color: '#888', padding: '20px', textAlign: 'center' }}>
          Loading themes...
        </div>
      ) : themes.length === 0 ? (
        <div style={{ color: '#888', padding: '20px', textAlign: 'center' }}>
          No themes yet. Create your first theme!
        </div>
      ) : filteredThemes.length === 0 ? (
        <div style={{ color: '#888', padding: '20px', textAlign: 'center' }}>
          No themes match "{searchQuery}"
        </div>
      ) : (
        <div
          style={{
            overflowY: 'auto',
            flex: 1,
          }}
        >
          {filteredThemes.map((theme) => (
            <div
              key={theme.id}
              style={{
                backgroundColor: '#0a0a0a',
                border: '1px solid #2a2a2a',
                borderRadius: '6px',
                padding: compact ? '8px 12px' : '12px',
                marginBottom: compact ? '4px' : '12px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#00ff88';
                e.currentTarget.style.boxShadow = '0 0 8px rgba(0, 255, 136, 0.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#2a2a2a';
                e.currentTarget.style.boxShadow = 'none';
              }}
              onClick={() => onThemeSelect(theme)}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: compact ? 0 : '10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                  <h3 style={{ color: '#00ff88', margin: 0, fontSize: compact ? '14px' : '16px', whiteSpace: 'nowrap' }}>
                    {theme.name}
                  </h3>
                  <span style={{ color: '#555', fontSize: '11px', whiteSpace: 'nowrap' }}>
                    {theme.tickers && theme.tickers.length} tickers
                  </span>
                  {compact && theme.tags && theme.tags.length > 0 && (
                    <div style={{ display: 'flex', gap: '4px', overflow: 'hidden' }}>
                      {theme.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          style={{
                            backgroundColor: getTagColor(tag),
                            color: '#ffffff',
                            padding: '1px 6px',
                            borderRadius: '8px',
                            fontSize: '10px',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div
                  style={{ display: 'flex', gap: '8px', flexShrink: 0 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSuggestingTheme(theme);
                    }}
                    style={{
                      padding: '4px 12px',
                      backgroundColor: '#2a2a3a',
                      color: '#bb88ff',
                      border: '1px solid #3a2a4a',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '12px',
                    }}
                  >
                    Suggest
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEditTheme(theme);
                    }}
                    style={{
                      padding: '4px 12px',
                      backgroundColor: '#2a2a4a',
                      color: '#88ff88',
                      border: '1px solid #2a4a2a',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '12px',
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteConfirm(theme.id);
                    }}
                    style={{
                      padding: '4px 12px',
                      backgroundColor: '#4a2a2a',
                      color: '#ff8888',
                      border: '1px solid #4a2a2a',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '12px',
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>

              {!compact && theme.thesis && (
                <p
                  style={{
                    color: '#aaa',
                    fontSize: '12px',
                    margin: '8px 0',
                    lineHeight: '1.4',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {theme.thesis}
                </p>
              )}

              {/* Clickable ticker chips */}
              {!compact && theme.tickers && theme.tickers.length > 0 && (
                <div
                  style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {theme.tickers.map((t) => (
                    <span
                      key={t}
                      onClick={() => onTickerClick && onTickerClick(t)}
                      title={tickerNames[t] || t}
                      style={{
                        backgroundColor: '#1a3a1a',
                        color: '#00ff88',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '11px',
                        cursor: 'pointer',
                        border: '1px solid #00ff8833',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}

              {!compact && theme.tags && theme.tags.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                  {theme.tags.map((tag) => (
                    <span
                      key={tag}
                      style={{
                        backgroundColor: getTagColor(tag),
                        color: '#ffffff',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '11px',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1001,
          }}
          onClick={() => setDeleteConfirm(null)}
        >
          <div
            style={{
              backgroundColor: '#0a0a0a',
              border: '1px solid #2a2a2a',
              borderRadius: '8px',
              padding: '24px',
              width: '90%',
              maxWidth: '400px',
              color: '#ffffff',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 16px 0', color: '#ff8888' }}>Delete Theme</h3>
            <p style={{ color: '#aaa', marginBottom: '20px' }}>
              Are you sure you want to delete this theme? This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeleteConfirm(null)}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#2a2a2a',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  handleDeleteTheme(deleteConfirm);
                }}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#ff4444',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Theme Form Modal */}
      {showForm && (
        <ThemeForm
          theme={editingTheme}
          onSave={handleSaveTheme}
          onCancel={() => {
            setShowForm(false);
            setEditingTheme(null);
          }}
        />
      )}

      {/* Ticker Suggestion Modal */}
      {suggestingTheme && (
        <TickerSuggestionPanel
          theme={suggestingTheme}
          onClose={() => setSuggestingTheme(null)}
          onTickersAdded={loadThemes}
        />
      )}
    </div>
  );
};

export default ThemeManager;
