// src/components/InputSection.js

import React from 'react';
import UnifiedInput from './UnifiedInput';
import RedCardsReview from './RedCardsReview';

function InputSection({ handleLog, deckName, processingMode }) {
  // If the user picks "red" in Config, show the RedCardsReview
  if (processingMode === 'red_cards') {
    return <RedCardsReview deckName={deckName} handleLog={handleLog} />;
  }

  // Otherwise fall back to your original input (text or images)
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
