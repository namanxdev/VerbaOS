import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  getCaretakerPatients, 
  getCaretakerNotifications, 
  markNotificationRead,
  getUsers,
  linkCaretaker 
} from '../services/api';
import NeumorphicCard from '../components/ui/NeumorphicCard';
import { Button } from '../components/ui/button';
import ThemeToggle from '../components/ui/ThemeToggle';

export default function CaretakerDashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [patients, setPatients] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showAddPatient, setShowAddPatient] = useState(false);
  const [availablePatients, setAvailablePatients] = useState([]);
  const [selectedTab, setSelectedTab] = useState('notifications'); // 'notifications' | 'patients'

  useEffect(() => {
    const savedUser = localStorage.getItem('speechIntentUser');
    if (!savedUser) {
      navigate('/');
      return;
    }
    
    const userData = JSON.parse(savedUser);
    if (userData.role !== 'caretaker') {
      navigate('/');
      return;
    }
    
    setUser(userData);
    loadData(userData.id);
    
    // Poll for new notifications every 5 seconds
    const interval = setInterval(() => {
      loadNotifications(userData.id);
    }, 5000);
    
    return () => clearInterval(interval);
  }, [navigate]);

  const loadData = async (caretakerId) => {
    setLoading(true);
    try {
      await Promise.all([
        loadPatients(caretakerId),
        loadNotifications(caretakerId)
      ]);
    } finally {
      setLoading(false);
    }
  };

  const loadPatients = async (caretakerId) => {
    try {
      const data = await getCaretakerPatients(caretakerId);
      setPatients(data.patients || []);
    } catch (err) {
      console.error('Failed to load patients:', err);
    }
  };

  const loadNotifications = async (caretakerId) => {
    try {
      const data = await getCaretakerNotifications(caretakerId);
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread || 0);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    }
  };

  const handleMarkRead = async (notificationId) => {
    try {
      await markNotificationRead(notificationId, user.id);
      setNotifications(notifications.map(n => 
        n.id === notificationId ? { ...n, read: true } : n
      ));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to mark as read:', err);
    }
  };

  const handleAddPatient = async () => {
    try {
      const allPatients = await getUsers('patient');
      // Filter out already linked patients
      const patientIds = patients.map(p => p.id);
      const available = allPatients.filter(p => !patientIds.includes(p.id));
      setAvailablePatients(available);
      setShowAddPatient(true);
    } catch (err) {
      console.error('Failed to load patients:', err);
    }
  };

  const handleLinkPatient = async (patientId) => {
    try {
      await linkCaretaker(patientId, user.id);
      await loadPatients(user.id);
      setShowAddPatient(false);
    } catch (err) {
      console.error('Failed to link patient:', err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('speechIntentUser');
    navigate('/');
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  const getIntentColor = (intent) => {
    const colors = {
      EMERGENCY: 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400 border-red-300',
      HELP: 'bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-400 border-orange-300',
      WATER: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 border-blue-300',
      PAIN: 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-400 border-purple-300',
      BATHROOM: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-400 border-yellow-300',
      TIRED: 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-400 border-indigo-300',
      COLD: 'bg-cyan-100 dark:bg-cyan-900/40 text-cyan-700 dark:text-cyan-400 border-cyan-300',
      HOT: 'bg-pink-100 dark:bg-pink-900/40 text-pink-700 dark:text-pink-400 border-pink-300',
    };
    return colors[intent] || 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neu-base dark:bg-neu-base-dark flex items-center justify-center">
        <div className="animate-pulse text-neu-text dark:text-neu-text-dark text-xl">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neu-base dark:bg-neu-base-dark p-4 md:p-6 transition-colors duration-500">
      
      {/* Header */}
      <header className="max-w-6xl mx-auto flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-slate-700 dark:text-slate-100">
            Caretaker Dashboard
          </h1>
          <p className="text-neu-text dark:text-neu-text-dark">
            Welcome, {user?.name} 
            <span className="text-xs ml-2 font-mono opacity-50">ID: {user?.id}</span>
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <Button
            onClick={handleLogout}
            className="bg-neu-base dark:bg-neu-base-dark shadow-neu-flat dark:shadow-neu-flat-dark hover:shadow-neu-pressed text-slate-600 dark:text-slate-300 px-4 py-2 rounded-xl"
          >
            Logout
          </Button>
        </div>
      </header>

      {/* Stats Bar */}
      <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <NeumorphicCard className="text-center py-4">
          <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">{patients.length}</div>
          <div className="text-sm text-neu-text dark:text-neu-text-dark">Patients</div>
        </NeumorphicCard>
        <NeumorphicCard className="text-center py-4">
          <div className="text-3xl font-bold text-orange-600 dark:text-orange-400">{unreadCount}</div>
          <div className="text-sm text-neu-text dark:text-neu-text-dark">Unread</div>
        </NeumorphicCard>
        <NeumorphicCard className="text-center py-4">
          <div className="text-3xl font-bold text-green-600 dark:text-green-400">{notifications.length}</div>
          <div className="text-sm text-neu-text dark:text-neu-text-dark">Total Alerts</div>
        </NeumorphicCard>
        <NeumorphicCard className="text-center py-4">
          <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">
            {notifications.filter(n => n.intent === 'EMERGENCY').length}
          </div>
          <div className="text-sm text-neu-text dark:text-neu-text-dark">Emergencies</div>
        </NeumorphicCard>
      </div>

      {/* Tabs */}
      <div className="max-w-6xl mx-auto mb-6">
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedTab('notifications')}
            className={`px-6 py-3 rounded-xl font-semibold transition-all ${
              selectedTab === 'notifications'
                ? 'bg-blue-500 text-white shadow-lg'
                : 'bg-neu-base dark:bg-neu-base-dark shadow-neu-flat dark:shadow-neu-flat-dark text-slate-600 dark:text-slate-300'
            }`}
          >
            Notifications {unreadCount > 0 && `(${unreadCount})`}
          </button>
          <button
            onClick={() => setSelectedTab('patients')}
            className={`px-6 py-3 rounded-xl font-semibold transition-all ${
              selectedTab === 'patients'
                ? 'bg-blue-500 text-white shadow-lg'
                : 'bg-neu-base dark:bg-neu-base-dark shadow-neu-flat dark:shadow-neu-flat-dark text-slate-600 dark:text-slate-300'
            }`}
          >
            My Patients
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto">
        <AnimatePresence mode="wait">
          {selectedTab === 'notifications' && (
            <motion.div
              key="notifications"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              {notifications.length === 0 ? (
                <NeumorphicCard className="text-center py-12">
                  <div className="text-6xl mb-4">🔔</div>
                  <h3 className="text-xl font-semibold text-slate-700 dark:text-slate-100 mb-2">
                    No notifications yet
                  </h3>
                  <p className="text-neu-text dark:text-neu-text-dark">
                    You'll see patient requests here when they need help
                  </p>
                </NeumorphicCard>
              ) : (
                <div className="space-y-4">
                  {notifications.map((notif) => (
                    <motion.div
                      key={notif.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`rounded-2xl border-l-4 ${getIntentColor(notif.intent)} ${
                        !notif.read ? 'ring-2 ring-blue-400' : ''
                      }`}
                    >
                      <NeumorphicCard className="!rounded-l-none">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <span className={`px-3 py-1 rounded-full text-sm font-bold ${getIntentColor(notif.intent)}`}>
                                {notif.intent}
                              </span>
                              <span className="text-sm text-neu-text dark:text-neu-text-dark">
                                from <strong>{notif.patient_name}</strong>
                              </span>
                              {!notif.read && (
                                <span className="px-2 py-0.5 bg-blue-500 text-white text-xs rounded-full">
                                  NEW
                                </span>
                              )}
                            </div>
                            <p className="text-lg text-slate-700 dark:text-slate-200 mb-1">
                              {notif.message}
                            </p>
                            {notif.transcription && (
                              <p className="text-sm text-neu-text/70 dark:text-neu-text-dark/70 italic">
                                "{notif.transcription}"
                              </p>
                            )}
                            <p className="text-xs text-neu-text/50 dark:text-neu-text-dark/50 mt-2">
                              {formatTime(notif.timestamp)} • Confidence: {(notif.confidence * 100).toFixed(0)}%
                            </p>
                          </div>
                          {!notif.read && (
                            <Button
                              onClick={() => handleMarkRead(notif.id)}
                              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-xl text-sm"
                            >
                              Mark Done
                            </Button>
                          )}
                        </div>
                      </NeumorphicCard>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {selectedTab === 'patients' && (
            <motion.div
              key="patients"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <div className="flex justify-end mb-4">
                <Button
                  onClick={handleAddPatient}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Add Patient
                </Button>
              </div>

              {patients.length === 0 ? (
                <NeumorphicCard className="text-center py-12">
                  <div className="text-6xl mb-4">👥</div>
                  <h3 className="text-xl font-semibold text-slate-700 dark:text-slate-100 mb-2">
                    No patients yet
                  </h3>
                  <p className="text-neu-text dark:text-neu-text-dark">
                    Add patients to start receiving their notifications
                  </p>
                </NeumorphicCard>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {patients.map((patient) => (
                    <NeumorphicCard key={patient.id}>
                      <div className="flex items-center gap-4">
                        <div className="w-14 h-14 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                          <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                            {patient.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-100">
                            {patient.name}
                          </h3>
                          <p className="text-sm text-neu-text dark:text-neu-text-dark font-mono">
                            ID: {patient.id}
                          </p>
                        </div>
                      </div>
                    </NeumorphicCard>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Add Patient Modal */}
      <AnimatePresence>
        {showAddPatient && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
            onClick={() => setShowAddPatient(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md"
            >
              <NeumorphicCard>
                <h2 className="text-xl font-bold text-slate-700 dark:text-slate-100 mb-4">
                  Add Patient
                </h2>
                {availablePatients.length === 0 ? (
                  <p className="text-neu-text dark:text-neu-text-dark">
                    No available patients to add. Ask patients to register first.
                  </p>
                ) : (
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {availablePatients.map((patient) => (
                      <button
                        key={patient.id}
                        onClick={() => handleLinkPatient(patient.id)}
                        className="w-full flex items-center gap-3 p-3 rounded-xl bg-neu-base dark:bg-neu-base-dark shadow-neu-flat dark:shadow-neu-flat-dark hover:shadow-neu-pressed transition-all"
                      >
                        <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                          <span className="font-bold text-blue-600 dark:text-blue-400">
                            {patient.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="text-left">
                          <div className="font-semibold text-slate-700 dark:text-slate-100">
                            {patient.name}
                          </div>
                          <div className="text-xs text-neu-text dark:text-neu-text-dark font-mono">
                            {patient.id}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                <button
                  onClick={() => setShowAddPatient(false)}
                  className="mt-4 w-full text-center text-neu-text dark:text-neu-text-dark hover:underline"
                >
                  Cancel
                </button>
              </NeumorphicCard>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
