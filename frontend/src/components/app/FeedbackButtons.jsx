import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import NeumorphicCard from '../ui/NeumorphicCard';

const AVAILABLE_INTENTS = [
  "HELP", "WATER", "YES", "NO", "PAIN", 
  "EMERGENCY", "BATHROOM", "TIRED", "COLD", "HOT"
];

const FeedbackButtons = ({ 
  embeddingId, 
  predictedIntent, 
  onFeedbackSubmit, 
  isSubmitting = false 
}) => {
  const [showCorrection, setShowCorrection] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(null); // 'yes' | 'no' | null

  const handleYes = () => {
    setFeedbackGiven('yes');
    onFeedbackSubmit({
      embeddingId,
      predictedIntent,
      isCorrect: true,
      correctIntent: null
    });
  };

  const handleNo = () => {
    setFeedbackGiven('no');
    setShowCorrection(true);
  };

  const handleCorrection = (correctIntent) => {
    onFeedbackSubmit({
      embeddingId,
      predictedIntent,
      isCorrect: false,
      correctIntent
    });
    setShowCorrection(false);
  };

  // Already gave feedback
  if (feedbackGiven === 'yes') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="mt-6 text-center"
      >
        <div className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-neu-base dark:bg-neu-base-dark shadow-neu-pressed dark:shadow-neu-pressed-dark text-slate-500 dark:text-slate-400 font-medium text-sm">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Thanks! System learned this pattern.
        </div>
      </motion.div>
    );
  }

  return (
    <div className="mt-6">
      <AnimatePresence mode="wait">
        {!showCorrection ? (
          <motion.div
            key="feedback-buttons"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="flex flex-col items-center gap-4"
          >
            <p className="text-neu-text dark:text-neu-text-dark text-sm font-medium">
              Is this correct?
            </p>
            <div className="flex gap-4">
              <motion.button
                onClick={handleYes}
                disabled={isSubmitting}
                whileTap={{ scale: 0.96 }}
                className="flex items-center gap-2 px-8 py-4 bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark rounded-full hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all font-medium disabled:opacity-50"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                YES
              </motion.button>
              <motion.button
                onClick={handleNo}
                disabled={isSubmitting}
                whileTap={{ scale: 0.96 }}
                className="flex items-center gap-2 px-8 py-4 bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark rounded-full hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all font-medium disabled:opacity-50"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                NO
              </motion.button>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="correction-panel"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="w-full"
          >
            <NeumorphicCard className="w-full max-w-2xl mx-auto">
              <p className="text-neu-text dark:text-neu-text-dark text-center mb-4 font-medium text-sm">
                What did you actually mean?
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                {AVAILABLE_INTENTS.map((intent) => (
                  <motion.button
                    key={intent}
                    onClick={() => handleCorrection(intent)}
                    disabled={isSubmitting || intent === predictedIntent}
                    whileTap={{ scale: 0.96 }}
                    className={`
                      py-3 px-3 text-sm font-medium rounded-full transition-all
                      ${intent === predictedIntent 
                        ? 'bg-neu-base dark:bg-neu-base-dark shadow-neu-pressed dark:shadow-neu-pressed-dark text-slate-400 dark:text-slate-500 cursor-not-allowed' 
                        : 'bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn-sm dark:shadow-neu-btn-dark hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark'
                      }
                    `}
                  >
                    {intent}
                  </motion.button>
                ))}
              </div>
              <button
                onClick={() => setShowCorrection(false)}
                className="mt-4 w-full text-center text-sm text-neu-text/70 dark:text-neu-text-dark/70 hover:text-neu-text dark:hover:text-neu-text-dark"
              >
                ← Go back
              </button>
            </NeumorphicCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default FeedbackButtons;
