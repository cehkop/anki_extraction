// src/App.js

import React, { useState } from 'react';
import Config from './components/Config';
import InputSection from './components/InputSection';
import Log from './components/Log';
import { Box, Grid } from '@mui/material';

function App() {
  const [inputMode, setInputMode] = useState('text');
  const [deckName, setDeckName] = useState('');
  const [processingMode, setProcessingMode] = useState('manual'); // New state for processing mode
  const [logs, setLogs] = useState([]);

  const handleLog = (logEntry) => {
    setLogs((prevLogs) => [...prevLogs, logEntry]);
  };

  return (
    <Box sx={{ flexGrow: 1, height: '100vh' }}>
      <Grid container sx={{ height: '100%' }}>
        <Grid item xs={2} sx={{ borderRight: '1px solid #444', height: '100%' }}>
          <Config
            inputMode={inputMode}
            setInputMode={setInputMode}
            deckName={deckName}
            setDeckName={setDeckName}
            processingMode={processingMode}
            setProcessingMode={setProcessingMode}
          />
        </Grid>
        <Grid item xs={7} sx={{ borderRight: '1px solid #444', height: '100%' }}>
          <InputSection
            inputMode={inputMode}
            handleLog={handleLog}
            deckName={deckName}
            processingMode={processingMode}
          />
        </Grid>
        <Grid item xs={3} sx={{ height: '100%' }}>
          <Log logs={logs} />
        </Grid>
      </Grid>
    </Box>
  );
}

export default App;
