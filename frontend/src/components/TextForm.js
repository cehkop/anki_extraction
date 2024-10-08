// src/components/TextForm.js

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { TextField, Button, Box } from '@mui/material';

function TextForm({ handleLog, deckName }) {
  const [text, setText] = useState('');

  // Handle text submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (text.trim() === '') {
      alert('Please enter some text.');
      return;
    }
    try {
      const res = await axios.post('http://localhost:2341/process_text', {
        text,
        deckName,
      });
      setText(''); // Clear the input field
      handleLog(`Text Response: ${JSON.stringify(res.data, null, 2)}`);
    } catch (error) {
      console.error(error);
      handleLog('Error processing text.');
    }
  };

  // Handle clear button
  const handleClear = () => {
    setText('');
  };

  // Handle paste events
  const handlePaste = async (event) => {
    const clipboardItems = event.clipboardData.items;
    for (let i = 0; i < clipboardItems.length; i++) {
      const item = clipboardItems[i];
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile();
        // Send the image file to the backend for OCR processing
        const formData = new FormData();
        formData.append('file', file);
        formData.append('deckName', deckName);

        try {
          const res = await axios.post('http://localhost:2341/process_pasted_image', formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });
          handleLog(`Image Paste Response: ${JSON.stringify(res.data, null, 2)}`);
        } catch (error) {
          console.error(error);
          handleLog('Error processing pasted image.');
        }

        event.preventDefault();
        return; // Exit after handling the image
      }
    }
  };

  useEffect(() => {
    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, [deckName]);

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
