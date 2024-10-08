// src/components/CustomFileInput.js

import React, {
  useRef,
  useState,
  forwardRef,
  useImperativeHandle,
  useEffect,
} from 'react';
import { Box, Typography } from '@mui/material';
import InsertPhotoIcon from '@mui/icons-material/InsertPhoto';

export const CustomFileInput = forwardRef(
  ({ accept = 'image/*', onFileChange }, ref) => {
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
        setImageFiles((prevFiles) => {
          const newFiles = [...prevFiles, ...files];
          onFileChange(newFiles);
          return newFiles;
        });
      }
    };

    const handleDragOver = (event) => {
      event.preventDefault();
    };

    const handleFileDrop = (event) => {
      event.preventDefault();
      const files = Array.from(event.dataTransfer.files);
      if (files.length > 0) {
        setImageFiles((prevFiles) => {
          const newFiles = [...prevFiles, ...files];
          onFileChange(newFiles);
          return newFiles;
        });
      }
    };

    // Handle paste events globally
    const handlePaste = (event) => {
      const clipboardItems = event.clipboardData.items;
      const imageItems = [];

      for (let i = 0; i < clipboardItems.length; i++) {
        const item = clipboardItems[i];
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile();
          imageItems.push(file);
        }
      }

      if (imageItems.length > 0) {
        setImageFiles((prevFiles) => {
          const newFiles = [...prevFiles, ...imageItems];
          onFileChange(newFiles);
          return newFiles;
        });
        event.preventDefault();
      }
    };

    useEffect(() => {
      window.addEventListener('paste', handlePaste);
      return () => {
        window.removeEventListener('paste', handlePaste);
      };
    }, []);

    return (
      <Box
        sx={{
          border: '2px dashed #777',
          borderRadius: 2,
          p: 2,
          textAlign: 'center',
          cursor: 'pointer',
          color: '#aaa',
          position: 'relative',
        }}
        onDragOver={handleDragOver}
        onDrop={handleFileDrop}
        onClick={handleImageUploadClick}
      >
        {imageFiles.length > 0 ? (
          <Box
            sx={{
              maxHeight: '200px',
              overflowY: 'auto',
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'center',
              gap: 1,
            }}
          >
            {imageFiles.map((file, index) => (
              <Box
                key={index}
                sx={{
                  width: '100px',
                  height: '100px',
                  position: 'relative',
                }}
              >
                <img
                  src={URL.createObjectURL(file)}
                  alt="Uploaded"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    borderRadius: '4px',
                  }}
                />
              </Box>
            ))}
          </Box>
        ) : (
          <Box
            sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}
          >
            <InsertPhotoIcon sx={{ fontSize: 48 }} />
            <Typography>
              Drag and drop images here, click to select them, or paste from clipboard
              (Ctrl+V)
            </Typography>
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
  }
);
