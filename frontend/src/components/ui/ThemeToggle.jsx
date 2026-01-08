import { useState, useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';
import { motion } from 'framer-motion';

const ThemeToggle = () => {
  const [theme, setTheme] = useState(
    localStorage.getItem('theme') || 'light'
  );

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <motion.button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      whileTap={{ scale: 0.95 }}
      className={`
        relative w-11 h-11 rounded-full flex items-center justify-center
        transition-all duration-200
        bg-neu-base dark:bg-neu-base-dark
        shadow-neu-btn dark:shadow-neu-btn-dark
        hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark
        active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark
        text-slate-500 dark:text-slate-400
      `}
      aria-label="Toggle Theme"
    >
      {theme === 'dark' ? (
        <Sun className="w-5 h-5" />
      ) : (
        <Moon className="w-5 h-5" />
      )}
    </motion.button>
  );
};

export default ThemeToggle;
