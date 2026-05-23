'use client';
import { useEffect, useState } from 'react';
import Shell from '@/components/layout/Shell';
import { TransactionsDashboard } from '@/components/phase2/frontend_components';
import { api } from '@/lib/api';

const IEC = 'AXGPK0287Q';

function fmt(n: number | null | undefined) {
  if (n == null) return '—';
  return '$' + Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function dateKeyToStr(key: string | null | undefined) {
  if (!key) return '—';
  const s = String(key);
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
}

export default function MyExportsPage() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    api().get(`exporters/by-iec/${IEC}`)
      .then(r => setProfile(r.data))
      .catch(e => { if (e.response?.status === 404) setMissing(true); })
      .finally(() => setLoading(false));
  }, []);

  return (
    <Shell>
      <div className="p-6 max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold">My Exports</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Shipments for IEC <span className="font-mono font-semibold">{IEC}</span>
          </p>
        </div>

        {/* Profile card */}
        {loading && <div className="text-gray-400 text-sm mb-6">Loading profile…</div>}

        {missing && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 text-sm text-amber-800">
            No exporter profile found for IEC <strong>{IEC}</strong> in the transactions database.
            This will be populated once real DGFT eBRC data is loaded via the NIRYAT pipeline.
          </div>
        )}

        {profile && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
            {/* Company info */}
            <div className="lg:col-span-2 bg-white border rounded-lg p-5">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-semibold">{profile.company_name}</h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    IEC: <span className="font-mono">{profile.iec_code}</span>
                    {profile.is_active && (
                      <span className="ml-2 bg-green-50 text-green-700 text-xs px-2 py-0.5 rounded-full">Active</span>
                    )}
                  </p>
                  {(profile.city || profile.state_code) && (
                    <p className="text-sm text-gray-600 mt-1">
                      📍 {[profile.city, profile.state_code].filter(Boolean).join(', ')}
                    </p>
                  )}
                  {profile.address && (
                    <p className="text-sm text-gray-500 mt-1">{profile.address}</p>
                  )}
                </div>
                <div className="text-right text-sm text-gray-500">
                  {profile.phone && <p>📞 {profile.phone}</p>}
                  {profile.email && <p>✉ {profile.email}</p>}
                </div>
              </div>
            </div>

            {/* KPI summary */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Transactions</p>
                <p className="text-2xl font-bold text-blue-700">{profile.transaction_count}</p>
              </div>
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Total Value</p>
                <p className="text-xl font-bold text-green-700">{fmt(profile.total_value_usd)}</p>
              </div>
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">First Export</p>
                <p className="text-sm font-semibold">{dateKeyToStr(profile.first_export_date)}</p>
              </div>
              <div className="bg-white border rounded-lg p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">Latest Export</p>
                <p className="text-sm font-semibold">{dateKeyToStr(profile.last_export_date)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Transactions table — reuse with IEC filter */}
        <TransactionsDashboard iecCode={IEC} title="My Shipments" />
      </div>
    </Shell>
  );
}
