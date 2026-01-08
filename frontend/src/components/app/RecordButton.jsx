import { motion } from 'framer-motion';
import { Mic, Square } from 'lucide-react';

const RecordButton = ({ isRecording, onClick }) => {
  return (
    <div className="flex flex-col items-center gap-8 py-6">
      <motion.button
        onClick={onClick}
        whileTap={{ scale: 0.96 }}
        whileHover={{ scale: 1.02 }}
        aria-label={isRecording ? "Stop recording" : "Start recording"}
        className={`
          w-28 h-28 rounded-full flex items-center justify-center
          transition-all duration-300 ease-out
          bg-neu-base dark:bg-neu-base-dark
          ${isRecording 
            ? 'shadow-neu-pressed dark:shadow-neu-pressed-dark' 
            : 'shadow-neu-convex dark:shadow-neu-convex-dark hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark'}
        `}
      >
        {isRecording ? (
          <Square className="w-8 h-8 text-slate-600 dark:text-slate-300 fill-current" />
        ) : (
          <Mic className="w-9 h-9 text-slate-500 dark:text-slate-400" />
        )}
      </motion.button>
      
      {/* Pill-shaped label */}
      <motion.span 
        className={`
          px-6 py-2.5 rounded-full text-sm font-medium tracking-wide
          bg-neu-base dark:bg-neu-base-dark
          shadow-neu-btn-sm dark:shadow-neu-btn-dark
          text-slate-500 dark:text-slate-400
        `}
        animate={{ opacity: isRecording ? [1, 0.6, 1] : 1 }}
        transition={{ duration: 1.5, repeat: isRecording ? Infinity : 0 }}
      >
        {isRecording ? 'Listening...' : 'Tap to Speak'}
      </motion.span>
    </div>
  );
};

export default RecordButton;