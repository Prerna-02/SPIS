'use client';

import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

interface Vessel {
    mmsi: number;
    last_seen: string;
    latitude: number;
    longitude: number;
    sog: number;
    cog: number;
    heading: number;
    anomaly_score: number;
    threshold: number;
    is_anomaly: boolean;
    risk_level: string;
    recommendation: string;
}

interface Alert {
    timestamp: string;
    mmsi: number;
    latitude: number;
    longitude: number;
    anomaly_score: number;
    risk_level: string;
    recommendation: string;
}

interface Stats {
    total_vessels: number;
    anomalous_vessels: number;
    normal_vessels: number;
    total_alerts: number;
    streaming_enabled: boolean;
    threshold: number;
}

export default function Dashboard() {
    const [vessels, setVessels] = useState<Vessel[]>([]);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [stats, setStats] = useState<Stats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch data every second
    useEffect(() => {
        const fetchData = async () => {
            try {
                const [vesselsRes, alertsRes, statsRes] = await Promise.all([
                    fetch(`${API_BASE}/live/vessels`),
                    fetch(`${API_BASE}/live/alerts`),
                    fetch(`${API_BASE}/live/stats`)
                ]);

                if (!vesselsRes.ok || !alertsRes.ok || !statsRes.ok) {
                    throw new Error('Failed to fetch data');
                }

                const vesselsData = await vesselsRes.json();
                const alertsData = await alertsRes.json();
                const statsData = await statsRes.json();

                setVessels(vesselsData.vessels || []);
                setAlerts(alertsData.alerts || []);
                setStats(statsData);
                setError(null);
            } catch (err) {
                setError('Unable to connect to API. Make sure the backend is running.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 1000);
        return () => clearInterval(interval);
    }, []);

    const formatTime = (isoString: string) => {
        const date = new Date(isoString);
        return date.toLocaleTimeString();
    };

    const getRiskBadgeClass = (risk: string) => {
        switch (risk?.toUpperCase()) {
            case 'LOW': return 'badge badge-low';
            case 'MEDIUM': return 'badge badge-medium';
            case 'HIGH': return 'badge badge-high';
            case 'CRITICAL': return 'badge badge-critical';
            default: return 'badge badge-normal';
        }
    };

    if (loading) {
        return (
            <div className="container" style={{ textAlign: 'center', padding: '4rem' }}>
                <div className="spinner" style={{ margin: '0 auto' }}></div>
                <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Loading dashboard...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="container">
                <div className="stat-card" style={{ textAlign: 'center', padding: '3rem' }}>
                    <h2 style={{ color: 'var(--accent-red)', marginBottom: '1rem' }}>⚠️ Connection Error</h2>
                    <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
                    <p style={{ marginTop: '1rem', fontSize: '0.9rem' }}>
                        Run: <code>docker-compose up</code> or <code>python app.py</code>
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="container">
            <div className="page-header">
                <h1 className="page-title">Live Vessel Monitoring</h1>
                <p className="page-subtitle">Real-time AIS anomaly detection for Copenhagen port area</p>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-label">Active Vessels</div>
                    <div className="stat-value blue">{stats?.total_vessels || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Normal</div>
                    <div className="stat-value green">{stats?.normal_vessels || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Anomalies</div>
                    <div className="stat-value red">{stats?.anomalous_vessels || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Total Alerts</div>
                    <div className="stat-value yellow">{stats?.total_alerts || 0}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Threshold</div>
                    <div className="stat-value">{stats?.threshold?.toFixed(3) || 'N/A'}</div>
                </div>
            </div>

            <div className="two-column">
                {/* Vessels Table */}
                <div className="table-container">
                    <div className="table-header">
                        <span className="table-title">Tracked Vessels</span>
                        <div className="live-indicator">
                            <span className="live-dot"></span>
                            Live
                        </div>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>MMSI</th>
                                <th>Position</th>
                                <th>SOG</th>
                                <th>Score</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {vessels.length === 0 ? (
                                <tr>
                                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                                        Waiting for vessel data...
                                    </td>
                                </tr>
                            ) : (
                                vessels.map((vessel) => (
                                    <tr key={vessel.mmsi} style={vessel.is_anomaly ? { background: 'rgba(239, 68, 68, 0.1)' } : {}}>
                                        <td style={{ fontWeight: 600 }}>{vessel.mmsi}</td>
                                        <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                            {vessel.latitude?.toFixed(4)}, {vessel.longitude?.toFixed(4)}
                                        </td>
                                        <td>{vessel.sog?.toFixed(1)} kn</td>
                                        <td>{vessel.anomaly_score?.toFixed(3)}</td>
                                        <td>
                                            <span className={getRiskBadgeClass(vessel.is_anomaly ? vessel.risk_level : 'normal')}>
                                                {vessel.is_anomaly ? vessel.risk_level : 'NORMAL'}
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Alerts Panel */}
                <div className="table-container">
                    <div className="table-header">
                        <span className="table-title">Recent Alerts</span>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            Last 50
                        </span>
                    </div>
                    <div style={{ padding: '1rem', maxHeight: '400px', overflowY: 'auto' }}>
                        {alerts.length === 0 ? (
                            <p style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                                No anomalies detected yet
                            </p>
                        ) : (
                            alerts.map((alert, idx) => (
                                <div className="alert-card" key={idx}>
                                    <div className="alert-header">
                                        <span className="alert-mmsi">MMSI: {alert.mmsi}</span>
                                        <span className="alert-time">{formatTime(alert.timestamp)}</span>
                                    </div>
                                    <div className="alert-details">
                                        <span className={getRiskBadgeClass(alert.risk_level)}>{alert.risk_level}</span>
                                        <span style={{ marginLeft: '0.5rem' }}>Score: {alert.anomaly_score?.toFixed(3)}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
