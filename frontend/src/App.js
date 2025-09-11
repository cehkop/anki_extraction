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
        {/* Sidebar */}
        <Grid
          item
          sx={{
            borderRight: '1px solid #444',
            height: '100%',
            flexBasis: '11.6667%', // 2 columns * 0.7 of 12-column grid
            maxWidth: '11.6667%',
          }}
        >
          <Config
            inputMode={inputMode}
            setInputMode={setInputMode}
            deckName={deckName}
            setDeckName={setDeckName}
            processingMode={processingMode}
            setProcessingMode={setProcessingMode}
          />
        </Grid>

        {/* Main Content */}
        <Grid
          item
          sx={{
            borderRight: '1px solid #444',
            height: '100%',
            flexBasis: '68.3333%', // remaining width after left (11.6667%) and right (20%)
            maxWidth: '68.3333%',
          }}
        >
          <InputSection
            inputMode={inputMode}
            handleLog={handleLog}
            deckName={deckName}
            processingMode={processingMode}
          />
        </Grid>

        {/* Log Section */}
        <Grid
          item
          sx={{
            height: '100%',
            flexBasis: '20%', // 3 columns * 0.8 of 12-column grid
            maxWidth: '20%',
          }}
        >
          <Log logs={logs} />
        </Grid>
      </Grid>
    </Box>
  );
}

export default App;
