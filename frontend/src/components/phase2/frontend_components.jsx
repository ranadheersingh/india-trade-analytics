import React, { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ============================================================================
// SHARED UTILITIES
// ============================================================================

const PAGE_SIZES = [25, 50, 100];

function fmt(n) {
  if (n == null) return '—';
  return '$' + Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function dateKeyToStr(key) {
  if (!key) return '—';
  const s = String(key);
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
}

function Pagination({ page, limit, total, onPage, onLimit }) {
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const from = total === 0 ? 0 : (page - 1) * limit + 1;
  const to = Math.min(page * limit, total);

  return (
    <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
      <span>
        {total === 0 ? 'No records' : `Showing ${from}–${to} of ${total.toLocaleString()} records`}
      </span>
      <div className="flex items-center gap-3">
        <span className="text-gray-500">Rows:</span>
        <select
          value={limit}
          onChange={e => onLimit(Number(e.target.value))}
          className="border rounded px-2 py-1 text-sm"
        >
          {PAGE_SIZES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button
          onClick={() => onPage(1)}
          disabled={page === 1}
          className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-100"
        >«</button>
        <button
          onClick={() => onPage(page - 1)}
          disabled={page === 1}
          className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-100"
        >‹</button>
        <span className="px-2">Page {page} / {totalPages}</span>
        <button
          onClick={() => onPage(page + 1)}
          disabled={page >= totalPages}
          className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-100"
        >›</button>
        <button
          onClick={() => onPage(totalPages)}
          disabled={page >= totalPages}
          className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-100"
        >»</button>
      </div>
    </div>
  );
}

function downloadCsv(items, filename) {
  if (!items.length) return;
  const cols = Object.keys(items[0]);
  const rows = [cols.join(','), ...items.map(r =>
    cols.map(c => {
      const v = r[c] ?? '';
      return String(v).includes(',') ? `"${v}"` : v;
    }).join(',')
  )];
  const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function FilterBar({ filters, onChange, countries, hsCodes, statusOptions, label }) {
  return (
    <div className="bg-white border rounded-lg p-4 mb-4">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">From Date</label>
          <input
            type="date"
            value={filters.date_from}
            onChange={e => onChange({ ...filters, date_from: e.target.value })}
            className="w-full border rounded px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">To Date</label>
          <input
            type="date"
            value={filters.date_to}
            onChange={e => onChange({ ...filters, date_to: e.target.value })}
            className="w-full border rounded px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">{label || 'Country'}</label>
          <select
            value={filters.country_iso}
            onChange={e => onChange({ ...filters, country_iso: e.target.value })}
            className="w-full border rounded px-2 py-1.5 text-sm"
          >
            <option value="">All countries</option>
            {countries.map(c => (
              <option key={c.iso_alpha_3} value={c.iso_alpha_3}>{c.country_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">HS Chapter</label>
          <select
            value={filters.hs_code}
            onChange={e => onChange({ ...filters, hs_code: e.target.value })}
            className="w-full border rounded px-2 py-1.5 text-sm"
          >
            <option value="">All HS chapters</option>
            {hsCodes.map(h => (
              <option key={h.hs_code} value={h.hs_code}>{h.hs_code} — {h.description?.slice(0, 40)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
          <select
            value={filters.status}
            onChange={e => onChange({ ...filters, status: e.target.value })}
            className="w-full border rounded px-2 py-1.5 text-sm"
          >
            <option value="">All statuses</option>
            {statusOptions.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>
      <button
        onClick={() => onChange({ date_from: '', date_to: '', country_iso: '', hs_code: '', status: '' })}
        className="mt-3 text-xs text-gray-500 hover:text-gray-700 underline"
      >
        Clear filters
      </button>
    </div>
  );
}

// ============================================================================
// TRANSACTIONS DASHBOARD (EXPORTS)
// ============================================================================

const EMPTY_FILTERS = { date_from: '', date_to: '', country_iso: '', hs_code: '', status: '' };

export const TransactionsDashboard = ({ iecCode, title } = {}) => {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(50);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [countries, setCountries] = useState([]);
  const [hsCodes, setHsCodes] = useState([]);

  useEffect(() => {
    api().get('meta/countries?limit=500').then(r => setCountries(r.data)).catch(() => {});
    api().get('meta/hs?level=2&limit=200').then(r => setHsCodes(r.data)).catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, limit };
      if (iecCode) params.iec_code = iecCode;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      if (filters.country_iso) params.country_iso = filters.country_iso;
      if (filters.hs_code) params.hs_code = filters.hs_code;
      if (filters.status) params.status = filters.status;
      const { data } = await api().get('transactions/exports', { params });
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    } finally {
      setLoading(false);
    }
  }, [page, limit, filters, iecCode]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleFilters = (f) => { setFilters(f); setPage(1); };
  const handleLimit = (l) => { setLimit(l); setPage(1); };

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">{title || 'Export Transactions'}</h1>
          <p className="text-sm text-gray-500 mt-0.5">Shipment-level export records</p>
        </div>
        <div className="flex items-center gap-3">
          {loading && <span className="text-sm text-gray-400 animate-pulse">Loading…</span>}
          <button
            onClick={() => downloadCsv(items, 'export-transactions.csv')}
            disabled={!items.length}
            className="flex items-center gap-1.5 text-sm border rounded px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40"
          >
            ↓ CSV
          </button>
        </div>
      </div>

      <FilterBar
        filters={filters}
        onChange={handleFilters}
        countries={countries}
        hsCodes={hsCodes}
        statusOptions={['completed', 'in_transit', 'pending', 'cancelled']}
        label="Destination"
      />

      <div className="overflow-x-auto bg-white border rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Transaction ID</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Date</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Exporter</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Destination</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">HS Code</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Product</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Value USD</th>
              <th className="px-4 py-3 text-center font-medium text-gray-600">Mode</th>
              <th className="px-4 py-3 text-center font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={9} className="text-center py-10 text-gray-400">No transactions found</td>
              </tr>
            )}
            {items.map((tx) => (
              <tr key={tx.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{tx.transaction_id}</td>
                <td className="px-4 py-2 text-gray-600">{dateKeyToStr(tx.export_date_key)}</td>
                <td className="px-4 py-2">
                  <div className="font-medium">{tx.exporter_name}</div>
                  <div className="text-xs text-gray-400">{tx.iec_code}</div>
                </td>
                <td className="px-4 py-2">
                  <span className="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded mr-1">{tx.iso_alpha_3}</span>
                  {tx.destination_country}
                </td>
                <td className="px-4 py-2 font-mono text-xs">{tx.hs_code}</td>
                <td className="px-4 py-2 text-gray-600 max-w-[200px] truncate">{tx.hs_description}</td>
                <td className="px-4 py-2 text-right font-medium">{fmt(tx.value_usd)}</td>
                <td className="px-4 py-2 text-center">
                  <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                    {tx.transport_mode_name}
                  </span>
                </td>
                <td className="px-4 py-2 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    tx.shipment_status === 'completed'
                      ? 'bg-green-50 text-green-700'
                      : tx.shipment_status === 'in_transit'
                      ? 'bg-yellow-50 text-yellow-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {tx.shipment_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} limit={limit} total={total} onPage={setPage} onLimit={handleLimit} />
    </div>
  );
};

// ============================================================================
// IMPORT TRANSACTIONS DASHBOARD
// ============================================================================

export const ImportTransactionsDashboard = () => {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(50);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [countries, setCountries] = useState([]);
  const [hsCodes, setHsCodes] = useState([]);

  useEffect(() => {
    api().get('meta/countries?limit=500').then(r => setCountries(r.data)).catch(() => {});
    api().get('meta/hs?level=2&limit=200').then(r => setHsCodes(r.data)).catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, limit };
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      if (filters.country_iso) params.country_iso = filters.country_iso;
      if (filters.hs_code) params.hs_code = filters.hs_code;
      if (filters.status) params.status = filters.status;
      const { data } = await api().get('transactions/imports', { params });
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      console.error('Failed to fetch import transactions:', err);
    } finally {
      setLoading(false);
    }
  }, [page, limit, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleFilters = (f) => { setFilters(f); setPage(1); };
  const handleLimit = (l) => { setLimit(l); setPage(1); };

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Import Transactions</h1>
          <p className="text-sm text-gray-500 mt-0.5">Shipment-level import records</p>
        </div>
        <div className="flex items-center gap-3">
          {loading && <span className="text-sm text-gray-400 animate-pulse">Loading…</span>}
          <button
            onClick={() => downloadCsv(items, 'import-transactions.csv')}
            disabled={!items.length}
            className="flex items-center gap-1.5 text-sm border rounded px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40"
          >
            ↓ CSV
          </button>
        </div>
      </div>

      <FilterBar
        filters={filters}
        onChange={handleFilters}
        countries={countries}
        hsCodes={hsCodes}
        statusOptions={['completed', 'in_transit', 'pending', 'cancelled']}
        label="Origin Country"
      />

      <div className="overflow-x-auto bg-white border rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Transaction ID</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Date</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Importer</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Origin</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">HS Code</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Product</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Value USD</th>
              <th className="px-4 py-3 text-center font-medium text-gray-600">Mode</th>
              <th className="px-4 py-3 text-center font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={9} className="text-center py-10 text-gray-400">No import transactions found</td>
              </tr>
            )}
            {items.map((tx) => (
              <tr key={tx.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{tx.transaction_id}</td>
                <td className="px-4 py-2 text-gray-600">{dateKeyToStr(tx.import_date_key)}</td>
                <td className="px-4 py-2 font-medium">{tx.importer_name}</td>
                <td className="px-4 py-2">
                  <span className="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded mr-1">{tx.iso_alpha_3}</span>
                  {tx.origin_country}
                </td>
                <td className="px-4 py-2 font-mono text-xs">{tx.hs_code}</td>
                <td className="px-4 py-2 text-gray-600 max-w-[200px] truncate">{tx.hs_description}</td>
                <td className="px-4 py-2 text-right font-medium">{fmt(tx.value_usd)}</td>
                <td className="px-4 py-2 text-center">
                  <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                    {tx.transport_mode_name}
                  </span>
                </td>
                <td className="px-4 py-2 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    tx.shipment_status === 'completed'
                      ? 'bg-green-50 text-green-700'
                      : tx.shipment_status === 'in_transit'
                      ? 'bg-yellow-50 text-yellow-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {tx.shipment_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} limit={limit} total={total} onPage={setPage} onLimit={handleLimit} />
    </div>
  );
};

// ============================================================================
// EXPORTERS DASHBOARD
// ============================================================================

export const ExportersDashboard = () => {
  const [exporters, setExporters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api().get('exporters').then(r => setExporters(r.data)).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6">Loading exporters...</div>;

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <h1 className="text-2xl font-bold mb-6">Indian Exporters Directory</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {exporters.map((exporter) => (
          <div key={exporter.exporter_key} className="bg-white border rounded-lg p-6 shadow-sm">
            <h3 className="text-lg font-semibold mb-2">{exporter.company_name}</h3>
            <p className="text-gray-600 mb-1 text-sm">IEC: {exporter.iec_code}</p>
            {exporter.city && (
              <p className="text-gray-600 mb-1 text-sm">Location: {exporter.city}, {exporter.state_code}</p>
            )}
            <p className="text-gray-600 mb-2 text-sm">Transactions: {exporter.transaction_count || 0}</p>
            <p className="text-lg font-bold text-green-600">
              {fmt(exporter.total_value_usd)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// ANALYTICS DASHBOARD
// ============================================================================

export const AnalyticsDashboard = () => {
  const [summary, setSummary] = useState({});
  const [transportModes, setTransportModes] = useState([]);
  const [topDestinations, setTopDestinations] = useState([]);
  const [topHsCodes, setTopHsCodes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api().get('analytics/summary'),
      api().get('analytics/by-transport-mode'),
      api().get('destinations'),
      api().get('analytics/by-hs-code'),
    ]).then(([s, t, d, h]) => {
      setSummary(s.data);
      setTransportModes(t.data);
      setTopDestinations(d.data);
      setTopHsCodes(h.data);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6">Loading analytics...</div>;

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <h1 className="text-2xl font-bold mb-6">Trade Analytics Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: 'Export Transactions', value: summary.export_transactions?.toLocaleString() || 0 },
          { label: 'Export Value', value: fmt(summary.export_value_usd) },
          { label: 'Active Exporters', value: summary.active_exporters || 0 },
          { label: 'Top Destination', value: topDestinations[0]?.country_name || 'N/A' },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-sm font-medium text-gray-500">{label}</h3>
            <p className="text-2xl font-bold mt-1">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">Exports by Transport Mode</h2>
          <div className="space-y-3">
            {transportModes.map((mode) => (
              <div key={mode.transport_mode_name} className="flex items-center justify-between">
                <span className="text-gray-700">{mode.transport_mode_name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">{mode.transaction_count} txns</span>
                  <span className="font-semibold">{fmt(mode.total_value_usd)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">Top Export Destinations</h2>
          <div className="space-y-3">
            {topDestinations.slice(0, 8).map((dest) => (
              <div key={dest.iso_alpha_3} className="flex items-center justify-between">
                <span className="text-gray-700">
                  <span className="text-xs font-mono bg-gray-100 px-1 rounded mr-1">{dest.iso_alpha_3}</span>
                  {dest.country_name}
                </span>
                <span className="font-semibold">{fmt(dest.total_value_usd)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">Top Exported Products (HS-2)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {topHsCodes.slice(0, 10).map((hs) => (
              <div key={hs.hs_code} className="flex items-center justify-between py-2 border-b last:border-0">
                <span className="text-gray-700">
                  <span className="text-xs font-mono bg-gray-100 px-1 rounded mr-1">{hs.hs_code}</span>
                  {hs.description?.slice(0, 45)}
                </span>
                <span className="font-semibold ml-2 whitespace-nowrap">{fmt(hs.total_value_usd)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// TRACKING DASHBOARD
// ============================================================================

export const TrackingDashboard = () => {
  const [transactionId, setTransactionId] = useState('');
  const [tracking, setTracking] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchTracking = async () => {
    if (!transactionId.trim()) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await api().get(`tracking/shipment/${transactionId}`);
      setTracking(data);
    } catch (err) {
      setError(err.response?.status === 404 ? 'Shipment tracking not found' : 'Failed to fetch tracking data');
      setTracking([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-[900px] mx-auto">
      <h1 className="text-2xl font-bold mb-6">Shipment Tracking</h1>

      <div className="mb-6 flex gap-3">
        <input
          type="text"
          placeholder="Enter Transaction ID (e.g., EXP2024001)"
          className="flex-1 border rounded px-3 py-2 text-sm"
          value={transactionId}
          onChange={e => setTransactionId(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && fetchTracking()}
        />
        <button
          onClick={fetchTracking}
          disabled={loading || !transactionId.trim()}
          className="bg-blue-600 text-white px-6 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Searching…' : 'Track'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6 text-sm">{error}</div>
      )}

      {tracking.length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-5">Tracking History</h2>
          <div className="space-y-5">
            {tracking.map((event, index) => (
              <div key={index} className="flex items-start gap-4">
                <div className="mt-1.5 w-3 h-3 bg-blue-500 rounded-full flex-shrink-0" />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium capitalize">{event.tracking_event.replace(/_/g, ' ')}</h3>
                    <span className="text-xs text-gray-400">
                      {new Date(event.event_timestamp).toLocaleString()}
                    </span>
                  </div>
                  {event.status_description && (
                    <p className="text-sm text-gray-600 mt-1">{event.status_description}</p>
                  )}
                  <div className="flex gap-4 mt-1">
                    {event.location && <span className="text-xs text-gray-500">📍 {event.location}</span>}
                    {event.carrier_name && (
                      <span className="text-xs text-gray-500">🚢 {event.carrier_name}{event.vessel_name ? ` · ${event.vessel_name}` : ''}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
