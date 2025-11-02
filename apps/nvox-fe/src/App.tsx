import { useState, useEffect } from "react";
import { AuthForm } from "./components/AuthForm";
import { JourneyView } from "./components/JourneyView";
import { apiClient } from "./services/api";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.setOnUnauthorized(() => {
      setIsAuthenticated(false);
    });

    setIsAuthenticated(apiClient.isAuthenticated());
    setLoading(false);
  }, []);

  const handleAuthSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return isAuthenticated ? (
    <JourneyView onLogout={handleLogout} />
  ) : (
    <AuthForm onSuccess={handleAuthSuccess} />
  );
}

export default App;
