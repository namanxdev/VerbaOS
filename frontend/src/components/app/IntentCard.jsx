import { motion } from 'framer-motion';
import NeumorphicCard from '../ui/NeumorphicCard';

const IntentCard = ({ intent, confidence, transcription }) => {
  return (
    <NeumorphicCard className="w-full max-w-md mx-auto text-center">
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4 }}
      >
        <div className="text-neu-text dark:text-neu-text-dark text-xs uppercase tracking-widest mb-3 font-medium">Detected Intent</div>
        <div className="text-3xl md:text-4xl font-bold text-slate-600 dark:text-slate-200 mb-4 capitalize">
          {intent || "Unknown"}
        </div>
        {transcription && (
          <div className="text-sm text-neu-text/70 dark:text-neu-text-dark/70 italic mb-5 max-w-[85%] mx-auto">
             "{transcription}"
          </div>
        )}
        
        {confidence && (
           <div className="inline-block px-5 py-2 rounded-full bg-neu-base dark:bg-neu-base-dark shadow-neu-pressed dark:shadow-neu-pressed-dark text-xs font-medium font-mono text-neu-text dark:text-neu-text-dark">
             {(confidence * 100).toFixed(0)}% confidence
           </div>
        )}
      </motion.div>
    </NeumorphicCard>
  );
};

export default IntentCard;
