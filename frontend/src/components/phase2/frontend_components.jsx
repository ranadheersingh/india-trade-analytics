import React, { useState, useEffect } from 'react';

// ============================================================================
// TRANSACTIONS DASHBOARD
// ============================================================================

export const TransactionsDashboard = () => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    exporter_key: '',
    country_key: '',
    hs_code_key: ''
  });

  useEffect(() => {
    fetchTransactions();
  }, [filters]);

  const fetchTransactions = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.exporter_key) params.append('exporter_key', filters.exporter_key);
      if (filters.country_key) params.append('country_key', filters.country_key);
      if (filters.hs_code_key) params.append('hs_code_key', filters.hs_code_key);

      const response = await fetch(`/api/v1/transactions/exports?${params}`);
      const data = await response.json();
      setTransactions(data);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-6">Loading transactions...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Export Transactions</h1>

      {/* Filters */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <input
          type="text"
          placeholder="Exporter Key"
          className="border p-2 rounded"
          value={filters.exporter_key}
          onChange={(e) => setFilters({...filters, exporter_key: e.target.value})}
        />
        <input
          type="text"
          placeholder="Country Key"
          className="border p-2 rounded"
          value={filters.country_key}
          onChange={(e) => setFilters({...filters, country_key: e.target.value})}
        />
        <input
          type="text"
          placeholder="HS Code Key"
          className="border p-2 rounded"
          value={filters.hs_code_key}
          onChange={(e) => setFilters({...filters, hs_code_key: e.target.value})}
        />
      </div>

      {/* Transactions Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border">
          <thead>
            <tr className="bg-gray-50">
              <th className="border px-4 py-2">Transaction ID</th>
              <th className="border px-4 py-2">Exporter</th>
              <th className="border px-4 py-2">Destination</th>
              <th className="border px-4 py-2">HS Code</th>
              <th className="border px-4 py-2">Value USD</th>
              <th className="border px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx, index) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="border px-4 py-2">{tx.transaction_id}</td>
                <td className="border px-4 py-2">{tx.exporter_name}</td>
                <td className="border px-4 py-2">{tx.destination_country}</td>
                <td className="border px-4 py-2">{tx.hs_description}</td>
                <td className="border px-4 py-2">${tx.value_usd?.toLocaleString()}</td>
                <td className="border px-4 py-2">{tx.shipment_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
    fetchExporters();
  }, []);

  const fetchExporters = async () => {
    try {
      const response = await fetch('/api/v1/exporters');
      const data = await response.json();
      setExporters(data);
    } catch (error) {
      console.error('Failed to fetch exporters:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-6">Loading exporters...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Indian Exporters Directory</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {exporters.map((exporter, index) => (
          <div key={index} className="bg-white border rounded-lg p-6 shadow-sm">
            <h3 className="text-lg font-semibold mb-2">{exporter.company_name}</h3>
            <p className="text-gray-600 mb-1">IEC: {exporter.iec_code}</p>
            <p className="text-gray-600 mb-1">Location: {exporter.city}, {exporter.state_code}</p>
            <p className="text-gray-600 mb-2">Transactions: {exporter.transaction_count || 0}</p>
            <p className="text-lg font-bold text-green-600">
              Total Value: ${exporter.total_value_usd?.toLocaleString() || 0}
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
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const [summaryRes, transportRes, destRes, hsRes] = await Promise.all([
        fetch('/api/v1/analytics/summary'),
        fetch('/api/v1/analytics/by-transport-mode'),
        fetch('/api/v1/destinations'),
        fetch('/api/v1/analytics/by-hs-code')
      ]);

      setSummary(await summaryRes.json());
      setTransportModes(await transportRes.json());
      setTopDestinations(await destRes.json());
      setTopHsCodes(await hsRes.json());
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-6">Loading analytics...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Trade Analytics Dashboard</h1>

      {/* Summary KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-sm font-medium text-gray-500">Export Transactions</h3>
          <p className="text-2xl font-bold">{summary.export_transactions || 0}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-sm font-medium text-gray-500">Export Value</h3>
          <p className="text-2xl font-bold">${summary.export_value_usd?.toLocaleString() || 0}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-sm font-medium text-gray-500">Active Exporters</h3>
          <p className="text-2xl font-bold">{summary.active_exporters || 0}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-sm font-medium text-gray-500">Top Destination</h3>
          <p className="text-2xl font-bold">{topDestinations[0]?.country_name || 'N/A'}</p>
        </div>
      </div>

      {/* Transport Mode Chart */}
      <div className="bg-white p-6 rounded-lg shadow-sm border mb-6">
        <h2 className="text-lg font-semibold mb-4">Exports by Transport Mode</h2>
        <div className="space-y-2">
          {transportModes.map((mode, index) => (
            <div key={index} className="flex justify-between">
              <span>{mode.transport_mode_name}</span>
              <span className="font-semibold">${mode.total_value_usd?.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Destinations */}
      <div className="bg-white p-6 rounded-lg shadow-sm border mb-6">
        <h2 className="text-lg font-semibold mb-4">Top Export Destinations</h2>
        <div className="space-y-2">
          {topDestinations.slice(0, 5).map((dest, index) => (
            <div key={index} className="flex justify-between">
              <span>{dest.country_name} ({dest.iso_alpha_3})</span>
              <span className="font-semibold">${dest.total_value_usd?.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top HS Codes */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h2 className="text-lg font-semibold mb-4">Top Exported Products</h2>
        <div className="space-y-2">
          {topHsCodes.slice(0, 5).map((hs, index) => (
            <div key={index} className="flex justify-between">
              <span className="flex-1">{hs.description}</span>
              <span className="font-semibold ml-4">${hs.total_value_usd?.toLocaleString()}</span>
            </div>
          ))}
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
      const response = await fetch(`/api/v1/tracking/shipment/${transactionId}`);
      if (response.ok) {
        const data = await response.json();
        setTracking(data);
      } else {
        setError('Shipment tracking not found');
        setTracking([]);
      }
    } catch (error) {
      setError('Failed to fetch tracking data');
      setTracking([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Shipment Tracking</h1>

      {/* Search */}
      <div className="mb-6 flex gap-4">
        <input
          type="text"
          placeholder="Enter Transaction ID (e.g., EXP2024001)"
          className="flex-1 border p-2 rounded"
          value={transactionId}
          onChange={(e) => setTransactionId(e.target.value)}
        />
        <button
          onClick={fetchTracking}
          disabled={loading}
          className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? 'Searching...' : 'Track Shipment'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* Tracking Timeline */}
      {tracking.length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Tracking History</h2>
          <div className="space-y-4">
            {tracking.map((event, index) => (
              <div key={index} className="flex items-start space-x-4">
                <div className="w-3 h-3 bg-blue-500 rounded-full mt-2"></div>
                <div className="flex-1">
                  <div className="flex justify-between">
                    <h3 className="font-medium capitalize">{event.tracking_event}</h3>
                    <span className="text-sm text-gray-500">
                      {new Date(event.event_timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-gray-600 mt-1">{event.status_description}</p>
                  {event.location && (
                    <p className="text-sm text-gray-500 mt-1">📍 {event.location}</p>
                  )}
                  {event.carrier_name && (
                    <p className="text-sm text-gray-500">🚢 {event.carrier_name} - {event.vessel_name}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};