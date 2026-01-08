import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { registerUser, getUser } from '../services/api';
import NeumorphicCard from '../components/ui/NeumorphicCard';
import { Button } from '../components/ui/button';
import ThemeToggle from '../components/ui/ThemeToggle';
import VisitorCounter from '../components/app/VisitorCounter';

export default function RoleSelection() {
  const navigate = useNavigate();
  const [showRegister, setShowRegister] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);
  const [name, setName] = useState('');
  const [existingId, setExistingId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('select'); // 'select', 'new', 'existing'

  // Check if user already exists in localStorage
  const checkExistingSession = () => {
    const savedUser = localStorage.getItem('speechIntentUser');
    if (savedUser) {
      const user = JSON.parse(savedUser);
      if (user.role === 'patient') {
        navigate('/patient');
      } else {
        navigate('/caretaker');
      }
      return true;
    }
    return false;
  };

  const handleRoleSelect = async (role) => {
    // Show registration/login options for both patient and caretaker
    setSelectedRole(role);
    setMode('select');
    setError('');
  };

  const handleNewUser = async () => {
    if (!name.trim()) {
      setError('Please enter your name');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const user = await registerUser(name.trim(), selectedRole);
      
      // Save to localStorage
      localStorage.setItem('speechIntentUser', JSON.stringify(user));
      
      // Navigate to appropriate dashboard
      if (selectedRole === 'patient') {
        navigate('/patient');
      } else {
        navigate('/caretaker');
      }
    } catch (err) {
      setError('Failed to register. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExistingUser = async () => {
    if (!existingId.trim()) {
      setError('Please enter your ID');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const user = await getUser(existingId.trim());
      
      // Verify role matches
      if (user.role !== selectedRole) {
        setError(`This ID belongs to a ${user.role}, not a ${selectedRole}`);
        setLoading(false);
        return;
      }
      
      // Save to localStorage
      localStorage.setItem('speechIntentUser', JSON.stringify(user));
      
      // Navigate to appropriate dashboard
      if (selectedRole === 'patient') {
        navigate('/patient');
      } else {
        navigate('/caretaker');
      }
    } catch (err) {
      setError('User not found. Please check your ID.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // For quick access without login (patient only)
  const handleQuickStart = async () => {
    setLoading(true);
    try {
      const user = await registerUser('Guest Patient', 'patient');
      localStorage.setItem('speechIntentUser', JSON.stringify(user));
      navigate('/patient');
    } catch (err) {
      const localUser = {
        id: 'local_' + Date.now(),
        name: 'Guest',
        role: 'patient'
      };
      localStorage.setItem('speechIntentUser', JSON.stringify(localUser));
      navigate('/patient');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neu-base dark:bg-neu-base-dark flex flex-col items-center justify-center p-6 transition-colors duration-500">
      
      {/* Theme Toggle */}
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-700 dark:text-slate-100 mb-4">
          VerbaOS
        </h1>
        <p className="text-neu-text dark:text-neu-text-dark text-lg">
          Assistive communication for patients and caretakers
        </p>
      </motion.div>

      {/* Role Selection */}
      {!selectedRole ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col md:flex-row gap-8"
        >
          {/* Patient Card */}
          <motion.button
            onClick={() => handleRoleSelect('patient')}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.98 }}
            disabled={loading}
            className="w-64 bg-neu-base dark:bg-neu-base-dark rounded-3xl shadow-neu-flat dark:shadow-neu-flat-dark p-8 hover:shadow-neu-convex dark:hover:shadow-neu-convex-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all duration-200 disabled:opacity-70"
          >
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-neu-base dark:bg-neu-base-dark shadow-neu-pressed dark:shadow-neu-pressed-dark flex items-center justify-center mb-5">
                <svg className="w-8 h-8 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-slate-600 dark:text-slate-200 mb-2">
                I'm a Patient
              </h2>
              <p className="text-neu-text dark:text-neu-text-dark text-center text-sm">
                {loading ? 'Loading...' : 'Record voice commands'}
              </p>
            </div>
          </motion.button>

          {/* Caretaker Card */}
          <motion.button
            onClick={() => handleRoleSelect('caretaker')}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.98 }}
            className="w-64 bg-neu-base dark:bg-neu-base-dark rounded-3xl shadow-neu-flat dark:shadow-neu-flat-dark p-8 hover:shadow-neu-convex dark:hover:shadow-neu-convex-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all duration-200"
          >
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 rounded-full bg-neu-base dark:bg-neu-base-dark shadow-neu-pressed dark:shadow-neu-pressed-dark flex items-center justify-center mb-5">
                <svg className="w-8 h-8 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-slate-600 dark:text-slate-200 mb-2">
                I'm a Caretaker
              </h2>
              <p className="text-neu-text dark:text-neu-text-dark text-center text-sm">
                Receive notifications
              </p>
            </div>
          </motion.button>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-md"
        >
          <NeumorphicCard>
            <div className="py-4">
              {/* Back button */}
              <button
                onClick={() => {
                  setSelectedRole(null);
                  setMode('select');
                  setError('');
                }}
                className="text-neu-text dark:text-neu-text-dark hover:text-blue-600 dark:hover:text-blue-400 mb-4 flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </button>

              <h2 className="text-xl font-semibold text-slate-600 dark:text-slate-200 mb-6 text-center capitalize">
                {selectedRole} Login
              </h2>

              {mode === 'select' && (
                <div className="flex flex-col gap-4">
                  <motion.button
                    onClick={() => setMode('new')}
                    whileTap={{ scale: 0.98 }}
                    className="w-full py-4 text-base font-medium bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark rounded-full hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all"
                  >
                    I'm New Here
                  </motion.button>
                  <motion.button
                    onClick={() => setMode('existing')}
                    whileTap={{ scale: 0.98 }}
                    className="w-full py-4 text-base font-medium bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark rounded-full hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all"
                  >
                    I Have an Account
                  </motion.button>
                  
                  {/* Quick Start option for patients only */}
                  {selectedRole === 'patient' && (
                    <>
                      <div className="flex items-center gap-3 my-2">
                        <div className="flex-1 h-px bg-slate-300 dark:bg-slate-600"></div>
                        <span className="text-xs text-neu-text dark:text-neu-text-dark">or</span>
                        <div className="flex-1 h-px bg-slate-300 dark:bg-slate-600"></div>
                      </div>
                      <motion.button
                        onClick={handleQuickStart}
                        disabled={loading}
                        whileTap={{ scale: 0.98 }}
                        className="w-full py-4 text-base font-medium bg-neu-base dark:bg-neu-base-dark text-slate-500 dark:text-slate-400 shadow-neu-btn-sm dark:shadow-neu-btn-dark rounded-full hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all disabled:opacity-50"
                      >
                        {loading ? 'Starting...' : 'Quick Start as Guest'}
                      </motion.button>
                    </>
                  )}
                </div>
              )}

              {mode === 'new' && (
                <div className="flex flex-col gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neu-text dark:text-neu-text-dark mb-2">
                      Your Name
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Enter your name"
                      className="w-full px-5 py-3.5 rounded-full bg-neu-base dark:bg-neu-base-dark shadow-neu-pressed dark:shadow-neu-pressed-dark text-slate-600 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none transition-all"
                    />
                  </div>
                  
                  {error && (
                    <p className="text-red-500 text-sm text-center">{error}</p>
                  )}

                  <motion.button
                    onClick={handleNewUser}
                    disabled={loading}
                    whileTap={{ scale: 0.98 }}
                    className="w-full py-4 text-base font-medium bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark rounded-full hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all disabled:opacity-50"
                  >
                    {loading ? 'Creating...' : 'Get Started'}
                  </motion.button>

                  <button
                    onClick={() => setMode('select')}
                    className="text-sm text-neu-text dark:text-neu-text-dark hover:underline"
                  >
                    Back to options
                  </button>
                </div>
              )}

              {mode === 'existing' && (
                <div className="flex flex-col gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neu-text dark:text-neu-text-dark mb-2">
                      Your User ID
                    </label>
                    <input
                      type="text"
                      value={existingId}
                      onChange={(e) => setExistingId(e.target.value)}
                      placeholder="Enter your ID (e.g., a1b2c3d4)"
                      className="w-full px-5 py-3.5 rounded-full bg-neu-base dark:bg-neu-base-dark shadow-neu-pressed dark:shadow-neu-pressed-dark text-slate-600 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none font-mono transition-all"
                    />
                  </div>
                  
                  {error && (
                    <p className="text-red-500 text-sm text-center">{error}</p>
                  )}

                  <motion.button
                    onClick={handleExistingUser}
                    disabled={loading}
                    whileTap={{ scale: 0.98 }}
                    className="w-full py-4 text-base font-medium bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark rounded-full hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all disabled:opacity-50"
                  >
                    {loading ? 'Logging in...' : 'Continue'}
                  </motion.button>

                  <button
                    onClick={() => setMode('select')}
                    className="text-sm text-neu-text dark:text-neu-text-dark hover:underline"
                  >
                    Back to options
                  </button>
                </div>
              )}
            </div>
          </NeumorphicCard>
        </motion.div>
      )}

      {/* Visitor Counter */}
      <VisitorCounter />
    </div>
  );
}
