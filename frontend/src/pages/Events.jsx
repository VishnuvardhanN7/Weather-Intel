import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  ChevronLeft, ChevronRight, Download, Plus, LogIn, Send,
  MapPin, FileText, Camera, X, CheckCircle2, AlertTriangle,
  Loader2, Image, FileVideo, Shield, Tag
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import EventTable from '../components/EventTable.jsx';
import FilterPanel from '../components/FilterPanel.jsx';
import { api } from '../services/api.js';
import { useAuth } from '../context/AuthContext.jsx';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'video/mp4', 'video/webm'];
const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = '.jpg,.jpeg,.png,.webp,.gif,.mp4,.webm';

function parse422Detail(detail) {
  if (!detail) return 'Please check the report details and try again.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .filter((d) => d && d.msg)
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc.filter((l) => typeof l === 'string').join(' ') : '';
        const label = field ? field.charAt(0).toUpperCase() + field.slice(1) + ': ' : '';
        return label + d.msg;
      });
    return msgs.length ? msgs.join('; ') : 'Please check the report details and try again.';
  }
  return 'Please check the report details and try again.';
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function CitizenReportForm({ onSuccess }) {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [fileError, setFileError] = useState('');
  const formRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileError('');
    setError('');

    if (!ALLOWED_TYPES.includes(file.type)) {
      setFileError('Unsupported file type. Please upload JPG, PNG, WEBP, GIF, MP4 or WEBM.');
      e.target.value = '';
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setFileError('File is too large. Maximum size is 10 MB.');
      e.target.value = '';
      return;
    }

    setSelectedFile(file);
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setFileError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setSuccess(false);

    const formData = new FormData(e.currentTarget);

    if (selectedFile) {
      formData.set('files', selectedFile);
    } else {
      formData.delete('files');
    }

    try {
      await api.post('/api/weather/citizen-report', formData);
      setSuccess(true);
      removeFile();
      formRef.current?.reset();
      onSuccess?.();
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      if (status === 401) {
        setError('Your session has expired. Please sign in again.');
      } else if (status === 413) {
        setError('The selected file is too large.');
      } else if (status === 415) {
        setError(detail || 'Unsupported file type.');
      } else if (status === 422) {
        setError(parse422Detail(detail));
      } else {
        setError(detail || 'Unable to submit report.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  if (success) {
    return (
      <div className="card border-emerald-500/30 bg-white dark:bg-[#0e1017]">
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/20">
            <CheckCircle2 className="h-7 w-7 text-emerald-600 dark:text-emerald-400" />
          </div>
          <h3 className="text-xl font-bold text-stone-900 dark:text-white mb-2">Report Submitted Successfully</h3>
          <p className="text-xs text-stone-600 dark:text-stone-400 max-w-md mb-4 leading-relaxed">
            Your weather observation has been ingested into the system and sent for automated AI verification.
          </p>
          <button onClick={() => setSuccess(false)} className="mt-4 btn-primary">
            Submit Another Observation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card bg-white dark:bg-[#13151f] border border-stone-200 dark:border-stone-800 shadow-sm dark:shadow-editorial p-6 sm:p-8">
      <form ref={formRef} onSubmit={handleSubmit} noValidate>
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-stone-200 dark:border-stone-800">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#D9A441]/10 border border-[#D9A441]/20 text-[#D9A441]">
            <Send className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-stone-900 dark:text-white tracking-tight">Citizen Weather Observation Report</h2>
            <p className="text-xs text-stone-600 dark:text-stone-400">Contribute severe weather observations from your local area</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 flex items-start gap-3 rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3" role="alert">
            <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-red-700 dark:text-red-300 font-medium">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="report-city" className="block text-xs font-bold text-stone-600 dark:text-stone-400 uppercase tracking-wider mb-1.5">
                City / Town
              </label>
              <input
                id="report-city"
                name="city"
                className="input text-xs"
                placeholder="e.g. Visakhapatnam"
              />
            </div>
            <div>
              <label htmlFor="report-state" className="block text-xs font-bold text-stone-600 dark:text-stone-400 uppercase tracking-wider mb-1.5">
                State
              </label>
              <input
                id="report-state"
                name="state"
                className="input text-xs"
                placeholder="e.g. Andhra Pradesh"
              />
            </div>
          </div>

          <div>
            <label htmlFor="report-title" className="block text-xs font-bold text-stone-600 dark:text-stone-400 uppercase tracking-wider mb-1.5">
              Incident Headline <span className="text-red-500">*</span>
            </label>
            <input
              id="report-title"
              name="title"
              required
              minLength={5}
              maxLength={500}
              className="input text-xs"
              placeholder="e.g. Severe downpour and localized urban flooding"
            />
          </div>

          <div>
            <label htmlFor="report-description" className="block text-xs font-bold text-stone-600 dark:text-stone-400 uppercase tracking-wider mb-1.5">
              Detailed Description <span className="text-red-500">*</span>
            </label>
            <textarea
              id="report-description"
              name="description"
              required
              minLength={10}
              className="input min-h-[110px] text-xs leading-relaxed"
              placeholder="Describe weather severity, wind intensity, water levels, visibility, and damage..."
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-stone-600 dark:text-stone-400 uppercase tracking-wider mb-1.5">
              Media Evidence <span className="text-stone-500 font-normal">(Optional)</span>
            </label>

            {!selectedFile ? (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-stone-300 dark:border-stone-800 bg-stone-50 dark:bg-[#0e1017] px-6 py-7 text-center transition-colors hover:border-stone-400 dark:hover:border-stone-700 cursor-pointer"
              >
                <Camera className="h-7 w-7 text-stone-400 dark:text-stone-500 mb-2" />
                <p className="text-xs text-stone-800 dark:text-stone-200 font-bold">Upload Photos or Video</p>
                <p className="text-[11px] text-stone-500 mt-1">JPG, PNG, WEBP, GIF, MP4, WEBM (Max 10 MB)</p>
              </button>
            ) : (
              <div className="flex items-center gap-4 rounded-2xl border border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#0e1017] px-4 py-3">
                {previewUrl ? (
                  <img src={previewUrl} alt="Evidence preview" className="h-14 w-14 rounded-xl object-cover border border-stone-200 dark:border-stone-800" />
                ) : (
                  <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-stone-200 dark:bg-stone-800">
                    <FileVideo className="h-6 w-6 text-stone-600 dark:text-stone-400" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-stone-900 dark:text-white truncate">{selectedFile.name}</p>
                  <p className="text-[11px] text-stone-500 dark:text-stone-400">{formatFileSize(selectedFile.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  className="p-1.5 rounded-full text-stone-500 dark:text-stone-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-stone-200 dark:hover:bg-stone-800 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
            {fileError && <p className="mt-2 text-xs text-red-600 dark:text-red-400 font-medium">{fileError}</p>}
            <input
              ref={fileInputRef}
              type="file"
              name="files"
              accept={ALLOWED_EXTENSIONS}
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-stone-200 dark:border-stone-800">
          <button type="submit" disabled={submitting} className="btn-primary inline-flex items-center gap-2 text-xs py-2.5">
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Submitting Report...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" /> Submit Report
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function Events() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const isAuthenticated = Boolean(user);
  const isAdmin = user?.role === 'admin';

  const initialSourceFilter = searchParams.get('source') || '';

  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({ page: 1, per_page: 20, total: 0, total_pages: 0 });
  const [filters, setFilters] = useState({
    event_type: '', severity: '', state: '', city: '',
    verification_status: '', source: initialSourceFilter, start_date: '', end_date: '', search: '',
  });
  const [showReportForm, setShowReportForm] = useState(false);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', pagination.page);
      params.append('per_page', pagination.per_page);
      Object.entries(filters).forEach(([key, val]) => {
        if (val) params.append(key, val);
      });
      const response = await api.get(`/api/weather?${params.toString()}`);
      setEvents(response.data.data);
      setPagination(response.data.pagination);
    } catch (err) {
      console.error('Error fetching events:', err);
    }
    setLoading(false);
  }, [pagination.page, pagination.per_page, filters]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setPagination(p => ({ ...p, page: 1 }));
  };

  const handleFilterReset = () => {
    setFilters({
      event_type: '', severity: '', state: '', city: '',
      verification_status: '', source: '', start_date: '', end_date: '', search: '',
    });
    setPagination(p => ({ ...p, page: 1 }));
  };

  const handleVerify = async (eventId, status) => {
    try {
      await api.post(`/api/weather/${eventId}/verify`, { verification_status: status });
      fetchEvents();
    } catch (err) {
      console.error('Verification error:', err);
    }
  };

  const handlePageChange = (newPage) => {
    setPagination(p => ({ ...p, page: newPage }));
  };

  const handleExport = () => {
    const csvHeaders = ['ID', 'Title', 'Type', 'Severity', 'City', 'State', 'Source', 'Status', 'Reported At'];
    const rows = events.map(e => [
      e.id, `"${e.title}"`, e.event_type, e.severity, e.city || '', e.state || '',
      e.source, e.verification_status, e.reported_at,
    ]);
    const csvContent = [csvHeaders.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `weather_events_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleReportClick = () => {
    if (!isAuthenticated) {
      navigate(`/login?return=${encodeURIComponent('/events')}`);
      return;
    }
    setShowReportForm((v) => !v);
  };

  const handleViewIntelligence = (eventId) => {
    navigate(`/events/${eventId}/intelligence`);
  };

  return (
    <div className="space-y-8" role="main" aria-label="Weather Events">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-stone-200 dark:border-stone-800/80">
        <div>
          <h1 className="text-2xl sm:text-3xl lg:text-[34px] font-extrabold text-stone-900 dark:text-[#faf9f6] tracking-tight">
            Weather Events
          </h1>
          <p className="text-[13px] text-stone-600 dark:text-stone-400 mt-1.5 font-normal max-w-2xl leading-relaxed">
            Browse and investigate weather events
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button onClick={handleReportClick} className="btn-primary inline-flex items-center gap-2 text-xs py-2 px-4">
            {isAuthenticated ? <Plus className="w-3.5 h-3.5 text-white dark:text-[#0f1016]" /> : <LogIn className="w-3.5 h-3.5 text-white dark:text-[#0f1016]" />}
            <span>{isAuthenticated ? 'Report Weather Incident' : 'Sign in to Report'}</span>
          </button>
          <button onClick={handleExport} className="btn-secondary inline-flex items-center gap-2 text-xs py-2 px-4">
            <Download className="w-3.5 h-3.5 text-stone-600 dark:text-stone-300" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {showReportForm && <CitizenReportForm onSuccess={fetchEvents} />}

      <FilterPanel filters={filters} onFilterChange={handleFilterChange} onReset={handleFilterReset} />

      <EventTable
        events={events}
        onVerify={isAdmin ? handleVerify : undefined}
        onViewIntelligence={handleViewIntelligence}
        loading={loading}
      />

      {pagination.total_pages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
          <p className="text-xs text-stone-600 dark:text-stone-400 font-medium">
            Showing {(pagination.page - 1) * pagination.per_page + 1} to{' '}
            {Math.min(pagination.page * pagination.per_page, pagination.total)} of {pagination.total} events
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="btn-secondary p-2 disabled:opacity-30 rounded-full"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            {Array.from({ length: Math.min(pagination.total_pages, 5) }, (_, i) => {
              let pageNum;
              if (pagination.total_pages <= 5) pageNum = i + 1;
              else if (pagination.page <= 3) pageNum = i + 1;
              else if (pagination.page >= pagination.total_pages - 2) pageNum = pagination.total_pages - 4 + i;
              else pageNum = pagination.page - 2 + i;

              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={`w-8 h-8 rounded-full text-xs font-bold transition-all ${
                    pagination.page === pageNum
                      ? 'bg-[#14161f] text-white dark:bg-[#faf9f6] dark:text-[#0f1016]'
                      : 'bg-white text-stone-700 dark:bg-[#141620] dark:text-stone-400 hover:bg-stone-100 dark:hover:text-white border border-stone-200 dark:border-stone-800'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
            <button
              onClick={() => handlePageChange(pagination.page + 1)}
              disabled={pagination.page >= pagination.total_pages}
              className="btn-secondary p-2 disabled:opacity-30 rounded-full"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}