// src/components/Log.js

import React from 'react';
import { Paper, Typography, List, ListItem, ListItemText } from '@mui/material';

function Log({ logs }) {
  return (
    <Paper sx={{ padding: 2, height: '100%', boxSizing: 'border-box', overflow: 'auto' }} elevation={3}>
      <Typography variant="h6" gutterBottom>
        Log
      </Typography>
      <List>
        {logs.map((log, index) => (
          <ListItem key={index} divider>
            <ListItemText primary={log} />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}

export default Log;
