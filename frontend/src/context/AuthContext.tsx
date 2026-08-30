import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api, setCsrfToken, ApiError } from '../lib/api';

export interface User {
  id: string;
  username: string;
  email: string;
  email_verified: boolean;
  credit_balance: number;
}

interface AuthContextType {
  user: User | null;
  credits: number;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, pass: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
  refreshCredits: () => Promise<number>;
  claimAdReward: () => Promise<{ success: boolean; newBalance: number }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [credits, setCredits] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshCredits = useCallback(async (): Promise<number> => {
    try {
      const res = await api.get<{ balance: number }>('/api/v1/credits/balance');
      setCredits(res.balance);
      if (user) {
        setUser((prev) => (prev ? { ...prev, credit_balance: res.balance } : null));
      }
      return res.balance;
    } catch {
      return credits;
    }
  }, [user, credits]);

  const refreshUser = useCallback(async (): Promise<User | null> => {
    try {
      const me = await api.get<User>('/api/v1/auth/me');
      setUser(me);
      setCredits(me.credit_balance);
      return me;
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setUser(null);
      }
      return null;
    }
  }, []);

  // Check authenticated session with server on initial application boot
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const me = await api.get<User>('/api/v1/auth/me');
        if (mounted) {
          setUser(me);
          setCredits(me.credit_balance);
        }
      } catch {
        if (mounted) {
          setUser(null);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const login = async (email: string, pass: string): Promise<User> => {
    const res = await api.post<{ user: User; csrf_token: string }>('/api/v1/auth/login', {
      email,
      password: pass,
    });
    setCsrfToken(res.csrf_token);
    setUser(res.user);
    setCredits(res.user.credit_balance);
    return res.user;
  };

  const logout = async () => {
    try {
      await api.post('/api/v1/auth/logout');
    } catch {
      // Ignore network errors on logout
    }
    setCsrfToken(null);
    setUser(null);
    setCredits(0);
  };

  const claimAdReward = async (): Promise<{ success: boolean; newBalance: number }> => {
    // Generate unique event reference ID to prevent duplicates
    const refId = `ad_evt_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const res = await api.post<{ status: string; balance: number }>('/api/v1/credits/claim-ad-reward', {
      provider: 'sponsor_network',
      provider_reference_id: refId,
    });
    setCredits(res.balance);
    if (user) {
      setUser((prev) => (prev ? { ...prev, credit_balance: res.balance } : null));
    }
    return { success: true, newBalance: res.balance };
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        credits,
        loading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
        refreshCredits,
        claimAdReward,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};
