// src/components/Config.js

import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Button,
  MenuItem,
  Select,
  TextField,
  Box,
} from '@mui/material';
import axios from 'axios';

function Config({ inputMode, setInputMode, deckName, setDeckName, processingMode, setProcessingMode }) {
  const [decks, setDecks] = useState([]);
  const [selectedDeck, setSelectedDeck] = useState('Default'); // Default deck name

  // Handle input mode change
  const handleInputChange = (e) => {
    setInputMode(e.target.value);
  };

  // Handle processing mode change
  const handleProcessingModeChange = (e) => {
    setProcessingMode(e.target.value);
  };

  // Handle deck name change
  const handleDeckChange = (e) => {
    setSelectedDeck(e.target.value);
    setDeckName(e.target.value);
  };

  // Handle manual deck name input
  const handleDeckNameInput = (e) => {
    setSelectedDeck(e.target.value);
    setDeckName(e.target.value);
  };

  // Fetch decks from the backend
  const fetchDecks = async () => {
    try {
      const response = await axios.get('http://localhost:2341/get_decks');
      setDecks(response.data.decks);
    } catch (error) {
      console.error('Error fetching decks:', error);
    }
  };

  useEffect(() => {
    setDeckName(selectedDeck);
  }, [selectedDeck, setDeckName]);

  return (
    <Paper sx={{ padding: 2, height: '100%', boxSizing: 'border-box' }} elevation={3}>
      <Typography variant="h6" gutterBottom>
        Config
      </Typography>

      {/* Processing Mode Selection */}
      <FormControl component="fieldset" sx={{ mt: 2 }}>
        <FormLabel component="legend">Processing Mode</FormLabel>
        <RadioGroup
          aria-label="processing-mode"
          value={processingMode || 'manual'} // Default to 'manual' if no value is set
          onChange={handleProcessingModeChange}
          name="processing-mode"
        >
          <FormControlLabel value="auto" control={<Radio />} label="Automatic" />
          <FormControlLabel value="manual" control={<Radio />} label="Manual" />
        </RadioGroup>
      </FormControl>

      {/* Deck Selection */}
      <Typography variant="h6" sx={{ mt: 4 }}>
        Choose Anki Deck
      </Typography>

      {/* Manual Deck Name Input */}
      <TextField
        label="Deck Name"
        variant="outlined"
        fullWidth
        value={selectedDeck}
        onChange={handleDeckNameInput}
        sx={{ mt: 2 }}
      />

      {/* Fetch Decks Button */}
      <Button variant="contained" onClick={fetchDecks} sx={{ mt: 2, mb: 2 }}>
        Fetch Decks
      </Button>

      {/* Decks Dropdown */}
      {decks.length > 0 ? (
        <FormControl fullWidth variant="outlined">
          <Select value={selectedDeck} onChange={handleDeckChange}>
            {decks.map((deck) => (
              <MenuItem key={deck} value={deck}>
                {deck}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      ) : (
        <Typography>No decks available. Enter a deck name or fetch decks.</Typography>
      )}
    </Paper>
  );
}

export default Config;
