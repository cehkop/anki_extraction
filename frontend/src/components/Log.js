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
              // We assume logs like "Response: {...}" or "Added Cards: {...}"
              if (log.startsWith('Response:') || log.startsWith('Added Cards:')) {
                const jsonString = log.substring(log.indexOf(':') + 1).trim();
                parsedLog = JSON.parse(jsonString);
                isJson = true;
              }
            } catch (error) {
              console.error('Error parsing log JSON:', error);
            }

            if (isJson && parsedLog) {
              // 1) Check if we have `cards` in the response
              if (parsedLog.cards && Array.isArray(parsedLog.cards)) {
                // Filter out cards with the specific "Anki is not running..." status
                const filteredCards = parsedLog.cards.filter(
                  (card) =>
                    card.Status &&
                    card.Status.trim() !== 'Anki is not running. Please launch Anki and ensure AnkiConnect is enabled.'
                );
            
                // If no cards are left after filtering, skip rendering this log
                if (filteredCards.length === 0) {
                  return null; // No cards to display
                }
            
                // Render the filtered cards
                return (
                  <Box key={index} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontSize: '0.75rem', color: '#fff' }}>
                      {log.startsWith('Added Cards:') ? 'Added Cards' : 'Cards'}
                    </Typography>
                    {filteredCards.map((card, cardIndex) => {
                      // If card.Status is "OK", color = green; otherwise red
                      const isSuccess = card.Status === 'OK';
                      const bgColor = isSuccess ? '#003300' : '#330000';
            
                      return (
                        <Box
                          key={cardIndex}
                          sx={{
                            backgroundColor: bgColor,
                            color: 'white',
                            p: 0.5,
                            mb: 0.5,
                            borderRadius: 1,
                            fontSize: '0.65rem',
                          }}
                        >
                          <strong>Front:</strong> {card.Front} <br />
                          <strong>Back:</strong> {card.Back}
                          {/* If Status is not OK, show error text in smaller font */}
                          {!isSuccess && card.Status && (
                            <Box
                              component="div"
                              sx={{
                                mt: 0.5,
                                fontSize: '0.6rem',
                                color: '#ffcccc',
                              }}
                            >
                              {card.Status}
                            </Box>
                          )}
                        </Box>
                      );
                    })}
                  </Box>
                );
              }
            
              // 2) Fallback if the parsed JSON doesn't have `cards`
              return (
                <Typography key={index} variant="body2" sx={{ fontSize: '0.65rem', color: '#ccc' }}>
                  {log}
                </Typography>
              );            
            } else {
              // Non-JSON logs
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
