// src/components/TextForm.js

import React, { useState } from 'react';
import { TextField, Button, Box } from '@mui/material';
import axios from 'axios';
import ManualCardReview from './ManualCardReview';

function TextForm({ handleLog, deckName, processingMode }) {
  const [text, setText] = useState('');
  const [extractedPairs, setExtractedPairs] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!text.trim()) {
      alert('Please enter some text.');
      return;
    }

    if (processingMode === 'auto') {
      // Automatic Processing
      try {
        const res = await axios.post('http://localhost:2341/process_text', {
          text,
          deckName,
        });
        handleLog(`Text Response: ${JSON.stringify(res.data, null, 2)}`);
        setText('');
      } catch (error) {
        console.error(error);
        handleLog('Error processing text.');
      }
    } else {
      // After receiving the response in manual processing
    try {
      const res = await axios.post('http://localhost:2341/extract_text', {
        text,
      });
      console.log('Extracted pairs:', res.data.pairs); // Add this line
      setExtractedPairs(res.data.pairs);
    } catch (error) {
      console.error(error);
      handleLog('Error extracting pairs.');
    }
    }
  };

  const handleClear = () => {
    setText('');
    setExtractedPairs(null);
  };

  const handleManualSubmit = async (selectedPairs) => {
    try {
      const res = await axios.post('http://localhost:2341/add_cards', {
        deckName,
        pairs: selectedPairs,
      });
      handleLog(`Added Cards: ${JSON.stringify(res.data, null, 2)}`);
      setExtractedPairs(null);
      // Do not clear the text here so that the input remains for comparison
    } catch (error) {
      console.error(error);
      handleLog('Error adding cards.');
    }
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
        disabled={processingMode === 'manual' && extractedPairs !== null}
      />
      <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          type="submit"
          disabled={processingMode === 'manual' && extractedPairs !== null}
        >
          Submit
        </Button>
        <Button variant="outlined" color="error" onClick={handleClear}>
          Clear
        </Button>
      </Box>

      {extractedPairs && (
        <ManualCardReview
          pairs={extractedPairs}
          onSubmit={handleManualSubmit}
          onCancel={handleClear}
        />
      )}
    </Box>
  );
}

export default TextForm;
