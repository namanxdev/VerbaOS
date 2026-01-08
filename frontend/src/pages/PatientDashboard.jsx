import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Toaster } from '../components/ui/toaster'
import { useToast } from '../hooks/use-toast'
import { Button } from '../components/ui/button'
import RecordButton from '../components/app/RecordButton'
import ListeningWave from '../components/app/ListeningWave'
import IntentCard from '../components/app/IntentCard'
import ActionButtons from '../components/app/ActionButtons'
import FeedbackButtons from '../components/app/FeedbackButtons'
import DiagramLayout from '../components/app/DiagramLayout'
import ThemeToggle from '../components/ui/ThemeToggle'
import NeumorphicCard from '../components/ui/NeumorphicCard'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { 
  sendAudioToBackend, 
  submitFeedback, 
  sendNotification,
  getPatientCaretakers,
  linkCaretaker,
  getUsers
} from '../services/api'
import { motion, AnimatePresence } from 'framer-motion'


export default function PatientDashboard() {
  const navigate = useNavigate()
  
  // User state
  const [user, setUser] = useState(null)
  const [caretakers, setCaretakers] = useState([])
  const [showAddCaretaker, setShowAddCaretaker] = useState(false)
  const [availableCaretakers, setAvailableCaretakers] = useState([])
  
  // App states: idle, recording, processing, result, feedback_submitted
  const [appState, setAppState] = useState('idle') 
  const [result, setResult] = useState(null)
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false)
  const [feedbackResult, setFeedbackResult] = useState(null)
  const [notificationSent, setNotificationSent] = useState(false)
  
  const { startRecording, stopRecording, isRecording, audioBlob, error: recorderError } = useAudioRecorder()
  const { toast } = useToast()

  // Steps for the Diagram: 0=Input, 1=Encoder, 2=Classifier, 3=Output
  const [diagramStep, setDiagramStep] = useState(0)

  // Check user session on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('speechIntentUser')
    if (!savedUser) {
      navigate('/')
      return
    }
    
    const userData = JSON.parse(savedUser)
    if (userData.role !== 'patient') {
      navigate('/')
      return
    }
    
    setUser(userData)
    
    // Only try to load caretakers if not a local-only session
    if (!userData.id.startsWith('local_')) {
      loadCaretakers(userData.id)
    }
  }, [navigate])

  const loadCaretakers = async (patientId) => {
    try {
      const data = await getPatientCaretakers(patientId)
      setCaretakers(data.caretakers || [])
    } catch (err) {
      console.error('Failed to load caretakers:', err)
    }
  }

  useEffect(() => {
    switch (appState) {
        case 'idle': setDiagramStep(0); break;
        case 'recording': setDiagramStep(1); break;
        case 'processing': setDiagramStep(2); break;
        case 'result': setDiagramStep(3); break;
        case 'error': setDiagramStep(0); break;
    }
  }, [appState]);

  useEffect(() => {
    if (recorderError) {
      toast({
        variant: "destructive",
        title: "Microphone Error",
        description: recorderError
      })
      setAppState('idle')
    }
  }, [recorderError, toast])

  // Watch for blob update
  useEffect(() => {
    if (audioBlob && appState === 'recording') {
       handleAudioUpload(audioBlob)
    }
  }, [audioBlob])

  const handleStart = async () => {
    setAppState('recording')
    setResult(null)
    setNotificationSent(false)
    await startRecording()
  }

  const handleStop = () => {
    stopRecording()
  }

  const handleAudioUpload = async (blob) => {
    setAppState('processing')
    try {
      const data = await sendAudioToBackend(blob)
      setResult(data)
      setAppState('result')
      
      // Automatically send notification to caretakers if we have any
      if (caretakers.length > 0 && user) {
        sendNotificationToCaretakers(data)
      }
    } catch (err) {
      console.error(err)
      toast({
        variant: "destructive",
        title: "Upload Failed",
        description: "Could not process your request. Please try again."
      })
      setAppState('error')
      setTimeout(() => setAppState('idle'), 3000)
    }
  }

  const sendNotificationToCaretakers = async (resultData) => {
    try {
      await sendNotification(
        user.id,
        resultData.intent,
        resultData.confidence,
        resultData.transcription
      )
      setNotificationSent(true)
      toast({
        title: "📢 Caretakers Notified",
        description: `Your ${caretakers.length} caretaker(s) have been alerted.`,
        className: "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200"
      })
    } catch (err) {
      console.error('Failed to send notification:', err)
    }
  }

  const handleAction = (action) => {
    toast({
      title: "Action Confirmed",
      description: `Proceeding with: ${action}`,
      className: "bg-neu-base border-white/50 text-neu-dark shadow-neu-flat"
    })
    
    setTimeout(() => {
        setAppState('idle')
        setResult(null)
        setFeedbackResult(null)
        setNotificationSent(false)
    }, 2000)
  }

  const handleFeedbackSubmit = async ({ embeddingId, predictedIntent, isCorrect, correctIntent }) => {
    if (!embeddingId) {
      toast({
        variant: "destructive",
        title: "Feedback Error",
        description: "No embedding ID available. The system may be using transcription-only mode."
      })
      return
    }

    setFeedbackSubmitting(true)
    try {
      const response = await submitFeedback(embeddingId, predictedIntent, isCorrect, correctIntent)
      setFeedbackResult(response)
      
      toast({
        title: isCorrect ? "✓ Feedback Recorded" : "✓ Correction Learned",
        description: response.message,
        className: "bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800 text-green-800 dark:text-green-200"
      })

      if (!isCorrect && correctIntent) {
        setAppState('feedback_submitted')
      }
    } catch (err) {
      console.error('Feedback error:', err)
      toast({
        variant: "destructive",
        title: "Feedback Failed",
        description: "Could not submit feedback. Please try again."
      })
    } finally {
      setFeedbackSubmitting(false)
    }
  }

  const resetSession = () => {
    setAppState('idle')
    setResult(null)
    setFeedbackResult(null)
    setNotificationSent(false)
  }

  const handleAddCaretaker = async () => {
    try {
      const allCaretakers = await getUsers('caretaker')
      const caretakerIds = caretakers.map(c => c.id)
      const available = allCaretakers.filter(c => !caretakerIds.includes(c.id))
      setAvailableCaretakers(available)
      setShowAddCaretaker(true)
    } catch (err) {
      console.error('Failed to load caretakers:', err)
    }
  }

  const handleLinkCaretaker = async (caretakerId) => {
    try {
      await linkCaretaker(user.id, caretakerId)
      await loadCaretakers(user.id)
      setShowAddCaretaker(false)
      toast({
        title: "✓ Caretaker Added",
        description: "They will now receive your notifications.",
        className: "bg-green-50 dark:bg-green-900/30 border-green-200 text-green-800"
      })
    } catch (err) {
      console.error('Failed to link caretaker:', err)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('speechIntentUser')
    navigate('/')
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-neu-base dark:bg-neu-base-dark flex items-center justify-center">
        <div className="animate-pulse text-neu-text dark:text-neu-text-dark text-xl">
          Loading...
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-neu-base dark:bg-neu-base-dark flex flex-col items-center py-4 px-6 lg:px-12 font-sans text-neu-dark dark:text-neu-text-dark transition-colors duration-500 overflow-x-hidden">
      
      {/* Header with User Info */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-7xl flex flex-col md:flex-row items-center justify-between mb-4 flex-shrink-0 relative z-10"
      >
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <Button
            onClick={handleLogout}
            className="bg-neu-base dark:bg-neu-base-dark shadow-neu-flat dark:shadow-neu-flat-dark hover:shadow-neu-pressed text-slate-600 dark:text-slate-300 px-3 py-2 rounded-xl text-sm"
          >
            Logout
          </Button>
        </div>

        <div className="text-center w-full md:text-left md:w-auto mt-2 md:mt-0">
            <h1 className="text-2xl md:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-700 dark:text-slate-100">
              VerbaOS
            </h1>
            <p className="text-neu-text dark:text-neu-text-dark mt-1 text-sm md:text-base">
              Welcome, <strong>{user.name}</strong>
              <span className="text-xs ml-2 font-mono opacity-50">ID: {user.id}</span>
            </p>
        </div>

        {/* Caretakers Badge */}
        <button
          onClick={handleAddCaretaker}
          className="mt-2 md:mt-0 flex items-center gap-2 px-4 py-2 rounded-xl bg-neu-base dark:bg-neu-base-dark shadow-neu-flat dark:shadow-neu-flat-dark hover:shadow-neu-pressed transition-all"
        >
          <span className="text-2xl">👥</span>
          <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
            {caretakers.length} Caretaker{caretakers.length !== 1 ? 's' : ''}
          </span>
        </button>
      </motion.header>

      {/* System Diagram */}
      <div className="w-full max-w-[1400px] flex-shrink-0 mb-4 scale-90 origin-top">
        <DiagramLayout activeStep={diagramStep} />
      </div>

      {/* Main Interaction Area */}
      <main className="w-full max-w-2xl flex flex-col items-center justify-center flex-grow">
        <AnimatePresence mode="wait">
          
          {/* IDLE State */}
          {appState === 'idle' && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col items-center"
            >
               <RecordButton 
                  isRecording={false}
                  onClick={handleStart}
               />
               {caretakers.length === 0 && (
                 <p className="mt-4 text-sm text-orange-600 dark:text-orange-400 text-center">
                   ⚠️ No caretakers linked. Add a caretaker to send notifications.
                 </p>
               )}
            </motion.div>
          )}

          {/* RECORDING State */}
          {appState === 'recording' && (
             <motion.div
               key="recording"
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               exit={{ opacity: 0 }}
               className="flex flex-col items-center justify-center h-full"
             >
                <div className="mb-8 scale-150">
                     <ListeningWave status="listening" />
                </div>
                <RecordButton 
                    isRecording={true}
                    onClick={handleStop}
                />
             </motion.div>
          )}

           {/* PROCESSING State */}
           {appState === 'processing' && (
             <motion.div
               key="processing"
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               exit={{ opacity: 0 }}
               className="flex flex-col items-center justify-center h-full"
             >
                <div className="scale-150 mb-6">
                     <ListeningWave status="processing" />
                </div>
                <p className="mt-4 text-neu-text dark:text-neu-text-dark text-lg font-medium animate-pulse tracking-wide">
                    Analyzing Audio Signature...
                </p>
             </motion.div>
          )}

           {/* RESULT State */}
           {appState === 'result' && result && (
             <motion.div
               key="result"
               initial={{ opacity: 0, y: 30 }}
               animate={{ opacity: 1, y: 0 }}
               exit={{ opacity: 0, y: -30 }}
               className="w-full flex flex-col items-center justify-center h-full"
             >
                <div className="scale-90 md:scale-100 origin-center w-full">
                    {/* Notification Badge */}
                    {notificationSent && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-4 px-4 py-2 bg-blue-100 dark:bg-blue-900/30 rounded-xl text-center text-sm text-blue-700 dark:text-blue-300"
                      >
                        📢 Notification sent to {caretakers.length} caretaker(s)
                      </motion.div>
                    )}
                    
                    <IntentCard 
                        intent={result.intent} 
                        confidence={result.confidence}
                        transcription={result.transcription}
                    />
                    
                    {/* Feedback Section */}
                    <FeedbackButtons
                      embeddingId={result.embedding_id}
                      predictedIntent={result.intent}
                      onFeedbackSubmit={handleFeedbackSubmit}
                      isSubmitting={feedbackSubmitting}
                    />
                    
                    {/* Action Buttons */}
                    <ActionButtons 
                        intent={result.intent} 
                        onAction={handleAction} 
                    />
                </div>
                 <div className="mt-8 text-center">
                    <button 
                        onClick={resetSession}
                        className="text-sm text-neu-text dark:text-neu-text-dark hover:text-primary dark:hover:text-blue-400 transition-colors hover:underline underline-offset-4"
                    >
                        Start New Session
                    </button>
                 </div>
             </motion.div>
          )}

          {/* FEEDBACK SUBMITTED State */}
          {appState === 'feedback_submitted' && (
            <motion.div
              key="feedback_submitted"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center justify-center text-center"
            >
              <div className="w-20 h-20 mb-6 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <svg className="w-10 h-10 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-slate-700 dark:text-slate-100 mb-2">
                Thanks for the correction!
              </h2>
              <p className="text-neu-text dark:text-neu-text-dark mb-6">
                The system will learn from this feedback.
              </p>
              {feedbackResult && (
                <p className="text-sm text-green-600 dark:text-green-400 mb-6">
                  {feedbackResult.message}
                </p>
              )}
              <Button
                onClick={resetSession}
                className="bg-neu-base dark:bg-neu-base-dark text-slate-700 dark:text-slate-200 shadow-neu-flat dark:shadow-neu-flat-dark hover:shadow-neu-pressed px-8 py-4 rounded-2xl font-semibold"
              >
                Start New Session
              </Button>
            </motion.div>
          )}

        </AnimatePresence>
      </main>

      {/* Add Caretaker Modal */}
      <AnimatePresence>
        {showAddCaretaker && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
            onClick={() => setShowAddCaretaker(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md"
            >
              <NeumorphicCard>
                <h2 className="text-xl font-bold text-slate-700 dark:text-slate-100 mb-2">
                  My Caretakers
                </h2>
                
                {/* Current caretakers */}
                {caretakers.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm text-neu-text dark:text-neu-text-dark mb-2">Currently linked:</p>
                    <div className="space-y-2">
                      {caretakers.map(c => (
                        <div key={c.id} className="flex items-center gap-2 px-3 py-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
                          <span className="text-green-600 dark:text-green-400">✓</span>
                          <span className="text-slate-700 dark:text-slate-200">{c.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Available caretakers to add */}
                <p className="text-sm text-neu-text dark:text-neu-text-dark mb-2">Add a caretaker:</p>
                {availableCaretakers.length === 0 ? (
                  <p className="text-neu-text dark:text-neu-text-dark text-sm italic">
                    No available caretakers. Ask caretakers to register first.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {availableCaretakers.map((caretaker) => (
                      <button
                        key={caretaker.id}
                        onClick={() => handleLinkCaretaker(caretaker.id)}
                        className="w-full flex items-center gap-3 p-3 rounded-xl bg-neu-base dark:bg-neu-base-dark shadow-neu-flat dark:shadow-neu-flat-dark hover:shadow-neu-pressed transition-all"
                      >
                        <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/40 flex items-center justify-center">
                          <span className="font-bold text-purple-600 dark:text-purple-400">
                            {caretaker.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="text-left">
                          <div className="font-semibold text-slate-700 dark:text-slate-100">
                            {caretaker.name}
                          </div>
                          <div className="text-xs text-neu-text dark:text-neu-text-dark font-mono">
                            {caretaker.id}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                
                <button
                  onClick={() => setShowAddCaretaker(false)}
                  className="mt-4 w-full text-center text-neu-text dark:text-neu-text-dark hover:underline"
                >
                  Close
                </button>
              </NeumorphicCard>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <Toaster />
    </div>
  )
}
