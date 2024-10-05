// src/components/CustomFileInput.js

import React, { useRef, useState, forwardRef, useImperativeHandle } from 'react';
import { Box, Typography } from '@mui/material';
import InsertPhotoIcon from '@mui/icons-material/InsertPhoto';

export const CustomFileInput = forwardRef(({ accept = 'image/*', onFileChange }, ref) => {
  const [imageFiles, setImageFiles] = useState([]);
  const fileInputRef = useRef(null);

  useImperativeHandle(ref, () => ({
    clear: () => {
      fileInputRef.current.value = '';
      setImageFiles([]);
    },
  }));

  const handleImageUploadClick = () => {
    fileInputRef.current?.click();
  };

  const updateImage = (event) => {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
      setImageFiles(files);
      onFileChange(files);
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  const handleFileDrop = (event) => {
    event.preventDefault();
    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) {
      setImageFiles(files);
      onFileChange(files);
    }
  };

  return (
    <Box
      sx={{
        border: '2px dashed #777',
        borderRadius: 2,
        p: 2,
        textAlign: 'center',
        cursor: 'pointer',
        color: '#aaa',
      }}
      onDragOver={handleDragOver}
      onDrop={handleFileDrop}
      onClick={handleImageUploadClick}
    >
      {imageFiles.length > 0 ? (
        imageFiles.map((file, index) => (
          <img
            key={index}
            src={URL.createObjectURL(file)}
            alt="Uploaded"
            style={{ maxWidth: '100%', maxHeight: '150px', margin: '5px' }}
          />
        ))
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <InsertPhotoIcon sx={{ fontSize: 48 }} />
          <Typography>Drag and drop images here, or click to select them</Typography>
        </Box>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={updateImage}
        multiple
      />
    </Box>
  );
});
