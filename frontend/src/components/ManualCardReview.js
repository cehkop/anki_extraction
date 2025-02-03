import React, { useState, useEffect } from 'react';
import { Box, Checkbox, Button, TextField } from '@mui/material';

function ManualCardReview({ pairs, onSubmit, onCancel }) {
  const [reviewCards, setReviewCards] = useState([]);

  useEffect(() => {
    // Initialize with 'selected: true' to ensure all cards are selected by default
    const initialized = pairs.map((card) => ({ ...card, selected: true }));
    setReviewCards(initialized);
    console.log('Initialized reviewCards:', initialized); // Debugging statement
  }, [pairs]);

  const handleCheckboxChange = (index) => {
    setReviewCards((prev) =>
      prev.map((card, i) =>
        i === index ? { ...card, selected: !card.selected } : card
      )
    );
    console.log(`[ManualCardReview] Toggled selection for card at index ${index}`);
  };

  const handleValueChange = (index, field, value) => {
    setReviewCards((prev) =>
      prev.map((card, i) =>
        i === index ? { ...card, [field]: value } : card
      )
    );
    console.log(`[ManualCardReview] Updated card at index ${index}: ${field} = ${value}`);
  };

  const handleSubmit = () => {
    const selectedCards = reviewCards.filter((card) => card.selected);
    console.log(`[ManualCardReview] Submitting selected cards:`, selectedCards);
    onSubmit(selectedCards);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      {/* Scrollable Cards Box */}
      <Box
        sx={{
          width: '100%',
          maxWidth: '600px',
          flexGrow: 1,
          maxHeight: '50vh',
          border: '1px solid #444',
          borderRadius: 2,
          p: 2,
          backgroundColor: '#2c2c2c',
          boxShadow: '0px 4px 12px rgba(0, 0, 0, 0.3)',
          overflowY: 'auto',
        }}
      >
        {reviewCards.map((card, index) => (
          <Box
            key={index}
            sx={{
              border: '1px solid #ccc',
              borderRadius: 1,
              p: 1,
              mb: 1,
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              backgroundColor: '#1e1e1e',
              color: '#fff',
            }}
          >
            {/* Editable Fields for Front and Back */}
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 0.8 }}>
              <TextField
                label="Front"
                variant="outlined"
                fullWidth
                multiline
                minRows={1} // Minimum height
                maxRows={5} // Maximum height
                value={card.Front}
                onChange={(e) => handleValueChange(index, 'Front', e.target.value)}
                margin='dense'
                size="small"
                sx={{
                  backgroundColor: '#2c2c2c',
                  '& .MuiOutlinedInput-root': {
                    // height: '35px', // Set a custom height for the TextField
                    '& textarea': {
                      color: '#fff',
                      padding: '0px',
                      lineHeight: 1.2,
                    },
                    '& fieldset': {
                      borderColor: '#444',
                    },
                    '&:hover fieldset': {
                      borderColor: '#888',
                    },
                  },
                }}
              />
              <TextField
                label="Back"
                variant="outlined"
                fullWidth
                multiline
                minRows={1} // Minimum height
                maxRows={3} // Maximum height
                value={card.Back}
                onChange={(e) => handleValueChange(index, 'Back', e.target.value)}
                margin='dense'
                size="small"
                sx={{
                  backgroundColor: '#2c2c2c',
                  '& .MuiOutlinedInput-root': {
                    '& textarea': {
                      color: '#fff',
                      padding: '0px',
                      lineHeight: 1.2,
                    },
                    '& fieldset': {
                      borderColor: '#444',
                    },
                    '&:hover fieldset': {
                      borderColor: '#888',
                    },
                  },
                }}
              />
            </Box>
            {/* Checkbox aligned to the right */}
            <Box sx={{ display: 'flex', alignItems: 'center', ml: 1 }}>
              <Checkbox
                checked={card.selected}
                onChange={() => handleCheckboxChange(index)}
                sx={{ color: '#fff' }}
              />
            </Box>
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
