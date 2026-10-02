import React, { useState } from 'react';
import { FieldReport, Region } from '../types';
import { MapPin, Camera, ThumbsUp, Flag, Send, Compass } from 'lucide-react';
import { api } from '../services/api';

interface FieldReportsViewProps {
  reports: FieldReport[];
  selectedRegion: Region | null;
  onReportSubmitted: () => void;
}

export const FieldReportsView: React.FC<FieldReportsViewProps> = ({
  reports,
  selectedRegion,
  onReportSubmitted,
}) => {
  const [postType, setPostType] = useState<FieldReport['post_type']>('fire_report');
  const [lat, setLat] = useState<string>(selectedRegion ? String(selectedRegion.center[0]) : '15.20');
  const [lon, setLon] = useState<string>(selectedRegion ? String(selectedRegion.center[1]) : '76.66');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;

    setIsSubmitting(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      await api.submitFieldReport(selectedRegion?.event_id || 2, {
        post_type: postType,
        lat: parseFloat(lat),
        lon: parseFloat(lon),
        description: description.trim(),
      });
      setDescription('');
      setSuccessMsg('Field report submitted and registered into surveillance stream.');
      onReportSubmitted();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit report');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Form Column */}
      <div className="lg:col-span-1 industrial-card p-5 space-y-4">
        <div className="border-b border-[#1E293B] pb-3">
          <h2 className="text-xs font-bold text-white uppercase font-mono tracking-wider">
            Submit Ground Observation
          </h2>
          <p className="text-[11px] text-[#94A3B8] mt-1">
            Contribute on-ground thermal confirmation, smoke sighting, or emergency help request.
          </p>
        </div>

        {successMsg && (
          <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs">
            {successMsg}
          </div>
        )}

        {errorMsg && (
          <div className="p-2.5 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          <div>
            <label className="text-[11px] font-mono text-[#64748B] block mb-1 uppercase">
              Incident Type
            </label>
            <select
              value={postType}
              onChange={(e) => setPostType(e.target.value as any)}
              className="w-full bg-[#0D131F] border border-[#2A374D] text-white p-2 rounded focus:outline-none focus:border-[#F59E0B]"
            >
              <option value="fire_report">Direct Fire Observation</option>
              <option value="info">General Environmental Info</option>
              <option value="request_help">Request Emergency Assistance</option>
              <option value="offer_help">Offer Logistics / Water Tender</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2 font-mono">
            <div>
              <label className="text-[10px] text-[#64748B] block mb-1 uppercase">
                Latitude (°N)
              </label>
              <input
                type="number"
                step="0.0001"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                required
                className="w-full bg-[#0D131F] border border-[#2A374D] text-white p-2 rounded focus:outline-none focus:border-[#F59E0B]"
              />
            </div>
            <div>
              <label className="text-[10px] text-[#64748B] block mb-1 uppercase">
                Longitude (°E)
              </label>
              <input
                type="number"
                step="0.0001"
                value={lon}
                onChange={(e) => setLon(e.target.value)}
                required
                className="w-full bg-[#0D131F] border border-[#2A374D] text-white p-2 rounded focus:outline-none focus:border-[#F59E0B]"
              />
            </div>
          </div>

          <div>
            <label className="text-[11px] font-mono text-[#64748B] block mb-1 uppercase">
              Observation Details
            </label>
            <textarea
              rows={3}
              placeholder="Describe smoke color, flame height, affected facility or perimeter boundary..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              className="w-full bg-[#0D131F] border border-[#2A374D] text-white p-2 rounded focus:outline-none focus:border-[#F59E0B] resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex items-center justify-center gap-2 bg-[#F59E0B] hover:bg-[#D97706] disabled:opacity-50 text-black font-semibold py-2 rounded transition-colors text-xs"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{isSubmitting ? 'Transmitting...' : 'Submit Incident Report'}</span>
          </button>
        </form>
      </div>

      {/* Reports Feed Column */}
      <div className="lg:col-span-2 industrial-card p-5 space-y-4">
        <div className="border-b border-[#1E293B] pb-3 flex justify-between items-center">
          <div>
            <h2 className="text-xs font-bold text-white uppercase font-mono tracking-wider">
              Active Ground Incident Reports
            </h2>
            <p className="text-[11px] text-[#94A3B8]">
              Verified field observations synchronized with satellite passes.
            </p>
          </div>
          <span className="font-mono text-xs font-bold text-[#F59E0B]">
            {reports.length} reports
          </span>
        </div>

        <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
          {reports.map((report) => (
            <div
              key={report.id}
              className="p-3.5 rounded bg-[#0D131F] border border-[#1E293B] hover:border-[#2A374D] transition-colors space-y-2"
            >
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  <span
                    className={`badge ${
                      report.post_type === 'fire_report'
                        ? 'badge-critical'
                        : report.post_type === 'request_help'
                        ? 'badge-high'
                        : 'badge-gold'
                    }`}
                  >
                    {(report.post_type || 'observation').replace(/_/g, ' ')}
                  </span>
                  <span className="text-[10px] font-mono text-[#64748B]">
                    Report #{report.id}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-[#64748B]">
                  {report.created_at ? new Date(report.created_at).toLocaleString() : 'Just now'}
                </span>
              </div>

              <p className="text-xs text-[#E2E8F0] leading-normal">{report.description}</p>

              <div className="flex justify-between items-center text-[10px] font-mono text-[#64748B] pt-2 border-t border-[#1E293B]/60">
                <span className="flex items-center gap-1 text-[#94A3B8]">
                  <MapPin className="w-3 h-3 text-[#F59E0B]" />
                  {report.lat.toFixed(4)}°N, {report.lon.toFixed(4)}°E
                </span>
                {report.bearing !== null && report.bearing !== undefined && (
                  <span className="flex items-center gap-1 text-[#F59E0B]">
                    <Compass className="w-3 h-3" />
                    Bearing: {report.bearing}°
                  </span>
                )}
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1 text-[#94A3B8]">
                    <ThumbsUp className="w-3 h-3" /> {report.like_count}
                  </span>
                </div>
              </div>
            </div>
          ))}

          {reports.length === 0 && (
            <div className="text-center py-12 text-[#64748B] text-xs">
              No field reports currently recorded for this surveillance window.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
