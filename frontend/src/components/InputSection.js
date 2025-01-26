// src/components/InputSection.js

import React from 'react';
import UnifiedInput from './UnifiedInput';

function InputSection({ handleLog, deckName, processingMode }) {
  return (
    <div>
      <UnifiedInput
        handleLog={handleLog}
        deckName={deckName}
        processingMode={processingMode}
      />
    </div>
  );
}

export default InputSection;
