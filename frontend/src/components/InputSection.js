// src/components/InputSection.js

import React from 'react';
import TextForm from './TextForm';
import ImageUpload from './ImageUpload';

function InputSection({ inputMode, handleLog, deckName }) {
  return (
    <div>
      {inputMode === 'text' ? (
        <TextForm handleLog={handleLog} deckName={deckName} />
      ) : (
        <ImageUpload handleLog={handleLog} deckName={deckName} />
      )}
    </div>
  );
}

export default InputSection;
