import React, { useState, useEffect, useCallback } from 'react';
import TopBar from './components/TopBar';
import RRGChart from './components/RRGChart';
import ThemeManager from './components/ThemeManager';
import SignalsPanel from './components/SignalsPanel';
import StockDetailPanel from './components/StockDetailPanel';
import './App.css';

function App() {
  const [selectedTheme, setSelectedTheme] = useState(null);
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [expandedPanel, setExpandedPanel] = useState(null);

  const togglePanel = useCallback((panel) => {
    setExpandedPanel(prev => prev === panel ? null : panel);
  }, []);

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape' && expandedPanel) setExpandedPanel(null);
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [expandedPanel]);

  const rrgChart = (
    <RRGChart
      isExpanded={expandedPanel === 'rrg'}
      onToggleExpand={() => togglePanel('rrg')}
    />
  );

  const signalsPanel = (
    <SignalsPanel
      selectedTheme={selectedTheme}
      onTickerClick={setSelectedTicker}
      isExpanded={expandedPanel === 'signals'}
      onToggleExpand={() => togglePanel('signals')}
    />
  );

  const themeManager = (
    <ThemeManager
      onThemeSelect={setSelectedTheme}
      onTickerClick={setSelectedTicker}
      isExpanded={expandedPanel === 'themes'}
      onToggleExpand={() => togglePanel('themes')}
    />
  );

  return (
    <div className="app-container">
      <TopBar />

      {expandedPanel && (
        <div className="fullscreen-overlay">
          {expandedPanel === 'rrg' && rrgChart}
          {expandedPanel === 'signals' && signalsPanel}
          {expandedPanel === 'themes' && themeManager}
        </div>
      )}

      <div className="main-content" style={expandedPanel ? { visibility: 'hidden' } : undefined}>
        <div className="left-section">
          {!expandedPanel && rrgChart}
          <div className="signals-wrapper">
            {!expandedPanel && signalsPanel}
          </div>
        </div>

        <div className="right-section">
          {!expandedPanel && themeManager}
        </div>
      </div>

      {selectedTicker && (
        <StockDetailPanel
          ticker={selectedTicker}
          onClose={() => setSelectedTicker(null)}
        />
      )}
    </div>
  );
}

export default App;
