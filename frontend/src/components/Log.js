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
        behavior: 'smooth', // Smooth scrolling to the top
      });
    }
  }, [logs]);

  return (
    <Paper
      sx={{
        padding: 2,
        height: '100%', // Ensure the Paper fills the available height
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
              if (log.startsWith('Image Response:')) {
                const jsonString = log.substring('Image Response:'.length);
                parsedLog = JSON.parse(jsonString);
                isJson = true;
              } else if (log.startsWith('Text Response:')) {
                const jsonString = log.substring('Text Response:'.length);
                parsedLog = JSON.parse(jsonString);
                isJson = true;
              }
            } catch (error) {
              console.error('Error parsing log JSON:', error);
            }

            if (isJson && parsedLog) {
              const elements = [];

              if (parsedLog.results) {
                // Handle Image Response
                elements.push(
                  <Box key={index} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>
                      Image Response
                    </Typography>
                    {parsedLog.results.map((result, idx) => {
                      const imageName = result.Image;
                      const pairs = result.Pairs || [];

                      return (
                        <Box key={`${index}-${idx}`} sx={{ mb: 2 }}>
                          <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>
                            {`Image: ${imageName}`}
                          </Typography>
                          {pairs.map((pair, pairIndex) => {
                            const success = pair.Status;
                            return (
                              <Box
                                key={pairIndex}
                                sx={{
                                  backgroundColor: success ? '#003300' : '#330000',
                                  color: 'white',
                                  p: 1,
                                  mb: 1,
                                  borderRadius: 1,
                                }}
                              >
                                <Typography variant="body2" sx={{ fontSize: '0.65rem' }}>
                                  <strong>Front:</strong> {pair.Front}
                                </Typography>
                                <Typography variant="body2" sx={{ fontSize: '0.65rem' }}>
                                  <strong>Back:</strong> {pair.Back}
                                </Typography>
                              </Box>
                            );
                          })}
                        </Box>
                      );
                    })}
                  </Box>
                );
              } else if (parsedLog.status) {
                // Handle Text Response
                elements.push(
                  <Box key={index} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontSize: '0.7rem' }}>
                      Text Response
                    </Typography>
                    {parsedLog.status.map((pair, pairIndex) => {
                      const success = pair.Status;
                      return (
                        <Box
                          key={pairIndex}
                          sx={{
                            backgroundColor: success ? '#003300' : '#330000',
                            color: 'white',
                            p: 1,
                            mb: 1,
                            borderRadius: 1,
                          }}
                        >
                          <Typography variant="body2" sx={{ fontSize: '0.65rem' }}>
                            <strong>Front:</strong> {pair.Front}
                          </Typography>
                          <Typography variant="body2" sx={{ fontSize: '0.65rem' }}>
                            <strong>Back:</strong> {pair.Back}
                          </Typography>
                        </Box>
                      );
                    })}
                  </Box>
                );
              } else {
                // Unknown format
                elements.push(
                  <Typography key={index} variant="body2" sx={{ fontSize: '0.65rem' }}>
                    {log}
                  </Typography>
                );
              }

              return (
                <React.Fragment key={index}>
                  {elements}
                </React.Fragment>
              );
            } else {
              // Not JSON or parsing error
              return (
                <Typography key={index} variant="body2" sx={{ fontSize: '0.65rem' }}>
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
