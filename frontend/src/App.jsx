import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Footer from './components/Footer';
import ChatbotWidget from './components/chatbot/ChatbotWidget';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import { AnalysisProvider } from './context/AnalysisContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import Assistant from './pages/Assistant';
import Classification from './pages/Classification';
import GradCAM from './pages/GradCAM';
import Home from './pages/Home';
import History from './pages/History';
import HowItWorks from './pages/HowItWorks';
import LesionDetection from './pages/LesionDetection';
import Login from './pages/Login';
import MedicalReportPreview from './pages/MedicalReportPreview';
import Profile from './pages/Profile';
import Register from './pages/Register';

function AppShell() {
  const { isAuthenticated, isAuthLoading } = useAuth();
  const location = useLocation();
  const isAuthPage = ['/login', '/register'].includes(location.pathname);
  const isAssistantPage = location.pathname === '/assistant';

  if (isAuthLoading) {
    return <main className="min-h-screen bg-slate-50" />;
  }

  return (
    <>
      {!isAuthPage && <Navbar />}
      <main className="min-h-screen bg-slate-50">
        <Routes>
          <Route path="/" element={<Navigate to={isAuthenticated ? '/home' : '/login'} replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/home"
            element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <History />
              </ProtectedRoute>
            }
          />
          <Route
            path="/how-it-works"
            element={
              <ProtectedRoute>
                <HowItWorks />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis/classification"
            element={
              <ProtectedRoute>
                <Classification />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis/lesions"
            element={
              <ProtectedRoute>
                <LesionDetection />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis/gradcam"
            element={
              <ProtectedRoute>
                <GradCAM />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assistant"
            element={
              <ProtectedRoute>
                <Assistant />
              </ProtectedRoute>
            }
          />
          <Route
            path="/report/:analysisId"
            element={
              <ProtectedRoute>
                <MedicalReportPreview />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
      {!isAuthPage && <Footer />}
      {!isAuthPage && !isAssistantPage && <ChatbotWidget />}
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AnalysisProvider>
        <BrowserRouter>
          <AppShell />
        </BrowserRouter>
      </AnalysisProvider>
    </AuthProvider>
  );
}
