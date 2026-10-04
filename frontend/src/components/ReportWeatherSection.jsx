import React, { useState } from 'react';
import { Plus, Send, LogIn, Camera, CheckCircle2, Loader2, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useLocationContext } from '../context/LocationContext.jsx';
import { api } from '../services/api.js';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'video/mp4', 'video/webm'];
const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = '.jpg,.jpeg,.png,.webp,.gif,.mp4,.webm';

export default function ReportWeatherSection({ onReportSubmitted }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { selectedLocation } = useLocationContext();
  const isAuthenticated = Boolean(user);

  const [openModal, setOpenModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [fileError, setFileError] = useState('');

  const handleOpenReport = () => {
    if (!isAuthenticated) {
      navigate(`/login?return=${encodeURIComponent('/dashboard')}`);
      return;
    }
    setOpenModal(true);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileError('');
    setError('');

    if (!ALLOWED_TYPES.includes(file.type)) {
      setFileError('Unsupported file type. Upload JPG, PNG, WEBP, GIF, MP4, or WEBM.');
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
      onReportSubmitted?.();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Unable to submit report. Please check details.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="bg-white border border-[#E5E2DA] rounded-xl p-6 sm:p-8 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F7EED7] text-[#A97820] text-xs font-bold border border-[#D9A441]/30">
            <Camera className="w-3.5 h-3.5 text-[#D9A441]" /> CITIZEN REPORTING
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-[#111111] tracking-tight">
            Report a Severe Weather Incident in {selectedLocation.city}
          </h2>
          <p className="text-xs sm:text-sm text-[#66635C] leading-relaxed">
            Help your community by submitting verified weather observations, rainfall levels, or damage reports for {selectedLocation.city}{selectedLocation.state ? `, ${selectedLocation.state}` : ''} directly into our real-time AI ingestion pipeline.
          </p>
        </div>

        <button
          onClick={handleOpenReport}
          className="btn-primary inline-flex items-center justify-center gap-2.5 px-6 py-3.5 text-xs sm:text-sm font-semibold rounded-full shrink-0 cursor-pointer"
        >
          {isAuthenticated ? <Plus className="w-4 h-4 text-[#D9A441]" /> : <LogIn className="w-4 h-4 text-[#D9A441]" />}
          <span>{isAuthenticated ? '+ REPORT WEATHER EVENT' : 'Sign In to Report Event'}</span>
        </button>
      </div>

      {/* Citizen Report Modal */}
      {openModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" role="dialog">
          <div className="bg-white border border-[#E5E2DA] rounded-xl max-w-xl w-full p-6 sm:p-8 shadow-2xl relative">
            <button
              onClick={() => { setOpenModal(false); setSuccess(false); }}
              className="absolute top-5 right-5 p-2 text-[#96938B] hover:text-[#111111] rounded-full bg-[#F7F7F5]"
              aria-label="Close report modal"
            >
              <X className="w-4 h-4" />
            </button>

            {success ? (
              <div className="py-6 text-center">
                <div className="w-12 h-12 rounded-full bg-[#2E7D5B]/10 border border-[#2E7D5B]/20 text-[#2E7D5B] flex items-center justify-center mx-auto mb-3">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-[#111111]">Report Submitted Successfully</h3>
                <p className="text-xs text-[#66635C] mt-1 mb-6">Your report has been sent to our AI fake detection and verification engine.</p>
                <button
                  onClick={() => setSuccess(false)}
                  className="px-5 py-2 bg-[#111111] text-white font-bold rounded-full text-xs"
                >
                  Submit Another Report
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="flex items-center gap-2 mb-2 pb-3 border-b border-[#E5E2DA]">
                  <Send className="w-5 h-5 text-[#D9A441]" />
                  <h3 className="text-base font-bold text-[#111111]">Submit Weather Observation</h3>
                </div>

                {error && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-700 font-medium">
                    {error}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-bold text-[#66635C] uppercase tracking-wider block mb-1">City / Town</label>
                    <input name="city" defaultValue={selectedLocation.city} placeholder="e.g. Vijayawada" className="input text-xs" />
                  </div>
                  <div>
                    <label className="text-[11px] font-bold text-[#66635C] uppercase tracking-wider block mb-1">State</label>
                    <input name="state" defaultValue={selectedLocation.state} placeholder="e.g. Andhra Pradesh" className="input text-xs" />
                  </div>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-[#66635C] uppercase tracking-wider block mb-1">Incident Headline *</label>
                  <input name="title" required placeholder={`e.g. Severe waterlogging near ${selectedLocation.city} main road`} className="input text-xs" />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-[#66635C] uppercase tracking-wider block mb-1">Description *</label>
                  <textarea name="description" required rows={3} placeholder="Describe rainfall intensity, water level, wind speed, damage..." className="input text-xs" />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-[#66635C] uppercase tracking-wider block mb-1">Media Evidence (Optional)</label>
                  {!selectedFile ? (
                    <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-[#E5E2DA] rounded-xl bg-[#F7F7F5] cursor-pointer hover:border-[#D9A441]">
                      <Camera className="w-5 h-5 text-[#96938B] mb-1" />
                      <span className="text-xs font-bold text-[#111111]">Upload Photo or Video</span>
                      <span className="text-[10px] text-[#96938B]">JPG, PNG, WEBP, MP4 (Max 10MB)</span>
                      <input type="file" accept={ALLOWED_EXTENSIONS} onChange={handleFileSelect} className="hidden" />
                    </label>
                  ) : (
                    <div className="flex items-center justify-between p-3 rounded-xl bg-[#F7F7F5] border border-[#E5E2DA]">
                      <span className="text-xs font-bold text-[#111111] truncate max-w-[200px]">{selectedFile.name}</span>
                      <button type="button" onClick={removeFile} className="p-1 text-red-500 hover:bg-red-500/10 rounded-full"><X className="w-4 h-4" /></button>
                    </div>
                  )}
                  {fileError && <p className="text-[11px] text-red-600 mt-1">{fileError}</p>}
                </div>

                <div className="flex justify-end gap-3 pt-3 border-t border-[#E5E2DA]">
                  <button type="button" onClick={() => setOpenModal(false)} className="btn-secondary text-xs">Cancel</button>
                  <button type="submit" disabled={submitting} className="btn-primary text-xs inline-flex items-center gap-2 font-semibold">
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin text-[#D9A441]" /> : <Send className="w-4 h-4 text-[#D9A441]" />}
                    Submit Report
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
