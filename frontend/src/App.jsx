import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import RoleSelection from './pages/RoleSelection'
import PatientDashboard from './pages/PatientDashboard'
import CaretakerDashboard from './pages/CaretakerDashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RoleSelection />} />
        <Route path="/patient" element={<PatientDashboard />} />
        <Route path="/caretaker" element={<CaretakerDashboard />} />
        <Route path="/demo" element={<Home />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
