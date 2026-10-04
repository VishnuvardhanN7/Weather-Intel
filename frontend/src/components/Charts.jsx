import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, ResponsiveContainer,
  AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';
import { useTheme } from '../context/ThemeContext.jsx';

// ATMOS restrained gold, charcoal & semantic palette
const WEATHER_COLORS = ['#D9A441', '#A97820', '#111111', '#66635C', '#2E7D5B', '#E2B84A', '#8C6627', '#44403C'];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white dark:bg-[#141620] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-3 shadow-subtle">
      <p className="text-xs font-bold text-[#111111] dark:text-stone-200 mb-1">{label}</p>
      {payload.map((item, idx) => (
        <p key={idx} className="text-xs font-medium" style={{ color: item.color }}>
          {item.name}: <span className="font-bold">{item.value}</span>
        </p>
      ))}
    </div>
  );
};

export function EventsByTypeBarChart({ data = [] }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#262838' : '#E5E2DA';
  const tickColor = isDark ? '#a1a1aa' : '#66635C';

  return (
    <div className="card-editorial">
      <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">Events by Type</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="event_type" tick={{ fill: tickColor, fontSize: 11 }} />
          <YAxis tick={{ fill: tickColor, fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" name="Events" radius={[6, 6, 0, 0]}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={WEATHER_COLORS[idx % WEATHER_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function EventsOverTimeChart({ data = [] }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#262838' : '#E5E2DA';
  const tickColor = isDark ? '#a1a1aa' : '#66635C';

  return (
    <div className="card-editorial">
      <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">Events Timeline</h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#D9A441" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#D9A441" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="date" tick={{ fill: tickColor, fontSize: 11 }} />
          <YAxis tick={{ fill: tickColor, fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#D9A441"
            strokeWidth={2.5}
            fillOpacity={1}
            fill="url(#colorCount)"
            name="Events"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function EventsByStatePieChart({ data = [] }) {
  const chartData = data.slice(0, 8);
  return (
    <div className="card-editorial">
      <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">Top Affected States</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            outerRadius={100}
            innerRadius={55}
            paddingAngle={4}
            dataKey="count"
            nameKey="state"
          >
            {chartData.map((entry, idx) => (
              <Cell key={idx} fill={WEATHER_COLORS[idx % WEATHER_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => <span className="text-[#66635C] dark:text-stone-300 text-xs font-medium">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SeverityDistributionChart({ data = [] }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#262838' : '#E5E2DA';
  const tickColor = isDark ? '#a1a1aa' : '#66635C';

  return (
    <div className="card-editorial">
      <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">Severity Breakdown</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} layout="vertical" margin={{ top: 10, right: 20, left: 40, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis type="number" tick={{ fill: tickColor, fontSize: 11 }} />
          <YAxis
            dataKey="severity"
            type="category"
            tick={{ fill: tickColor, fontSize: 11 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" name="Events" radius={[0, 6, 6, 0]}>
            {data.map((entry, idx) => {
              const colorMap = { low: '#2E7D5B', moderate: '#D9A441', high: '#E2B84A', critical: '#DC2626' };
              return <Cell key={idx} fill={colorMap[entry.severity] || WEATHER_COLORS[idx % WEATHER_COLORS.length]} />;
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function VerificationStatsChart({ data = [] }) {
  return (
    <div className="card-editorial">
      <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">Verification Status Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={100}
            innerRadius={60}
            paddingAngle={4}
            dataKey="count"
            nameKey="verification_status"
          >
            {data.map((entry, idx) => {
              const colorMap = {
                pending: '#D9A441',
                verified: '#2E7D5B',
                rejected: '#DC2626',
                needs_review: '#E2B84A'
              };
              return <Cell key={idx} fill={colorMap[entry.verification_status] || WEATHER_COLORS[idx % WEATHER_COLORS.length]} />;
            })}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => <span className="text-[#66635C] dark:text-stone-300 text-xs font-medium capitalize">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SourceBreakdownChart({ data = [] }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#262838' : '#E5E2DA';
  const tickColor = isDark ? '#a1a1aa' : '#66635C';

  return (
    <div className="card-editorial">
      <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">Ingestion Data Sources</h3>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid stroke={gridColor} />
          <PolarAngleAxis dataKey="source" tick={{ fill: tickColor, fontSize: 11 }} />
          <PolarRadiusAxis tick={{ fill: isDark ? '#71717a' : '#96938B', fontSize: 10 }} />
          <Radar
            name="Events"
            dataKey="count"
            stroke="#D9A441"
            fill="#D9A441"
            fillOpacity={0.25}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SourceLatencyChart({ data = [] }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#262838' : '#E5E2DA';
  const tickColor = isDark ? '#a1a1aa' : '#66635C';

  return (
    <div className="card-editorial">
      <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">Average Latency by Source (ms)</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 10 }} interval={0} angle={-25} textAnchor="end" />
          <YAxis tick={{ fill: tickColor, fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="latency" name="Latency (ms)" fill="#D9A441" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SourceVerifiedVSRejectedChart({ data = [] }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#262838' : '#E5E2DA';
  const tickColor = isDark ? '#a1a1aa' : '#66635C';

  return (
    <div className="card-editorial">
      <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">Verified vs Rejected by Source</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 10 }} interval={0} angle={-25} textAnchor="end" />
          <YAxis tick={{ fill: tickColor, fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar dataKey="verified" name="Verified" fill="#2E7D5B" radius={[4, 4, 0, 0]} />
          <Bar dataKey="rejected" name="Rejected" fill="#DC2626" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SourceMediaChart({ data = [] }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#262838' : '#E5E2DA';
  const tickColor = isDark ? '#a1a1aa' : '#66635C';

  return (
    <div className="card-editorial">
      <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">Media Collected by Source</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 10 }} interval={0} angle={-25} textAnchor="end" />
          <YAxis tick={{ fill: tickColor, fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="media_count" name="Media Items" fill="#A97820" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

