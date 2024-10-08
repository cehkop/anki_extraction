// src/App.js

import React, { useState } from 'react';
import Config from './components/Config';
import InputSection from './components/InputSection';
import Log from './components/Log';
import { Box, Grid } from '@mui/material';

function App() {
  const [inputMode, setInputMode] = useState('text');
  const [deckName, setDeckName] = useState(''); // New state for selected deck
  const [logs, setLogs] = useState([]);

  const handleLog = (logEntry) => {
    setLogs((prevLogs) => [...prevLogs, logEntry]);
  };

  return (
    <Box sx={{ flexGrow: 1, height: '100vh', overflow: 'hidden' }}>
      <Grid container sx={{ height: '100%' }}>
        <Grid item xs={2} sx={{ borderRight: '1px solid #444' }}>
          <Config
            inputMode={inputMode}
            setInputMode={setInputMode}
            deckName={deckName}
            setDeckName={setDeckName}
          />
        </Grid>
        <Grid item xs={8} sx={{ borderRight: '1px solid #444' }}>
          <InputSection
            inputMode={inputMode}
            handleLog={handleLog}
            deckName={deckName}
          />
        </Grid>
        <Grid item xs={2}>
          <Log logs={logs} />
        </Grid>
      </Grid>
    </Box>
  );
}

export default App;
