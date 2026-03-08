import React, { useState } from 'react';
import TopBar from './components/TopBar';
import RRGChart from './components/RRGChart';
import ThemeManager from './components/ThemeManager';
import SignalsPanel from './components/SignalsPanel';
import StockDetailPanel from './components/StockDetailPanel';
import './App.css';

function App() {
  const [selectedTheme, setSelectedTheme] = useState(null);
  const [selectedTicker, setSelectedTicker] = useState(null);

  return (
    <div className="app-container">
      <TopBar />

      <div className="main-content">
        <div className="left-section">
          <RRGChart />
          <div className="signals-wrapper">
            <SignalsPanel
              selectedTheme={selectedTheme}
              onTickerClick={setSelectedTicker}
            />
          </div>
        </div>

        <div className="right-section">
          <ThemeManager
            onThemeSelect={setSelectedTheme}
            onTickerClick={setSelectedTicker}
          />
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
