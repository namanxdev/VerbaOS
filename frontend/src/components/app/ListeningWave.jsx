import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

export default function ListeningWave({ status }) {
  // status: 'listening' | 'processing'
  
  const [text, setText] = useState("Listening...")

  useEffect(() => {
    if (status === 'processing') {
      const timer = setTimeout(() => {
        setText("Understanding your request...")
      }, 500) // Delay change slightly for effect
      return () => clearTimeout(timer)
    } else {
      setText("Listening...")
    }
  }, [status])

  // Simple visualizer bars simulation
  const bars = [1, 2, 3, 4, 5]

  return (
    <div className="flex flex-col items-center justify-center space-y-8 py-8">
      <div className="flex h-16 items-center justify-center space-x-2">
        {status === 'listening' ? (
          bars.map((bar) => (
            <motion.div
              key={bar}
              className="w-2 rounded-full bg-slate-500/80 dark:bg-slate-400/80"
              animate={{
                height: [16, 40, 16],
              }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                delay: bar * 0.1,
                repeatType: "reverse",
                ease: "easeInOut"
              }}
            />
          ))
        ) : (
           // Processing state - maybe a spinner or different wave
            <div className="flex gap-3">
               {[1,2,3].map(i => (
                 <motion.div
                   key={i}
                   className="w-4 h-4 bg-neu-text dark:bg-neu-text-dark rounded-full opacity-60"
                   animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
                   transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                  />
               ))}
            </div>
        )}
      </div>

      <motion.p
        key={text}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-lg font-medium text-gray-600"
      >
        {text}
      </motion.p>
    </div>
  )
}