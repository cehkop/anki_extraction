import React, { useState } from 'react';
import axios from 'axios';
import { Box, Typography, Checkbox, Button, Paper } from '@mui/material';

function RedCardsReview({ deckName, handleLog }) {
  const [redCards, setRedCards] = useState([]);
  const [cardsLoaded, setCardsLoaded] = useState(false);

  // Called when user clicks "Get Cards"
  const fetchRedCards = async () => {
    if (!deckName) {
      handleLog('No deck name provided.');
      return;
    }

    try {
      // Suppose your endpoint is POST /update_cards_red_manual
      // and we pass { deck_name } in the body
      const res = await axios.get('http://localhost:2341/update_cards_red_manual_get', {
        params: {
          deck_name: deckName
        }
      });
      
      console.log('Fetched red cards for manual update:', res.data); // It's an array
      
      const withSelections = res.data.map((item) => {
        const newSuggestions = item.New.map(sug => ({ ...sug, selected: true }));
        return { ...item, New: newSuggestions };
      });
      
      setRedCards(withSelections);
      // The response might be { cards: [...] }
      console.log('Fetched red cards for manual update:', res.data);
      handleLog(`Fetched red cards: ${JSON.stringify(res.data)}`);

      setCardsLoaded(true);
    } catch (error) {
      console.error('Error fetching red cards manually:', error);
      handleLog('Error fetching red cards manually.');
    }
  };

  const handleCheckboxChange = (cardIndex, sugIndex) => {
    setRedCards((prev) =>
      prev.map((card, i) => {
        if (i === cardIndex) {
          // toggle the selected property of suggestion sugIndex
          const updatedNew = card.New.map((sug, j) =>
            j === sugIndex ? { ...sug, selected: !sug.selected } : sug
          );
          return { ...card, New: updatedNew };
        }
        return card;
      })
    );
  };


  const handleClear = () => {
  };

  const handleSubmit = async () => {
    // Gather user’s final choices
    const finalData = redCards.map((card) => ({
      noteId: card.noteId,
      oldFront: card.Front,
      oldBack: card.Back,
      newSuggestions: card.New.map((sug) => ({
        Front: sug.Front,
        Back: sug.Back,
        selected: sug.selected,
      })),
    }));

    console.log('Submitting final red cards data:', finalData);

    try {
      // POST to "update_cards_red_manual_adding" or whichever route you have
      const resp = await axios.post('http://localhost:2341/update_cards_red_manual_adding', {
        deckName,
        data: finalData
      });
      handleLog(`update_cards_red_manual_adding response: ${JSON.stringify(resp.data)}`);
    } catch (error) {
      console.error('Error submitting manual red cards update:', error);
      handleLog('Error submitting manual red cards update.');
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      {/* Button to fetch red cards */}
      <Box sx={{ mb: 2 }}>
        <Button variant="contained" onClick={fetchRedCards}>
          Get Cards
        </Button>
      </Box>

      {/* Show cards only after they've been fetched */}
      {!cardsLoaded ? (
        <Typography variant="body2" sx={{ color: '#ccc' }}>
          Click "Get Cards" to load red cards for manual review.
        </Typography>
      ) : (
        <Box
          sx={{
            width: '100%',
            maxWidth: '800px',
            maxHeight: '70vh',
            overflowY: 'auto',
            border: '1px solid #444',
            borderRadius: 2,
            p: 2,
            backgroundColor: '#2c2c2c',
          }}
        >
          {redCards.map((card, cardIndex) => (
            <Paper
              key={cardIndex}
              sx={{
                mb: 2,
                p: 2,
                backgroundColor: '#333',
                color: '#fff',
                display: 'flex',
                gap: 2
              }}
            >
              {/* Left side: old card */}
              <Box
                sx={{
                  flex: '1 1 40%',
                  borderRight: '1px solid #666',
                  pr: 2
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                  Old Card
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  <strong>Front:</strong> {card.Front}
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  <strong>Back:</strong> {card.Back}
                </Typography>
              </Box>

              {/* Right side: new suggestions */}
              <Box sx={{ flex: '1 1 60%', display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                  New Suggestions
                </Typography>
                {card.New.map((suggestion, sugIndex) => (
                  <Box
                    key={sugIndex}
                    sx={{
                      border: '1px solid #555',
                      p: 1,
                      display: 'flex',
                      flexDirection: 'row',
                      gap: 2
                    }}
                  >
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2">
                        <strong>Front:</strong> {suggestion.Front}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Back:</strong> {suggestion.Back}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Checkbox
                        checked={suggestion.selected}
                        onChange={() => handleCheckboxChange(cardIndex, sugIndex)}
                        sx={{ color: '#fff' }}
                      />
                    </Box>
                  </Box>
                ))}
              </Box>
            </Paper>
          ))}
        </Box>
      )}

      {/* Submit only visible if we have cards */}
      {cardsLoaded && (
        <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
          <Button variant="contained" onClick={handleSubmit}>
            Submit
          </Button>
          <Button variant="outlined" color="error" onClick={handleClear}>
            Cancel
          </Button>
        </Box>
      )}
    </Box>
  );
}

export default RedCardsReview;
