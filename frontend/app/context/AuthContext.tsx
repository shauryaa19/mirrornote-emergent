import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import * as Linking from 'expo-linking';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const AUTH_URL = 'https://auth.emergentagent.com';

interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  isPremium: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  loginWithGoogle: () => void;
  logout: () => Promise<void>;
  updatePremiumStatus: (isPremium: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    initializeAuth();
    
    // Listen for deep links (returning from Google auth)
    const subscription = Linking.addEventListener('url', handleDeepLink);
    
    return () => subscription.remove();
  }, []);

  const initializeAuth = async () => {
    try {
      // Check for session_id in URL (coming back from Google auth)
      const url = await Linking.getInitialURL();
      if (url) {
        const { queryParams } = Linking.parse(url);
        if (queryParams?.session_id) {
          await processSessionId(queryParams.session_id as string);
          return;
        }
      }
      
      // Check existing session
      await checkSession();
    } catch (error) {
      console.error('Auth initialization error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeepLink = async ({ url }: { url: string }) => {
    const { queryParams } = Linking.parse(url);
    if (queryParams?.session_id) {
      await processSessionId(queryParams.session_id as string);
    }
  };

  const processSessionId = async (sessionId: string) => {
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/auth/session`,
        { session_id: sessionId },
        { withCredentials: true }
      );
      setUser(response.data);
    } catch (error) {
      console.error('Session processing error:', error);
    }
  };

  const checkSession = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/auth/me`, {
        withCredentials: true
      });
      setUser(response.data);
    } catch (error) {
      // No valid session
      setUser(null);
    }
  };

  const loginWithGoogle = () => {
    // Redirect URL is your app's main route (dashboard)
    const redirectUrl = Linking.createURL('/(tabs)/dashboard');
    const authUrl = `${AUTH_URL}/?redirect=${encodeURIComponent(redirectUrl)}`;
    
    // Open auth URL in browser
    Linking.openURL(authUrl);
  };

  const logout = async () => {
    try {
      await axios.post(`${BACKEND_URL}/api/auth/logout`, {}, {
        withCredentials: true
      });
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const updatePremiumStatus = (isPremium: boolean) => {
    if (user) {
      setUser({ ...user, isPremium });
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, logout, updatePremiumStatus }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
