import React, { useRef, useState } from 'react';
import axios from 'axios';
import { Button, Box } from '@mui/material';
import { CustomFileInput } from './CustomFileInput';
import ManualCardReview from './ManualCardReview';

function ImageUpload({ handleLog, deckName, processingMode }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [extractedPairs, setExtractedPairs] = useState(null);
  const fileInputRef = useRef();

  const handleFileChange = (files) => {
    setSelectedFiles(files);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (selectedFiles.length === 0) {
      alert('Please select at least one image.');
      return;
    }

    if (processingMode === 'auto') {
      // Automatic Processing
      const formData = new FormData();
      selectedFiles.forEach((file) => {
        formData.append('files', file);
      });
      formData.append('deckName', deckName); // Include deckName in the form data

      try {
        const res = await axios.post('http://localhost:2341/process_images', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        fileInputRef.current.clear(); // Clear the input field
        setSelectedFiles([]);

        handleLog(`Image Response: ${JSON.stringify(res.data, null, 2)}`);
      } catch (error) {
        console.error(error);
        handleLog('Error processing images.');
      }
    } else {
      // Manual Processing
      const formData = new FormData();
      selectedFiles.forEach((file) => {
        formData.append('files', file);
      });

      try {
        const res = await axios.post('http://localhost:2341/extract_images', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        setExtractedPairs(res.data.pairs);
      } catch (error) {
        console.error(error);
        handleLog('Error extracting pairs from images.');
      }
    }
  };

  const handleManualSubmit = async (selectedPairs) => {
    try {
      const res = await axios.post('http://localhost:2341/add_cards', {
        deckName,
        pairs: selectedPairs,
      });
      handleLog(`Added Cards: ${JSON.stringify(res.data, null, 2)}`);
      setExtractedPairs(null);
      setSelectedFiles([]);
      fileInputRef.current.clear();
    } catch (error) {
      console.error(error);
      handleLog('Error adding cards.');
    }
  };

  const handleClear = () => {
    fileInputRef.current.clear(); // Clear the input field
    setSelectedFiles([]);
    setExtractedPairs(null);
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      {!extractedPairs ? (
        <>
          <CustomFileInput ref={fileInputRef} onFileChange={handleFileChange} />
          <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
            <Button variant="contained" type="submit">
              Submit
            </Button>
            <Button variant="outlined" color="error" onClick={handleClear}>
              Clear
            </Button>
          </Box>
        </>
      ) : (
        <ManualCardReview
          pairs={extractedPairs}
          onSubmit={handleManualSubmit}
          onCancel={handleClear}
        />
      )}
    </Box>
  );
}

export default ImageUpload;
