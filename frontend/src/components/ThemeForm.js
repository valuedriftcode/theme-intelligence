import React, { useState, useEffect } from 'react';

const ThemeForm = ({ theme, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: '',
    thesis: '',
    tickers: [],
    tags: [],
  });

  const [tickerInput, setTickerInput] = useState('');
  const [tagInput, setTagInput] = useState('');

  useEffect(() => {
    if (theme) {
      setFormData(theme);
      setTickerInput('');
      setTagInput('');
    }
  }, [theme]);

  const handleNameChange = (e) => {
    setFormData({ ...formData, name: e.target.value });
  };

  const handleThesisChange = (e) => {
    setFormData({ ...formData, thesis: e.target.value });
  };

  const handleTickerInputChange = (e) => {
    setTickerInput(e.target.value);
  };

  const handleTagInputChange = (e) => {
    setTagInput(e.target.value);
  };

  const addTicker = () => {
    if (tickerInput.trim()) {
      const newTicker = tickerInput.trim().toUpperCase();
      if (!formData.tickers.includes(newTicker)) {
        setFormData({
          ...formData,
          tickers: [...formData.tickers, newTicker],
        });
      }
      setTickerInput('');
    }
  };

  const removeTicker = (ticker) => {
    setFormData({
      ...formData,
      tickers: formData.tickers.filter((t) => t !== ticker),
    });
  };

  const addTag = () => {
    if (tagInput.trim()) {
      const newTag = tagInput.trim().toLowerCase();
      if (!formData.tags.includes(newTag)) {
        setFormData({
          ...formData,
          tags: [...formData.tags, newTag],
        });
      }
      setTagInput('');
    }
  };

  const removeTag = (tag) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter((t) => t !== tag),
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.name.trim()) {
      onSave(formData);
    }
  };

  const getTagColor = (tag) => {
    const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd', '#00d2d3'];
    const hash = tag.charCodeAt(0) + tag.charCodeAt(tag.length - 1);
    return colors[hash % colors.length];
  };

  return (
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
        zIndex: 1000,
      }}
      onClick={onCancel}
    >
      <div
        style={{
          backgroundColor: '#0a0a0a',
          border: '1px solid #2a2a2a',
          borderRadius: '8px',
          padding: '24px',
          width: '90%',
          maxWidth: '500px',
          maxHeight: '90vh',
          overflowY: 'auto',
          color: '#ffffff',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ margin: '0 0 20px 0', color: '#00ff88' }}>
          {theme ? 'Edit Theme' : 'Create New Theme'}
        </h2>

        <form onSubmit={handleSubmit}>
          {/* Name */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#aaa' }}>
              Theme Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={handleNameChange}
              placeholder="e.g., Artificial Intelligence"
              style={{
                width: '100%',
                padding: '10px',
                backgroundColor: '#1a1a1a',
                border: '1px solid #2a2a2a',
                borderRadius: '4px',
                color: '#ffffff',
                fontSize: '14px',
                boxSizing: 'border-box',
              }}
              required
            />
          </div>

          {/* Thesis */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#aaa' }}>
              Investment Thesis
            </label>
            <textarea
              value={formData.thesis}
              onChange={handleThesisChange}
              placeholder="Describe the investment thesis for this theme..."
              style={{
                width: '100%',
                padding: '10px',
                backgroundColor: '#1a1a1a',
                border: '1px solid #2a2a2a',
                borderRadius: '4px',
                color: '#ffffff',
                fontSize: '14px',
                boxSizing: 'border-box',
                minHeight: '100px',
                fontFamily: 'inherit',
              }}
            />
          </div>

          {/* Tickers */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#aaa' }}>
              Tickers
            </label>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
              <input
                type="text"
                value={tickerInput}
                onChange={handleTickerInputChange}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addTicker();
                  }
                }}
                placeholder="Enter ticker symbol"
                style={{
                  flex: 1,
                  padding: '8px',
                  backgroundColor: '#1a1a1a',
                  border: '1px solid #2a2a2a',
                  borderRadius: '4px',
                  color: '#ffffff',
                  fontSize: '14px',
                }}
              />
              <button
                type="button"
                onClick={addTicker}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#00ff88',
                  color: '#000',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                }}
              >
                Add
              </button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {formData.tickers.map((ticker) => (
                <div
                  key={ticker}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: '#1a3a1a',
                    border: '1px solid #00ff88',
                    borderRadius: '20px',
                    padding: '4px 12px',
                    fontSize: '12px',
                  }}
                >
                  {ticker}
                  <button
                    type="button"
                    onClick={() => removeTicker(ticker)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#ff4444',
                      cursor: 'pointer',
                      fontSize: '16px',
                      padding: 0,
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Tags */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#aaa' }}>
              Tags
            </label>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
              <input
                type="text"
                value={tagInput}
                onChange={handleTagInputChange}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addTag();
                  }
                }}
                placeholder="Enter tag"
                style={{
                  flex: 1,
                  padding: '8px',
                  backgroundColor: '#1a1a1a',
                  border: '1px solid #2a2a2a',
                  borderRadius: '4px',
                  color: '#ffffff',
                  fontSize: '14px',
                }}
              />
              <button
                type="button"
                onClick={addTag}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#00ff88',
                  color: '#000',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                }}
              >
                Add
              </button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {formData.tags.map((tag) => (
                <div
                  key={tag}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: getTagColor(tag),
                    color: '#ffffff',
                    borderRadius: '20px',
                    padding: '4px 12px',
                    fontSize: '12px',
                  }}
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#ffffff',
                      cursor: 'pointer',
                      fontSize: '16px',
                      padding: 0,
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Buttons */}
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={onCancel}
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
              type="submit"
              style={{
                padding: '10px 20px',
                backgroundColor: '#00ff88',
                color: '#000',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold',
              }}
            >
              Save Theme
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ThemeForm;
