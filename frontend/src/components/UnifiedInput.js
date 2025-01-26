// src/components/UnifiedInput.js

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Box, Button, Typography, TextField } from '@mui/material';
import ManualCardReview from './ManualCardReview';
import { CustomFileInput } from './CustomFileInput';

function UnifiedInput({ handleLog, deckName, processingMode }) {
  const [inputText, setInputText] = useState('');
  const [extractedPairs, setExtractedPairs] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const fileInputRef = useRef();

  // ---------------------------------------------
  // 1) Handle user pasting images or text
  // ---------------------------------------------
  useEffect(() => {
    const handlePaste = (event) => {
      const clipboardItems = event.clipboardData.items;
      let foundImage = false;
      let foundText = false;

      // 1. Try to get text (if any)
      const pastedText = event.clipboardData.getData('text/plain');
      if (pastedText) {
        foundText = true;
      }

      // 2. Try to get image items (if any)
      let imageFiles = [];
      for (let i = 0; i < clipboardItems.length; i++) {
        const item = clipboardItems[i];
        if (item.type.startsWith('image/')) {
          foundImage = true;
          // Convert the clipboard item to a File object
          const file = item.getAsFile();
          if (file) {
            imageFiles.push(file);
          }
        }
      }

      // If we found text or image, prevent default so it doesn't do
      // anything else in the browser
      if (foundText || foundImage) {
        event.preventDefault();
      }

      // If text was found, append it to inputText
      if (foundText) {
        setInputText((prev) => (prev ? prev + '\n' + pastedText : pastedText));
      }

      // If images were found, append them to selectedFiles
      if (imageFiles.length > 0) {
        setSelectedFiles((prevFiles) => [...prevFiles, ...imageFiles]);
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, []);

  // ------------------------------------------------------------
  // 2) If user picks images via the <input type="file" /> or drag
  // ------------------------------------------------------------
  const handleFileChange = (files) => {
    setSelectedFiles(files);
  };

  // ---------------------------------------------
  // 3) Submit logic: send both text & images
  // ---------------------------------------------
  const handleSubmit = async (e) => {
    e.preventDefault();

    // At least one of inputText or selectedFiles must exist
    if (!inputText.trim() && selectedFiles.length === 0) {
      alert('Please provide text or images to process.');
      return;
    }

    // Prepare form data
    const formData = new FormData();
    formData.append('text', inputText);
    formData.append('deckName', deckName || '');
    formData.append('mode', processingMode || 'manual');

    selectedFiles.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const res = await axios.post('http://localhost:2341/process', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      console.log("Response from backend:", res.data);
      // If mode is 'auto', we typically get { status: [...] }
      // If mode is 'manual', we typically get { pairs: [...] }
      handleLog(`Response: ${JSON.stringify(res.data, null, 2)}`);

      if (processingMode === 'manual' && res.data.cards) {
        // Show pairs for user to confirm in ManualCardReview
        setExtractedPairs(res.data.cards);
      } else {
        // 'auto' flow or no pairs
        setInputText('');
        setSelectedFiles([]);
        fileInputRef.current.clear();
      }
    } catch (error) {
      console.error(error);
      handleLog('Error processing input.');
    }
  };

  // ---------------------------------------------
  // 4) Clear everything
  // ---------------------------------------------
  const handleClear = () => {
    setInputText('');
    setSelectedFiles([]);
    setExtractedPairs(null);
    fileInputRef.current.clear();
  };

  // ---------------------------------------------
  // 5) Final manual submission to /add_cards
  // ---------------------------------------------
  const handleManualSubmit = async (selectedPairs) => {
    try {
      const res = await axios.post('http://localhost:2341/add_cards', {
        deckName,
        pairs: selectedPairs,
      });
      handleLog(`Added Cards: ${JSON.stringify(res.data, null, 2)}`);

      // Clear everything
      setExtractedPairs(null);
      setInputText('');
      setSelectedFiles([]);
      fileInputRef.current.clear();
    } catch (error) {
      console.error(error);
      handleLog('Error adding cards.');
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      {/* Text input (optional) */}
      <TextField
        label="Enter text (optional)"
        multiline
        rows={4}
        variant="outlined"
        fullWidth
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        sx={{ mb: 2 }}
      />

      {/* File input for images (optional) */}
      <CustomFileInput ref={fileInputRef} onFileChange={handleFileChange} />

      {/* Buttons */}
      {!extractedPairs ? (
        <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
          <Button variant="contained" type="submit">
            Submit
          </Button>
          <Button variant="outlined" color="error" onClick={handleClear}>
            Clear
          </Button>
        </Box>
      ) : (
        <Box sx={{ mt: 2 }}>
          <ManualCardReview
            pairs={extractedPairs}
            onSubmit={handleManualSubmit}
            onCancel={handleClear}
          />
        </Box>
      )}
    </Box>
  );
}

export default UnifiedInput;
