import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { registerVisitor } from '../../services/api';

const VisitorCounter = () => {
  const [count, setCount] = useState(null);
  const [isNew, setIsNew] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const trackVisitor = async () => {
      try {
        // Check if already registered in this session
        const sessionKey = 'visitor_registered';
        const alreadyRegistered = sessionStorage.getItem(sessionKey);
        
        const response = await registerVisitor();
        setCount(response.count);
        setIsNew(response.is_new_visitor);
        
        if (!alreadyRegistered) {
          sessionStorage.setItem(sessionKey, 'true');
        }
      } catch (error) {
        console.error('Failed to track visitor:', error);
        setCount('--');
      } finally {
        setLoading(false);
      }
    };

    trackVisitor();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.5 }}
      className="fixed bottom-4 left-4 z-50"
    >
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-full bg-neu-base dark:bg-neu-base-dark shadow-neu-btn dark:shadow-neu-btn-dark">
        {/* User icon */}
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-neu-base dark:bg-neu-base-dark shadow-neu-pressed dark:shadow-neu-pressed-dark">
          <svg 
            className="w-4 h-4 text-slate-500 dark:text-slate-400" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={1.5} 
              d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" 
            />
          </svg>
        </div>
        
        {/* Counter */}
        <div className="flex flex-col">
          <span className="text-[10px] text-neu-text/60 dark:text-neu-text-dark/60 uppercase tracking-wider font-medium">
            Visitors
          </span>
          <div className="flex items-center gap-1">
            {loading ? (
              <span className="text-base font-semibold text-slate-600 dark:text-slate-300 animate-pulse">
                ...
              </span>
            ) : (
              <motion.span
                key={count}
                initial={{ scale: 1.1 }}
                animate={{ scale: 1 }}
                className="text-base font-semibold text-slate-600 dark:text-slate-300 font-mono"
              >
                {count?.toLocaleString?.() || count}
              </motion.span>
            )}
            {isNew && !loading && (
              <motion.span
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-[10px] px-1.5 py-0.5 rounded-full bg-neu-base dark:bg-neu-base-dark shadow-neu-pressed dark:shadow-neu-pressed-dark text-slate-500 dark:text-slate-400 font-medium"
              >
                +1
              </motion.span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default VisitorCounter;
