import React from 'react';
import TextForm from './TextForm';
import ImageUpload from './ImageUpload';

function InputSection({ inputMode, handleLog, deckName, processingMode }) {
  return (
    <div>
      {inputMode === 'text' ? (
        <TextForm
          handleLog={handleLog}
          deckName={deckName}
          processingMode={processingMode}
        />
      ) : (
        <ImageUpload
          handleLog={handleLog}
          deckName={deckName}
          processingMode={processingMode}
        />
      )}
    </div>
  );
}

export default InputSection;
