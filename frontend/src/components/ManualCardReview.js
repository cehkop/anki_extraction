// src/components/ManualCardReview.js

import React, { useState, useEffect } from 'react';
import { Box, Typography, Checkbox, Button, FormControlLabel } from '@mui/material';

function ManualCardReview({ pairs, onSubmit, onCancel }) {
  const [selectedPairs, setSelectedPairs] = useState([]);

  useEffect(() => {
    // Initialize selectedPairs with the pairs from props, adding 'selected: true'
    const initializedPairs = pairs.map((pair) => ({ ...pair, selected: true }));
    setSelectedPairs(initializedPairs);
    console.log('Initialized selectedPairs:', initializedPairs); // Debugging statement
  }, [pairs]);

  const handleCheckboxChange = (index) => {
    setSelectedPairs((prev) =>
      prev.map((pair, i) =>
        i === index ? { ...pair, selected: !pair.selected } : pair
      )
    );
  };

  const handleSubmit = () => {
    const pairsToAdd = selectedPairs.filter((pair) => pair.selected);
    onSubmit(pairsToAdd);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      <Typography variant="h6" gutterBottom sx={{ color: '#fff' }}>
        Review Cards
      </Typography>

      <Box
        sx={{
          flex: 1, // Takes up remaining space
          border: '1px solid #444',
          borderRadius: 2,
          p: 2,
          backgroundColor: '#2c2c2c',
          overflowY: 'auto', // Enable scrolling for overflow
          mt: 1,
        }}
      >
        {selectedPairs.map((pair, index) => (
          <Box
            key={index}
            sx={{
              border: '1px solid #ccc',
              borderRadius: 1,
              p: 0.5, // Reduced padding for smaller gap
              mb: 1, // Smaller margin between cards
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: '#1e1e1e',
              color: '#fff',
              fontSize: '0.75rem', // Reduced text size for compactness
            }}
          >
            <Box sx={{ flex: 1 }}>
              <Typography variant="body2" sx={{ color: '#fff', fontSize: '0.75rem' }}>
                <strong>Front:</strong> {pair.Front}
              </Typography>
              <Typography variant="body2" sx={{ color: '#fff', fontSize: '0.75rem' }}>
                <strong>Back:</strong> {pair.Back}
              </Typography>
            </Box>
            <FormControlLabel
              control={
                <Checkbox
                  checked={pair.selected}
                  onChange={() => handleCheckboxChange(index)}
                />
              }
              label="Add this card"
              labelPlacement="start"
              sx={{ ml: 1, color: '#fff', fontSize: '0.75rem' }}
            />
          </Box>
        ))}
      </Box>

      <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
        <Button variant="contained" onClick={handleSubmit}>
          Submit
        </Button>
        <Button variant="outlined" color="error" onClick={onCancel}>
          Cancel
        </Button>
      </Box>
    </Box>
  );
}

export default ManualCardReview;
