// src/components/ImageUpload.js

import React, { useRef, useState } from 'react';
import axios from 'axios';
import { Button, Box } from '@mui/material';
import { CustomFileInput } from './CustomFileInput';

function ImageUpload({ handleLog, deckName }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
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
  };

  const handleClear = () => {
    fileInputRef.current.clear(); // Clear the input field
    setSelectedFiles([]);
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <CustomFileInput ref={fileInputRef} onFileChange={handleFileChange} />
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

export default ImageUpload;
