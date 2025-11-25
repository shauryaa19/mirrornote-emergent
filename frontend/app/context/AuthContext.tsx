import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import axios from 'axios';
import * as Linking from 'expo-linking';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const AUTH_URL = 'https://auth.emergentagent.com';
const SESSION_TOKEN_KEY = '@session_token';

interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  loginWithGoogle: () => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Set up axios interceptor to add Authorization header and handle errors
axios.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem(SESSION_TOKEN_KEY);
    if (token) {
      if (!config.headers) {
        config.headers = {} as any;
      }
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Handle Rate Limiting
      if (error.response.status === 429) {
        Alert.alert(
          "Too Many Requests",
          "You're doing that too fast. Please wait a moment and try again."
        );
      }
      // Handle Unauthorized (Session Expired)
      else if (error.response.status === 401) {
        // Optional: Trigger logout or refresh logic here
        console.log("Session expired or unauthorized");
      }
    } else if (error.request) {
      // Network error
      Alert.alert(
        "Network Error",
        "Please check your internet connection."
      );
    }
    return Promise.reject(error);
  }
);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const processingRef = useRef<string | null>(null);
  const processingLockRef = useRef(false);

  useEffect(() => {
    initializeAuth();

    const subscription = Linking.addEventListener('url', handleDeepLink);

    return () => subscription.remove();
  }, []);

  const initializeAuth = async () => {
    try {
      const url = await Linking.getInitialURL();

      if (url) {
        const sessionId = extractSessionId(url);

        if (sessionId) {
          await processSessionId(sessionId);
          return;
        }
      }

      await checkSession();
    } catch (error) {
      console.error('[AuthContext] Auth initialization error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeepLink = async ({ url }: { url: string }) => {
    const sessionId = extractSessionId(url);

    if (sessionId) {
      if (processingRef.current === sessionId || processingLockRef.current) {
        return;
      }

      await processSessionId(sessionId);
    }
  };

  const extractSessionId = (url: string): string | null => {
    const hashMatch = url.match(/#.*session_id=([^&]+)/);
    if (hashMatch) {
      return hashMatch[1];
    }

    const { queryParams } = Linking.parse(url);

    if (queryParams?.session_id) {
      return queryParams.session_id as string;
    }

    return null;
  };

  const processSessionId = async (sessionId: string) => {
    if (processingLockRef.current) {
      return;
    }

    if (processingRef.current === sessionId) {
      return;
    }

    processingLockRef.current = true;
    processingRef.current = sessionId;

    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/auth/session`,
        { session_id: sessionId }
      );

      if (response.data.session_token) {
        await AsyncStorage.setItem(SESSION_TOKEN_KEY, response.data.session_token);
      }

      const { session_token, ...userData } = response.data;
      setUser(userData);
    } catch (error) {
      console.error('[AuthContext] Session processing error:', error);
      await AsyncStorage.removeItem(SESSION_TOKEN_KEY);
      setUser(null);
    } finally {
      processingLockRef.current = false;
      processingRef.current = null;
    }
  };

  const checkSession = async () => {
    try {
      const token = await AsyncStorage.getItem(SESSION_TOKEN_KEY);

      if (!token) {
        setUser(null);
        return;
      }

      const response = await axios.get(`${BACKEND_URL}/api/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('[AuthContext] Session check error:', error);
      await AsyncStorage.removeItem(SESSION_TOKEN_KEY);
      setUser(null);
    }
  };

  const loginWithGoogle = () => {
    const redirectUrl = Linking.createURL('/dashboard');
    const authUrl = `${AUTH_URL}/?redirect=${encodeURIComponent(redirectUrl)}`;
    Linking.openURL(authUrl);
  };

  const logout = async () => {
    try {
      await axios.post(`${BACKEND_URL}/api/auth/logout`);
      await AsyncStorage.removeItem(SESSION_TOKEN_KEY);
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      await AsyncStorage.removeItem(SESSION_TOKEN_KEY);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, logout }}>
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

export default function AuthContextRoute() {
  return null;
}
