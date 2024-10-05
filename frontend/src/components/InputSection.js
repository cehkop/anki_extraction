// src/components/InputSection.js

import React from 'react';
import { Paper, Typography } from '@mui/material';
import TextForm from './TextForm';
import ImageUpload from './ImageUpload';

function InputSection({ inputMode, handleLog }) {
  return (
    <Paper sx={{ padding: 2, height: '100%', boxSizing: 'border-box', overflow: 'auto' }} elevation={3}>
      <Typography variant="h6" gutterBottom>
        Input
      </Typography>
      {inputMode === 'text' ? (
        <TextForm handleLog={handleLog} />
      ) : (
        <ImageUpload handleLog={handleLog} />
      )}
    </Paper>
  );
}

export default InputSection;
