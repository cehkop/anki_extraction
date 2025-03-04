// src/components/UnifiedInput.js

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Box, Button, TextField, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import ManualCardReview from './ManualCardReview';
import { CustomFileInput } from './CustomFileInput';

function UnifiedInput({ handleLog, deckName, processingMode }) {
  const [inputText, setInputText] = useState('');
  const [extractedPairs, setExtractedPairs] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [ankiError, setAnkiError] = useState(false); // State to control Dialog visibility
  const fileInputRef = useRef();

  // ----------------------------
  // 1) Handle paste text + images
  // ----------------------------
  useEffect(() => {
    const handlePaste = (event) => {
      const clipboardItems = event.clipboardData.items;
      let foundImage = false;
      let foundText = false;

      // Possibly text
      const pastedText = event.clipboardData.getData('text/plain');
      if (pastedText) {
        foundText = true;
      }

      // Possibly images
      let imageFiles = [];
      for (let i = 0; i < clipboardItems.length; i++) {
        const item = clipboardItems[i];
        if (item.type.startsWith('image/')) {
          foundImage = true;
          const file = item.getAsFile();
          if (file) {
            imageFiles.push(file);
          }
        }
      }

      if (foundText || foundImage) {
        event.preventDefault();
      }

      if (foundText) {
        setInputText((prev) => (prev ? prev + '\n' + pastedText : pastedText));
      }

      if (imageFiles.length > 0) {
        // Deduplicate by name+size
        setSelectedFiles((prevFiles) => {
          const newFiles = imageFiles.filter(
            (img) => !prevFiles.some((p) => p.name === img.name && p.size === img.size)
          );
          return [...prevFiles, ...newFiles];
        });
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, []);

  // ----------------------------------
  // 2) If user picks images in file input
  // ----------------------------------
  const handleFileChange = (files) => {
    // Deduplicate by name + size
    setSelectedFiles((prevFiles) => {
      const newFiles = files.filter(
        (file) => !prevFiles.some((p) => p.name === file.name && p.size === file.size)
      );
      return [...prevFiles, ...newFiles];
    });
  };

  // ----------------------------------
  // 3) Clear logic
  // ----------------------------------
  const handleManualCardsClear = () => {
    // For "manual" flow: we want to keep text, but reset extracted pairs & files
    setExtractedPairs(null);
  };

  const handleAllClear = () => {
    // Wipe everything: text, pairs, files
    setInputText('');
    setSelectedFiles([]);
    setExtractedPairs(null);
    if (fileInputRef.current) {
      fileInputRef.current.clear();
    }
  };

  // ----------------------------------
  // 4) Submission logic
  // ----------------------------------
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!inputText.trim() && selectedFiles.length === 0) {
      alert('Please provide text or images to process.');
      return;
    }

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
      handleLog(`Response: ${JSON.stringify(res.data, null, 2)}`);

      if (res.data.cards) {
        // Check if there's an ankiError
        const ankiErrorExists = res.data.cards.some(
          (card) =>
            card.Status ===
            "Anki is not running. Please launch Anki and ensure AnkiConnect is enabled."
        );

        if (ankiErrorExists) {
          setAnkiError(true);
        } else {
          // If all cards are "OK", then do a full clear
          const allSuccess = res.data.cards.every((card) => card.Status === "OK");
          if (allSuccess) {
            handleAllClear();
          }
        }
      }

      // If manual and there's "cards", show them
      if (processingMode === 'manual' && res.data.cards) {
        setExtractedPairs(res.data.cards);
      }
    } catch (error) {
      console.error(error);
      handleLog('Error processing input.');
    }
  };

  // Submit selected pairs from ManualCardReview
  const handleManualSubmit = async (selectedPairs) => {
    try {
      const res = await axios.post('http://localhost:2341/add_cards', {
        deckName,
        pairs: selectedPairs,
      });
      handleLog(`Added Cards: ${JSON.stringify(res.data, null, 2)}`);

      if (res.data.cards) {
        const ankiErrorExists = res.data.cards.some(
          (card) =>
            card.Status ===
            "Anki is not running. Please launch Anki and ensure AnkiConnect is enabled."
        );

        if (ankiErrorExists) {
          setAnkiError(true);
        } else {
          // If all new cards are "OK", clear everything
          const allSuccess = res.data.cards.every((card) => card.Status === "OK");
          if (allSuccess) {
            handleAllClear();
          }
        }
      }
    } catch (error) {
      console.error(error);
      handleLog('Error adding cards.');
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      {/* Text input */}
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

      {/* File input */}
      <CustomFileInput ref={fileInputRef} onFileChange={handleFileChange} />

      {/* Buttons */}
      {!extractedPairs ? (
        <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
          <Button variant="contained" type="submit">
            Submit
          </Button>
          <Button variant="outlined" color="error" onClick={handleAllClear}>
            Clear
          </Button>
        </Box>
      ) : (
        <Box sx={{ mt: 2 }}>
          <ManualCardReview
            pairs={extractedPairs}
            onSubmit={handleManualSubmit}
            onCancel={handleManualCardsClear}
          />
        </Box>
      )}

      {/* Dialog for Anki error */}
      <Dialog
        open={ankiError}
        onClose={() => setAnkiError(false)}
        aria-labelledby="anki-error-dialog"
      >
        <DialogTitle id="anki-error-dialog" sx={{ fontSize: '1.5rem' }}>
          Anki Error
        </DialogTitle>
        <DialogContent>
          Please launch Anki and ensure AnkiConnect is enabled.
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAnkiError(false)} autoFocus>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default UnifiedInput;
