import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CloudSun, Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../services/api.js';
import { consumeReturnTo } from '../services/api.js';
import { useAuth } from '../context/AuthContext.jsx';

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
  });

  const sessionExpired = searchParams.get('auto') === 'expired';

  const redirectAfterLogin = () => {
    const returnTo = consumeReturnTo() || searchParams.get('return');
    navigate(returnTo && returnTo.startsWith('/') ? returnTo : '/dashboard', { replace: true });
  };

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formData = new URLSearchParams();
      formData.append('username', form.username.trim());
      formData.append('password', form.password);

      const response = await api.post('/api/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const { access_token, user } = response.data;
      login(access_token, user);
      redirectAfterLogin();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || d.message).join(', ')
          : 'Login failed. Please check your credentials.';
      setError(message);
    }
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await api.post('/api/auth/register', {
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        full_name: form.full_name.trim(),
      });

      const loginFormData = new URLSearchParams();
      loginFormData.append('username', form.username.trim());
      loginFormData.append('password', form.password);

      const loginResponse = await api.post('/api/auth/login', loginFormData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const { access_token, user } = loginResponse.data;
      login(access_token, user);
      redirectAfterLogin();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || d.message).join(', ')
          : 'Registration failed. Please try again.';
      setError(message);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#F7F7F5] text-[#111111] flex items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-md">
        
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-[#111111] text-white flex items-center justify-center mx-auto mb-3 shadow-sm">
            <CloudSun className="w-6 h-6 text-[#D9A441]" />
          </div>
          <h1 className="text-2xl font-bold text-[#111111] tracking-tight">Weather Intel Portal</h1>
          <p className="text-xs text-[#66635C] mt-1 font-medium">
            National Severe Weather Big Data & Analytics Platform
          </p>
        </div>

        <div className="bg-white border border-[#E5E2DA] rounded-xl shadow-sm p-6 sm:p-8">
          {/* Tab Selector */}
          <div className="flex p-1 bg-[#F7F7F5] rounded-full border border-[#E5E2DA] mb-6">
            <button
              onClick={() => { setIsRegister(false); setError(''); }}
              className={`flex-1 py-2 text-xs font-bold rounded-full transition-all ${
                !isRegister
                  ? 'bg-[#111111] text-white shadow-sm'
                  : 'text-[#66635C] hover:text-[#111111]'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setIsRegister(true); setError(''); }}
              className={`flex-1 py-2 text-xs font-bold rounded-full transition-all ${
                isRegister
                  ? 'bg-[#111111] text-white shadow-sm'
                  : 'text-[#66635C] hover:text-[#111111]'
              }`}
            >
              Register
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-700 text-xs font-medium">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-600" />
              {error}
            </div>
          )}

          {sessionExpired && !error && (
            <div className="flex items-center gap-2 p-3 mb-4 bg-[#F7EED7] border border-[#D9A441]/30 rounded-lg text-[#A97820] text-xs font-medium">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-[#D9A441]" />
              Your session expired. Please sign in again.
            </div>
          )}

          <form onSubmit={isRegister ? handleRegister : handleLogin} className="space-y-4">
            {isRegister && (
              <div>
                <label className="text-[11px] font-bold text-[#66635C] uppercase tracking-wider mb-1 block">Full Name</label>
                <input
                  type="text"
                  name="full_name"
                  value={form.full_name}
                  onChange={handleChange}
                  placeholder="e.g. Dr. Rajesh Kumar"
                  className="input text-xs"
                />
              </div>
            )}

            <div>
              <label className="text-[11px] font-bold text-[#66635C] uppercase tracking-wider mb-1 block">Username</label>
              <input
                type="text"
                name="username"
                value={form.username}
                onChange={handleChange}
                placeholder="Enter username"
                required
                className="input text-xs"
              />
            </div>

            {isRegister && (
              <div>
                <label className="text-[11px] font-bold text-[#66635C] uppercase tracking-wider mb-1 block">Email Address</label>
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="you@domain.gov.in"
                  required
                  className="input text-xs"
                />
              </div>
            )}

            <div>
              <label className="text-[11px] font-bold text-[#66635C] uppercase tracking-wider mb-1 block">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="Enter password"
                  required
                  className="input text-xs pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#96938B] hover:text-[#111111]"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-xs font-semibold"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-[#D9A441]" />
                  {isRegister ? 'Creating Account...' : 'Signing in...'}
                </>
              ) : (
                isRegister ? 'Create Account' : 'Sign In'
              )}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-[#E5E2DA] text-center">
            <p className="text-[11px] text-[#96938B] font-medium">
              For Admin Login : username/password = admin/admin123
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
