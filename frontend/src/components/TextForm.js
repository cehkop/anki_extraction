// src/components/TextForm.js

import React, { useState } from 'react';
import axios from 'axios';
import { TextField, Button, Box } from '@mui/material';

function TextForm({ handleLog }) {
  const [text, setText] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (text.trim() === '') {
      alert('Please enter some text.');
      return;
    }
    try {
      const res = await axios.post('http://localhost:2341/process_text', { text });
      handleLog(`Text Response: ${JSON.stringify(res.data, null, 2)}`);
      // You can choose to clear the text here if desired
      // setText('');
    } catch (error) {
      console.error(error);
      handleLog('Error processing text.');
    }
  };

  const handleClear = () => {
    setText('');
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <TextField
        label="Enter text to process"
        multiline
        rows={6}
        variant="outlined"
        fullWidth
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
        <Button variant="contained" type="submit">
          Submit
        </Button>
        <Button variant="outlined" color="error" onClick={handleClear}>
          Clear
        </Button>
      </Box>
    </Box>
  );
}

export default TextForm;
