'use client';

import { useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

interface DetectionResult {
    is_anomaly: boolean;
    anomaly_score: number;
    threshold: number;
    status: string;
    risk_level: string;
    recommendation: string;
    in_port_area: boolean;
}

export default function ManualCheck() {
    const [formData, setFormData] = useState({
        timestamp_str: '27/02/2024 12:30:00',
        mmsi: '123456789',
        latitude: '55.70',
        longitude: '12.55',
        sog: '10.5',
        cog: '180.0',
        heading: '175.0'
    });

    const [result, setResult] = useState<DetectionResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const payload = {
                timestamp_str: formData.timestamp_str,
                mmsi: parseFloat(formData.mmsi),
                latitude: parseFloat(formData.latitude),
                longitude: parseFloat(formData.longitude),
                sog: parseFloat(formData.sog),
                cog: parseFloat(formData.cog),
                heading: parseFloat(formData.heading)
            };

            const response = await fetch(`${API_BASE}/detect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            setResult(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to detect anomaly');
        } finally {
            setLoading(false);
        }
    };

    const getRiskColor = (risk: string) => {
        switch (risk?.toUpperCase()) {
            case 'LOW': return 'var(--accent-blue)';
            case 'MEDIUM': return 'var(--accent-yellow)';
            case 'HIGH': return 'var(--accent-red)';
            case 'CRITICAL': return 'var(--accent-red)';
            default: return 'var(--accent-green)';
        }
    };

    return (
        <div className="container">
            <div className="page-header">
                <h1 className="page-title">Manual Anomaly Check</h1>
                <p className="page-subtitle">Enter vessel AIS data to check for anomalous behavior</p>
            </div>

            <div className="two-column">
                {/* Input Form */}
                <div className="table-container" style={{ padding: '1.5rem' }}>
                    <h3 style={{ marginBottom: '1.5rem' }}>Vessel Data Input</h3>

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Timestamp (DD/MM/YYYY HH:MM:SS)</label>
                            <input
                                type="text"
                                name="timestamp_str"
                                value={formData.timestamp_str}
                                onChange={handleChange}
                                className="form-input"
                                placeholder="27/02/2024 12:30:00"
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">MMSI (Maritime Mobile Service Identity)</label>
                            <input
                                type="text"
                                name="mmsi"
                                value={formData.mmsi}
                                onChange={handleChange}
                                className="form-input"
                                placeholder="123456789"
                            />
                        </div>

                        <div className="form-grid">
                            <div className="form-group">
                                <label className="form-label">Latitude</label>
                                <input
                                    type="text"
                                    name="latitude"
                                    value={formData.latitude}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="55.70"
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Longitude</label>
                                <input
                                    type="text"
                                    name="longitude"
                                    value={formData.longitude}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="12.55"
                                />
                            </div>
                        </div>

                        <div className="form-grid">
                            <div className="form-group">
                                <label className="form-label">SOG (knots)</label>
                                <input
                                    type="text"
                                    name="sog"
                                    value={formData.sog}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="10.5"
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">COG (degrees)</label>
                                <input
                                    type="text"
                                    name="cog"
                                    value={formData.cog}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="180.0"
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Heading (degrees)</label>
                                <input
                                    type="text"
                                    name="heading"
                                    value={formData.heading}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="175.0"
                                />
                            </div>
                        </div>

                        <button type="submit" className="btn btn-primary" disabled={loading}>
                            {loading ? (
                                <>
                                    <div className="spinner"></div>
                                    Analyzing...
                                </>
                            ) : (
                                '🔍 Check for Anomaly'
                            )}
                        </button>
                    </form>

                    {error && (
                        <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', color: 'var(--accent-red)' }}>
                            {error}
                        </div>
                    )}
                </div>

                {/* Results Panel */}
                <div className="table-container" style={{ padding: '1.5rem' }}>
                    <h3 style={{ marginBottom: '1.5rem' }}>Detection Result</h3>

                    {!result ? (
                        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                            <p style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>🔎</p>
                            <p>Enter vessel data and click "Check for Anomaly"</p>
                        </div>
                    ) : (
                        <div className="response-panel">
                            <div className="response-status">
                                <div
                                    className={`response-icon ${result.is_anomaly ? 'anomaly' : 'normal'}`}
                                    style={{ fontSize: '2rem' }}
                                >
                                    {result.is_anomaly ? '⚠️' : '✅'}
                                </div>
                                <div>
                                    <h2 style={{ color: result.is_anomaly ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                                        {result.status}
                                    </h2>
                                    <p style={{ color: 'var(--text-secondary)' }}>{result.recommendation}</p>
                                </div>
                            </div>

                            <div className="response-grid">
                                <div className="response-item">
                                    <div className="response-item-label">Anomaly Score</div>
                                    <div className="response-item-value" style={{ color: result.is_anomaly ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                                        {result.anomaly_score?.toFixed(4)}
                                    </div>
                                </div>
                                <div className="response-item">
                                    <div className="response-item-label">Threshold</div>
                                    <div className="response-item-value">{result.threshold?.toFixed(4)}</div>
                                </div>
                                <div className="response-item">
                                    <div className="response-item-label">Risk Level</div>
                                    <div className="response-item-value" style={{ color: getRiskColor(result.risk_level) }}>
                                        {result.risk_level}
                                    </div>
                                </div>
                                <div className="response-item">
                                    <div className="response-item-label">In Port Area</div>
                                    <div className="response-item-value">
                                        {result.in_port_area ? '✅ Yes' : '❌ No'}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
