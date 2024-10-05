// src/components/Config.js

import React from 'react';
import { Paper, Typography, FormControl, InputLabel, Select, MenuItem } from '@mui/material';

function Config({ inputMode, setInputMode }) {
  const handleInputChange = (e) => {
    setInputMode(e.target.value);
  };

  return (
    <Paper sx={{ padding: 2, height: '100%', boxSizing: 'border-box' }} elevation={3}>
      <Typography variant="h6" gutterBottom>
        Config
      </Typography>
      <FormControl fullWidth variant="outlined">
        <InputLabel id="input-mode-label">Input Mode</InputLabel>
        <Select
          labelId="input-mode-label"
          id="input-mode-select"
          value={inputMode}
          onChange={handleInputChange}
          label="Input Mode"
        >
          <MenuItem value="text">Text</MenuItem>
          <MenuItem value="image">Image</MenuItem>
        </Select>
      </FormControl>
    </Paper>
  );
}

export default Config;
