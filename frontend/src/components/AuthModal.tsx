import React, { useState } from 'react';
import { X, Lock, User as UserIcon, Mail, ShieldAlert, Eye, EyeOff, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { User } from '../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: User) => void;
  initialMode?: 'signin' | 'signup';
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialMode = 'signin',
}) => {
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>(initialMode);
  const [identifier, setIdentifier] = useState('admin@enterprise.com');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberSession, setRememberSession] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [signupSuccess, setSignupSuccess] = useState(false);

  React.useEffect(() => {
    setActiveTab(initialMode);
    setPassword('');
    setError('');
  }, [initialMode, isOpen]);

  if (!isOpen) return null;

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await api.login(identifier.trim(), password);
      onSuccess(res.user);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const regUsername = username.trim() || email.split('@')[0].replace(/[^a-zA-Z0-9_-]/g, '_');
      const res = await api.register(regUsername, password, email.trim() || undefined);
      setSignupSuccess(true);
      setTimeout(() => {
        onSuccess(res.user);
        onClose();
      }, 700);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fillAdminCredentials = () => {
    setIdentifier('admin@enterprise.com');
    setPassword('');
    setError('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in">
      <div className="bg-[#0D131F] border border-[#2A374D] w-full max-w-md rounded-2xl shadow-2xl p-6 md:p-8 space-y-5 text-[#E2E8F0]">
        
        {/* Navigation Tabs & Close Button */}
        <div className="flex items-center justify-between border-b border-[#1E293B] pb-3">
          <div className="flex items-center gap-1 bg-[#070A10] p-1 rounded-lg border border-[#1E293B]">
            <button
              type="button"
              onClick={() => {
                setActiveTab('signin');
                setError('');
              }}
              className={`px-4 py-1.5 rounded-md text-xs font-semibold uppercase tracking-wider transition-all ${
                activeTab === 'signin'
                  ? 'bg-[#E11D48] text-white shadow-sm'
                  : 'text-[#94A3B8] hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab('signup');
                setError('');
              }}
              className={`px-4 py-1.5 rounded-md text-xs font-semibold uppercase tracking-wider transition-all ${
                activeTab === 'signup'
                  ? 'bg-[#E11D48] text-white shadow-sm'
                  : 'text-[#94A3B8] hover:text-white'
              }`}
            >
              Sign Up
            </button>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#94A3B8] hover:text-white rounded-lg hover:bg-[#1E293B] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Title & Subtitle */}
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            {activeTab === 'signin' ? 'Enterprise Sign In' : 'Create Enterprise Account'}
          </h2>
          <p className="text-xs text-[#94A3B8] mt-1">
            {activeTab === 'signin'
              ? 'Sign in to access industrial surveillance, thermal intelligence & analytics.'
              : 'Register for mission-critical industrial monitoring & thermal anomaly alerts.'}
          </p>
        </div>

        {/* Error Notification Banner */}
        {error && (
          <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs flex items-start gap-2.5 shadow-sm">
            <ShieldAlert className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <span className="font-semibold text-red-200">
                {activeTab === 'signin' ? 'Sign In Failed: ' : 'Registration Failed: '}
              </span>
              {error}
            </div>
          </div>
        )}

        {/* Success Banner */}
        {signupSuccess && (
          <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Account created successfully! Authenticating...</span>
          </div>
        )}

        {/* TAB 1: SIGN IN FORM */}
        {activeTab === 'signin' ? (
          <form onSubmit={handleSignIn} className="space-y-4 text-xs">
            <div>
              <label className="text-[11px] font-semibold text-[#94A3B8] block mb-1.5 uppercase tracking-wider">
                Work Email or Username
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[#64748B] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="admin@enterprise.com"
                  className="w-full bg-[#070A10] border border-[#2A374D] focus:border-[#E11D48] text-white pl-10 pr-3.5 py-2.5 rounded-xl focus:outline-none transition-colors text-xs"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[11px] font-semibold text-[#94A3B8] uppercase tracking-wider">
                  Password
                </label>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#64748B] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your security password"
                  className="w-full bg-[#070A10] border border-[#2A374D] focus:border-[#E11D48] text-white pl-10 pr-10 py-2.5 rounded-xl focus:outline-none transition-colors text-xs"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-[#E2E8F0] transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me Checkbox */}
            <div className="flex items-center justify-between text-xs pt-1">
              <label className="flex items-center gap-2 text-[#94A3B8] cursor-pointer hover:text-white select-none">
                <input
                  type="checkbox"
                  checked={rememberSession}
                  onChange={(e) => setRememberSession(e.target.checked)}
                  className="w-4 h-4 rounded border-[#2A374D] bg-[#070A10] text-[#E11D48] focus:ring-0 focus:ring-offset-0 cursor-pointer"
                />
                <span>Remember session (7 days)</span>
              </label>
              
              <button
                type="button"
                onClick={fillAdminCredentials}
                title="Prefill administrator email identifier"
                className="text-[11px] font-medium text-[#F59E0B] hover:text-[#FBBF24] hover:underline flex items-center gap-1"
              >
                <span>⚡ Use Admin Identifier</span>
              </button>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#E11D48] hover:bg-[#BE123C] disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl transition-all shadow-md text-xs uppercase tracking-wider font-mono mt-3"
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>
        ) : (
          /* TAB 2: SIGN UP / REGISTER FORM */
          <form onSubmit={handleSignUp} className="space-y-4 text-xs">
            <div>
              <label className="text-[11px] font-semibold text-[#94A3B8] block mb-1.5 uppercase tracking-wider">
                Full Name or Analyst Callsign
              </label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-[#64748B] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="analyst_callsign"
                  className="w-full bg-[#070A10] border border-[#2A374D] focus:border-[#E11D48] text-white pl-10 pr-3.5 py-2.5 rounded-xl focus:outline-none transition-colors text-xs"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-[#94A3B8] block mb-1.5 uppercase tracking-wider">
                Work Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[#64748B] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@enterprise.com"
                  className="w-full bg-[#070A10] border border-[#2A374D] focus:border-[#E11D48] text-white pl-10 pr-3.5 py-2.5 rounded-xl focus:outline-none transition-colors text-xs"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-[#94A3B8] block mb-1.5 uppercase tracking-wider">
                Security Password (Min 8 characters)
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#64748B] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Create a strong password"
                  className="w-full bg-[#070A10] border border-[#2A374D] focus:border-[#E11D48] text-white pl-10 pr-10 py-2.5 rounded-xl focus:outline-none transition-colors text-xs"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-[#E2E8F0] transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#E11D48] hover:bg-[#BE123C] disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl transition-all shadow-md text-xs uppercase tracking-wider font-mono mt-3"
            >
              {loading ? 'Creating Account...' : 'Create Enterprise Account'}
            </button>
          </form>
        )}

        {/* Footer Security Assurance */}
        <div className="pt-3 border-t border-[#1E293B] text-center">
          <p className="text-[11px] text-[#64748B] flex items-center justify-center gap-1.5">
            <span>🔒 Secured with Argon2id password hashing and rotating JWT tokens.</span>
          </p>
        </div>

      </div>
    </div>
  );
};
