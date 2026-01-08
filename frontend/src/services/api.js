import axios from 'axios'

// Use environment variable or fallback to localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000' 

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const sendAudioToBackend = async (audioBlob) => {
  if (!audioBlob) throw new Error("No audio blob provided")

  const formData = new FormData()
  // Append with a filename so backend treats it as a file. 
  // Using .wav as required by the backend.
  formData.append('audio', audioBlob, 'recording.wav')

  try {
    const response = await apiClient.post('/api/audio', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  } catch (error) {
    console.error("API Error sending audio:", error)
    throw error
  }
}

/**
 * Submit feedback on a classification result
 * @param {string} embeddingId - The embedding_id from the audio response
 * @param {string} predictedIntent - What the system predicted
 * @param {boolean} isCorrect - True if prediction was correct
 * @param {string|null} correctIntent - If wrong, what should it be
 */
export const submitFeedback = async (embeddingId, predictedIntent, isCorrect, correctIntent = null) => {
  try {
    const params = new URLSearchParams({
      embedding_id: embeddingId,
      predicted_intent: predictedIntent,
      is_correct: isCorrect.toString(),
    })
    
    if (correctIntent) {
      params.append('correct_intent', correctIntent)
    }
    
    const response = await apiClient.post(`/api/audio/feedback?${params.toString()}`)
    return response.data
  } catch (error) {
    console.error("API Error submitting feedback:", error)
    throw error
  }
}

/**
 * Get available intents for correction dropdown
 */
export const getAvailableIntents = async () => {
  try {
    const response = await apiClient.get('/api/audio/intents/list')
    return response.data.intents
  } catch (error) {
    console.error("API Error getting intents:", error)
    throw error
  }
}

/**
 * Get intent database stats
 */
export const getIntentStats = async () => {
  try {
    const response = await apiClient.get('/api/audio/intents')
    return response.data.intents
  } catch (error) {
    console.error("API Error getting stats:", error)
    throw error
  }
}

/**
 * Register a visitor and get the total count
 */
export const registerVisitor = async () => {
  try {
    const response = await apiClient.post('/api/visitors/register')
    return response.data
  } catch (error) {
    console.error("API Error registering visitor:", error)
    throw error
  }
}

/**
 * Get current visitor count without registering
 */
export const getVisitorCount = async () => {
  try {
    const response = await apiClient.get('/api/visitors')
    return response.data.count
  } catch (error) {
    console.error("API Error getting visitor count:", error)
    throw error
  }
}


// =============================================================================
// USER MANAGEMENT
// =============================================================================

/**
 * Register a new user (patient or caretaker)
 */
export const registerUser = async (name, role) => {
  try {
    const response = await apiClient.post('/api/users/register', { name, role })
    return response.data
  } catch (error) {
    console.error("API Error registering user:", error)
    throw error
  }
}

/**
 * Get user by ID
 */
export const getUser = async (userId) => {
  try {
    const response = await apiClient.get(`/api/users/${userId}`)
    return response.data
  } catch (error) {
    console.error("API Error getting user:", error)
    throw error
  }
}

/**
 * Get all users by role
 */
export const getUsers = async (role = null) => {
  try {
    const url = role ? `/api/users/?role=${role}` : '/api/users/'
    const response = await apiClient.get(url)
    return response.data.users
  } catch (error) {
    console.error("API Error getting users:", error)
    throw error
  }
}

/**
 * Link a caretaker to a patient
 */
export const linkCaretaker = async (patientId, caretakerId) => {
  try {
    const response = await apiClient.post(
      `/api/users/patients/${patientId}/link-caretaker`,
      { caretaker_id: caretakerId }
    )
    return response.data
  } catch (error) {
    console.error("API Error linking caretaker:", error)
    throw error
  }
}

/**
 * Get caretakers for a patient
 */
export const getPatientCaretakers = async (patientId) => {
  try {
    const response = await apiClient.get(`/api/users/patients/${patientId}/caretakers`)
    return response.data
  } catch (error) {
    console.error("API Error getting caretakers:", error)
    throw error
  }
}

/**
 * Get patients for a caretaker
 */
export const getCaretakerPatients = async (caretakerId) => {
  try {
    const response = await apiClient.get(`/api/users/caretakers/${caretakerId}/patients`)
    return response.data
  } catch (error) {
    console.error("API Error getting patients:", error)
    throw error
  }
}

/**
 * Send notification from patient to caretakers
 */
export const sendNotification = async (patientId, intent, message, confidence = 0, transcription = "") => {
  try {
    const response = await apiClient.post('/api/users/notifications', {
      patient_id: patientId,
      intent,
      message,
      confidence,
      transcription
    })
    return response.data
  } catch (error) {
    console.error("API Error sending notification:", error)
    throw error
  }
}

/**
 * Get notifications for a caretaker
 */
export const getCaretakerNotifications = async (caretakerId, unreadOnly = false) => {
  try {
    const response = await apiClient.get(
      `/api/users/caretakers/${caretakerId}/notifications?unread_only=${unreadOnly}`
    )
    return response.data
  } catch (error) {
    console.error("API Error getting notifications:", error)
    throw error
  }
}

/**
 * Mark notification as read
 */
export const markNotificationRead = async (notificationId, caretakerId) => {
  try {
    const response = await apiClient.post(
      `/api/users/notifications/${notificationId}/read?caretaker_id=${caretakerId}`
    )
    return response.data
  } catch (error) {
    console.error("API Error marking notification read:", error)
    throw error
  }
}