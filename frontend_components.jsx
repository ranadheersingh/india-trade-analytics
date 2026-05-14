/**
 * Frontend Components for Phase 2-4 Dashboards
 * - Transaction Detail Dashboard
 * - Exporter Directory
 * - Port & Transport Analytics
 * - Real-time Tracking
 */

// ============================================================================
// 1. TRANSACTION DETAIL DASHBOARD
// ============================================================================

import React, { useState, useEffect } from 'react';

export function TransactionDashboard() {
  const [transactions, setTransactions] = useState([]);
  const [filters, setFilters] = useState({
    exporter_id: '',
    destination: '',
    hs_code: '',
    startDate: '',
    endDate: ''
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });

      const response = await fetch(`/api/v1/transactions/exports?${params}`);
      const data = await response.json();
      setTransactions(data.data || []);
    } catch (error) {
      console.error('Error fetching transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleSearch = () => {
    fetchTransactions();
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>📊 Export Transactions</h1>

      {/* Filters */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '10px',
        marginBottom: '20px',
        padding: '15px',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px'
      }}>
        <input
          type="text"
          name="exporter_id"
          placeholder="Exporter ID"
          value={filters.exporter_id}
          onChange={handleFilterChange}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <input
          type="text"
          name="destination"
          placeholder="Destination Country"
          value={filters.destination}
          onChange={handleFilterChange}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <input
          type="text"
          name="hs_code"
          placeholder="HS Code"
          value={filters.hs_code}
          onChange={handleFilterChange}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <input
          type="date"
          name="startDate"
          value={filters.startDate}
          onChange={handleFilterChange}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <input
          type="date"
          name="endDate"
          value={filters.endDate}
          onChange={handleFilterChange}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: '8px 16px',
            backgroundColor: '#0066cc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          🔍 Search
        </button>
      </div>

      {/* Results Summary */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginBottom: '20px'
      }}>
        <div style={{
          padding: '15px',
          backgroundColor: '#e3f2fd',
          borderRadius: '8px',
          borderLeft: '4px solid #0066cc'
        }}>
          <div style={{ fontSize: '12px', color: '#666' }}>Total Transactions</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{transactions.length}</div>
        </div>
        <div style={{
          padding: '15px',
          backgroundColor: '#f3e5f5',
          borderRadius: '8px',
          borderLeft: '4px solid #9c27b0'
        }}>
          <div style={{ fontSize: '12px', color: '#666' }}>Total Value</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
            ${(transactions.reduce((sum, t) => sum + (t.total_value_usd || 0), 0) / 1000000).toFixed(2)}M
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          backgroundColor: 'white',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          borderRadius: '8px',
          overflow: 'hidden'
        }}>
          <thead>
            <tr style={{ backgroundColor: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
              <th style={{ padding: '12px', textAlign: 'left' }}>Transaction ID</th>
              <th style={{ padding: '12px', textAlign: 'left' }}>Date</th>
              <th style={{ padding: '12px', textAlign: 'left' }}>Exporter</th>
              <th style={{ padding: '12px', textAlign: 'left' }}>Destination</th>
              <th style={{ padding: '12px', textAlign: 'left' }}>HS Code</th>
              <th style={{ padding: '12px', textAlign: 'right' }}>Quantity</th>
              <th style={{ padding: '12px', textAlign: 'right' }}>Value (USD)</th>
              <th style={{ padding: '12px', textAlign: 'left' }}>Mode</th>
              <th style={{ padding: '12px', textAlign: 'left' }}>BL</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((trans) => (
              <tr key={trans.transaction_id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '12px' }}>{trans.transaction_id}</td>
                <td style={{ padding: '12px' }}>{trans.export_date}</td>
                <td style={{ padding: '12px' }}>{trans.exporter_name}</td>
                <td style={{ padding: '12px' }}>{trans.destination_country}</td>
                <td style={{ padding: '12px' }}>{trans.product_hs_code}</td>
                <td style={{ padding: '12px', textAlign: 'right' }}>{trans.quantity} {trans.unit_of_measure}</td>
                <td style={{ padding: '12px', textAlign: 'right' }}>${trans.total_value_usd?.toLocaleString()}</td>
                <td style={{ padding: '12px' }}>{trans.mode_of_transport}</td>
                <td style={{ padding: '12px' }}>{trans.bill_of_lading}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {loading && <div style={{ textAlign: 'center', marginTop: '20px' }}>Loading...</div>}
      {!loading && transactions.length === 0 && (
        <div style={{ textAlign: 'center', marginTop: '20px', color: '#666' }}>
          No transactions found
        </div>
      )}
    </div>
  );
}

// ============================================================================
// 2. EXPORTER DIRECTORY
// ============================================================================

export function ExporterDirectory() {
  const [exporters, setExporters] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedExporter, setSelectedExporter] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchExporters();
  }, []);

  const fetchExporters = async () => {
    setLoading(true);
    try {
      const params = search ? `?search=${search}` : '';
      const response = await fetch(`/api/v1/exporters${params}`);
      const data = await response.json();
      setExporters(data.data || []);
    } catch (error) {
      console.error('Error fetching exporters:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    setSearch(e.target.value);
  };

  const handleSearchClick = () => {
    fetchExporters();
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>🏢 Exporter Directory</h1>

      {/* Search */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <input
          type="text"
          placeholder="Search exporters..."
          value={search}
          onChange={handleSearch}
          style={{
            flex: 1,
            padding: '10px',
            borderRadius: '4px',
            border: '1px solid #ccc'
          }}
        />
        <button
          onClick={handleSearchClick}
          style={{
            padding: '10px 20px',
            backgroundColor: '#0066cc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Search
        </button>
      </div>

      {/* Exporters Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: '20px'
      }}>
        {exporters.map((exporter) => (
          <div
            key={exporter.exporter_key}
            style={{
              padding: '20px',
              backgroundColor: 'white',
              borderRadius: '8px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              cursor: 'pointer',
              transition: 'transform 0.2s',
            }}
            onClick={() => setSelectedExporter(exporter)}
            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-4px)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px' }}>
              {exporter.exporter_name}
            </div>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '15px' }}>
              ID: {exporter.exporter_id}
            </div>

            {exporter.email && (
              <div style={{ fontSize: '12px', marginBottom: '5px' }}>
                📧 {exporter.email}
              </div>
            )}
            {exporter.phone && (
              <div style={{ fontSize: '12px', marginBottom: '5px' }}>
                ☎️ {exporter.phone}
              </div>
            )}
            {exporter.website && (
              <div style={{ fontSize: '12px', marginBottom: '15px' }}>
                🌐 {exporter.website}
              </div>
            )}

            <div style={{ borderTop: '1px solid #eee', paddingTop: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '12px', color: '#666' }}>Shipments</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold' }}>
                    {exporter.stats?.shipments || 0}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: '#666' }}>Total Value</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold' }}>
                    ${(exporter.stats?.total_value_usd / 1000000).toFixed(2)}M
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {loading && <div style={{ textAlign: 'center' }}>Loading...</div>}
      {!loading && exporters.length === 0 && (
        <div style={{ textAlign: 'center', color: '#666' }}>
          No exporters found
        </div>
      )}

      {/* Selected Exporter Details Modal */}
      {selectedExporter && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }} onClick={() => setSelectedExporter(null)}>
          <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            maxWidth: '500px',
            maxHeight: '80vh',
            overflowY: 'auto'
          }} onClick={(e) => e.stopPropagation()}>
            <h2>{selectedExporter.exporter_name}</h2>
            <p>ID: {selectedExporter.exporter_id}</p>
            <p>Email: {selectedExporter.email || 'N/A'}</p>
            <p>Phone: {selectedExporter.phone || 'N/A'}</p>
            <p>Website: {selectedExporter.website || 'N/A'}</p>
            <p>Active: {selectedExporter.is_active ? '✅ Yes' : '❌ No'}</p>
            <hr />
            <h3>Statistics</h3>
            <p>Shipments: {selectedExporter.stats?.shipments || 0}</p>
            <p>Total Value: ${selectedExporter.stats?.total_value_usd?.toLocaleString()}</p>
            <button
              onClick={() => setSelectedExporter(null)}
              style={{
                marginTop: '20px',
                padding: '10px 20px',
                backgroundColor: '#ccc',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// 3. ANALYTICS DASHBOARD
// ============================================================================

export function AnalyticsDashboard() {
  const [summary, setSummary] = useState(null);
  const [byMode, setByMode] = useState([]);
  const [destinations, setDestinations] = useState([]);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const [summaryRes, modeRes, destRes] = await Promise.all([
        fetch('/api/v1/analytics/summary'),
        fetch('/api/v1/analytics/by-transport-mode'),
        fetch('/api/v1/destinations')
      ]);

      setSummary((await summaryRes.json()));
      setByMode((await modeRes.json()).data || []);
      setDestinations((await destRes.json()).data || []);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>📈 Analytics Dashboard</h1>

      {/* KPIs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '20px',
        marginBottom: '30px'
      }}>
        <div style={{
          padding: '20px',
          backgroundColor: '#e8f5e9',
          borderRadius: '8px',
          borderLeft: '4px solid #4caf50'
        }}>
          <div style={{ fontSize: '12px', color: '#666' }}>Total Shipments</div>
          <div style={{ fontSize: '32px', fontWeight: 'bold' }}>
            {summary?.exports?.total_shipments || 0}
          </div>
        </div>

        <div style={{
          padding: '20px',
          backgroundColor: '#e3f2fd',
          borderRadius: '8px',
          borderLeft: '4px solid #2196f3'
        }}>
          <div style={{ fontSize: '12px', color: '#666' }}>Total Value</div>
          <div style={{ fontSize: '32px', fontWeight: 'bold' }}>
            ${(summary?.exports?.total_value_usd / 1000000).toFixed(2)}M
          </div>
        </div>

        <div style={{
          padding: '20px',
          backgroundColor: '#fff3e0',
          borderRadius: '8px',
          borderLeft: '4px solid #ff9800'
        }}>
          <div style={{ fontSize: '12px', color: '#666' }}>Active Exporters</div>
          <div style={{ fontSize: '32px', fontWeight: 'bold' }}>{summary?.exporters || 0}</div>
        </div>

        <div style={{
          padding: '20px',
          backgroundColor: '#f3e5f5',
          borderRadius: '8px',
          borderLeft: '4px solid #9c27b0'
        }}>
          <div style={{ fontSize: '12px', color: '#666' }}>Destinations</div>
          <div style={{ fontSize: '32px', fontWeight: 'bold' }}>{summary?.destinations || 0}</div>
        </div>
      </div>

      {/* Charts Section */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '20px'
      }}>
        {/* By Transport Mode */}
        <div style={{
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <h3>🚢 By Transport Mode</h3>
          {byMode.map((item) => (
            <div key={item.mode} style={{ marginBottom: '15px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                <span>{item.mode || 'Unknown'}</span>
                <span>{item.percentage?.toFixed(1)}%</span>
              </div>
              <div style={{
                width: '100%',
                height: '20px',
                backgroundColor: '#eee',
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{
                  height: '100%',
                  width: `${item.percentage || 0}%`,
                  backgroundColor: '#2196f3',
                  transition: 'width 0.3s'
                }} />
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginTop: '3px' }}>
                {item.shipments} shipments, ${(item.total_value_usd / 1000000).toFixed(2)}M
              </div>
            </div>
          ))}
        </div>

        {/* Top Destinations */}
        <div style={{
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <h3>🌍 Top Destinations</h3>
          {destinations.slice(0, 5).map((dest) => (
            <div key={dest.country} style={{
              padding: '10px 0',
              borderBottom: '1px solid #eee',
              display: 'flex',
              justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ fontWeight: 'bold' }}>{dest.country}</div>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  {dest.shipments} shipments
                </div>
              </div>
              <div style={{ textAlign: 'right', fontWeight: 'bold' }}>
                ${(dest.total_value_usd / 1000000).toFixed(2)}M
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 4. REAL-TIME TRACKING
// ============================================================================

export function TrackingDashboard() {
  const [containerNumber, setContainerNumber] = useState('');
  const [tracking, setTracking] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTrack = async () => {
    if (!containerNumber.trim()) {
      setError('Please enter a container number');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await fetch(`/api/v1/tracking/shipment/${containerNumber}`);
      if (!response.ok) {
        throw new Error('Shipment not found');
      }
      const data = await response.json();
      setTracking(data);
    } catch (err) {
      setError(err.message);
      setTracking(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>🚚 Real-Time Shipment Tracking</h1>

      {/* Search Box */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            placeholder="Enter container number (e.g., CONT-002001)"
            value={containerNumber}
            onChange={(e) => setContainerNumber(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleTrack()}
            style={{
              flex: 1,
              padding: '12px',
              borderRadius: '4px',
              border: '1px solid #ccc',
              fontSize: '14px'
            }}
          />
          <button
            onClick={handleTrack}
            disabled={loading}
            style={{
              padding: '12px 24px',
              backgroundColor: loading ? '#ccc' : '#0066cc',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '14px'
            }}
          >
            {loading ? 'Tracking...' : '🔍 Track'}
          </button>
        </div>
        {error && <div style={{ color: '#d32f2f', marginTop: '10px' }}>❌ {error}</div>}
      </div>

      {/* Tracking Details */}
      {tracking && (
        <div style={{
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}>
          <div style={{ marginBottom: '20px' }}>
            <h2 style={{ margin: 0 }}>Container: {tracking.container}</h2>
            <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
              Updated: {new Date(tracking.last_updated).toLocaleString()}
            </div>
          </div>

          {/* Status Badge */}
          <div style={{
            display: 'inline-block',
            padding: '8px 16px',
            borderRadius: '20px',
            backgroundColor: tracking.status === 'In-Transit' ? '#e3f2fd' : '#e8f5e9',
            color: tracking.status === 'In-Transit' ? '#0066cc' : '#2e7d32',
            marginBottom: '20px',
            fontWeight: 'bold'
          }}>
            {tracking.status}
          </div>

          {/* Ship Details */}
          <div style={{
            padding: '15px',
            backgroundColor: '#f5f5f5',
            borderRadius: '4px',
            marginBottom: '20px'
          }}>
            <h3 style={{ margin: '0 0 10px 0' }}>Vessel Information</h3>
            <div>Vessel: <strong>{tracking.vessel}</strong></div>
            <div>Current Location: <strong>{tracking.current_location}</strong></div>
            <div>Current Port: <strong>{tracking.current_port}</strong></div>
          </div>

          {/* Timeline */}
          <div style={{ marginBottom: '20px' }}>
            <h3>📅 Timeline</h3>
            <div style={{ position: 'relative', paddingLeft: '30px' }}>
              {/* Departure */}
              <div style={{ marginBottom: '20px' }}>
                <div style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  width: '12px',
                  height: '12px',
                  backgroundColor: '#4caf50',
                  borderRadius: '50%',
                  border: '2px solid white'
                }} />
                <div style={{ fontWeight: 'bold' }}>Departure</div>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  {tracking.timeline.departure || 'Not yet'}
                </div>
              </div>

              {/* In Transit */}
              <div style={{ marginBottom: '20px' }}>
                <div style={{
                  position: 'absolute',
                  left: 0,
                  top: '80px',
                  width: '12px',
                  height: '12px',
                  backgroundColor: '#2196f3',
                  borderRadius: '50%',
                  border: '2px solid white'
                }} />
                <div style={{ fontWeight: 'bold' }}>In Transit</div>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  Expected arrival: {tracking.timeline.expected_arrival || 'TBD'}
                </div>
              </div>

              {/* Arrival */}
              <div>
                <div style={{
                  position: 'absolute',
                  left: 0,
                  top: '160px',
                  width: '12px',
                  height: '12px',
                  backgroundColor: tracking.timeline.actual_arrival ? '#4caf50' : '#ccc',
                  borderRadius: '50%',
                  border: '2px solid white'
                }} />
                <div style={{ fontWeight: 'bold' }}>Arrival</div>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  {tracking.timeline.actual_arrival || 'Not arrived'}
                </div>
              </div>
            </div>
          </div>

          {/* Delay Info */}
          {tracking.delay.is_delayed && (
            <div style={{
              padding: '15px',
              backgroundColor: '#fff3e0',
              borderRadius: '4px',
              borderLeft: '4px solid #ff9800',
              marginBottom: '20px'
            }}>
              ⚠️ <strong>Delayed by {tracking.delay.days} days</strong>
            </div>
          )}

          {/* Documents */}
          <div>
            <h3>📄 Documents</h3>
            {tracking.documents.bill_of_lading && (
              <div>BL: <strong>{tracking.documents.bill_of_lading}</strong></div>
            )}
            {tracking.documents.invoice && (
              <div>Invoice: <strong>{tracking.documents.invoice}</strong></div>
            )}
            {tracking.documents.customs_entry && (
              <div>Customs Entry: <strong>{tracking.documents.customs_entry}</strong></div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Export all components
// ============================================================================

export default {
  TransactionDashboard,
  ExporterDirectory,
  AnalyticsDashboard,
  TrackingDashboard
};
