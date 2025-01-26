import React, { useState, useEffect } from 'react';
import { Box, Checkbox, Button, Typography, FormControlLabel } from '@mui/material';

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
    console.log(`[ManualCardReview] Toggled selection for card at index ${index}`);
  };

  const handleSubmit = () => {
    const pairsToAdd = selectedPairs.filter((pair) => pair.selected);
    console.log(`[ManualCardReview] Submitting selected pairs:`, pairsToAdd);
    onSubmit(pairsToAdd);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%', // Take the full height of the parent container
        justifyContent: 'space-between', // Ensure buttons remain visible
        alignItems: 'center',
      }}
    >
      {/* Scrollable Cards Box */}
      <Box
        sx={{
          width: '100%',
          maxWidth: '600px',
          flexGrow: 1,
          maxHeight: '50vh', // Sets a maximum height for the scrolling box
          border: '1px solid #444',
          borderRadius: 2,
          p: 2,
          backgroundColor: '#2c2c2c',
          boxShadow: '0px 4px 12px rgba(0, 0, 0, 0.3)',
          overflowY: 'auto', // Enables scrolling if content exceeds height
        }}
      >
        {selectedPairs.map((pair, index) => (
          <Box
            key={index}
            sx={{
              border: '1px solid #ccc',
              borderRadius: 1,
              p: 1,
              mb: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: '#1e1e1e',
              color: '#fff',
              fontSize: '0.75rem',
            }}
          >
            {/* Card Content */}
            <Box sx={{ flex: 1 }}>
              <Typography variant="body2" sx={{ color: '#fff', fontSize: '0.75rem' }}>
                <strong>Front:</strong> {pair.Front}
              </Typography>
              <Typography variant="body2" sx={{ color: '#fff', fontSize: '0.75rem' }}>
                <strong>Back:</strong> {pair.Back}
              </Typography>
            </Box>
            {/* Checkbox */}
            <FormControlLabel
              control={
                <Checkbox
                  checked={pair.selected}
                  onChange={() => handleCheckboxChange(index)}
                  sx={{ color: '#fff' }}
                />
              }
              label=""
              sx={{ ml: 1 }}
            />
          </Box>
        ))}
      </Box>

      {/* Submit and Cancel Buttons */}
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
