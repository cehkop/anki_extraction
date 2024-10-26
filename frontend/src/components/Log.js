// src/components/Log.js

import React, { useEffect, useRef } from 'react';
import { Paper, Typography, Box } from '@mui/material';

function Log({ logs }) {
  const logContainerRef = useRef(null);

  // Scroll to the top each time new logs are added
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTo({
        top: 0,
        behavior: 'smooth',
      });
    }
  }, [logs]);

  return (
    <Paper
      sx={{
        padding: 2,
        height: '100%',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
      }}
      elevation={3}
    >
      <Typography variant="h6" gutterBottom>
        Log
      </Typography>
      <Box
        ref={logContainerRef}
        sx={{
          overflowY: 'auto',
          flexGrow: 1,
          minHeight: 0,
        }}
      >
        {logs
          .slice()
          .reverse()
          .map((log, index) => {
            let parsedLog;
            let isJson = false;

            try {
              if (log.startsWith('Image Response:') || log.startsWith('Text Response:') || log.startsWith('Added Cards:')) {
                const jsonString = log.substring(log.indexOf(':') + 1);
                parsedLog = JSON.parse(jsonString);
                isJson = true;
              }
            } catch (error) {
              console.error('Error parsing log JSON:', error);
            }

            if (isJson && parsedLog) {
              const elements = [];

              if (parsedLog.results) {
                elements.push(
                  <Box key={index} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontSize: '0.75rem', color: '#fff' }}>
                      Image Response
                    </Typography>
                    {parsedLog.results.map((result, idx) => (
                      <Box key={`${index}-${idx}`} sx={{ mb: 1 }}>
                        <Typography variant="body2" sx={{ fontSize: '0.7rem', color: '#ccc' }}>
                          {`Image: ${result.Image}`}
                        </Typography>
                        {(result.Pairs || []).map((pair, pairIndex) => (
                          <Box
                            key={pairIndex}
                            sx={{
                              backgroundColor: pair.Status ? '#003300' : '#330000',
                              color: 'white',
                              p: 0.5,
                              mb: 0.5,
                              borderRadius: 1,
                              fontSize: '0.65rem',
                            }}
                          >
                            <strong>Front:</strong> {pair.Front} <br />
                            <strong>Back:</strong> {pair.Back}
                          </Box>
                        ))}
                      </Box>
                    ))}
                  </Box>
                );
              } else if (parsedLog.status) {
                elements.push(
                  <Box key={index} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontSize: '0.75rem', color: '#fff' }}>
                      {log.startsWith('Added Cards:') ? 'Added Cards' : 'Text Response'}
                    </Typography>
                    {parsedLog.status.map((pair, pairIndex) => (
                      <Box
                        key={pairIndex}
                        sx={{
                          backgroundColor: pair.Status ? '#003300' : '#330000',
                          color: 'white',
                          p: 0.5,
                          mb: 0.5,
                          borderRadius: 1,
                          fontSize: '0.65rem',
                        }}
                      >
                        <strong>Front:</strong> {pair.Front} <br />
                        <strong>Back:</strong> {pair.Back}
                      </Box>
                    ))}
                  </Box>
                );
              } else {
                elements.push(
                  <Typography key={index} variant="body2" sx={{ fontSize: '0.65rem', color: '#ccc' }}>
                    {log}
                  </Typography>
                );
              }

              return <React.Fragment key={index}>{elements}</React.Fragment>;
            } else {
              return (
                <Typography key={index} variant="body2" sx={{ fontSize: '0.65rem', color: '#ccc' }}>
                  {log}
                </Typography>
              );
            }
          })}
      </Box>
    </Paper>
  );
}

export default Log;
