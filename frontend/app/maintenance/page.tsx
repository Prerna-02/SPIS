'use client'

import { useState, useEffect, useCallback } from 'react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import PageWrapper from '../components/PageWrapper'

// ============================================================
// TYPES
// ============================================================
interface EquipmentRecord {
    asset_id: string
    asset_type: string
    timestamp: string
    operation_state: string
    utilization_rate: number
    load_tons: number
    motor_temp_c: number
    gearbox_temp_c: number
    hydraulic_pressure_bar: number
    vibration_rms: number
    current_amp: number
    rpm: number
    rul_hours: number
    failure_mode: string
    failure_in_72h: boolean
    risk_level: string
}

interface RULPrediction {
    asset_id: string
    asset_type: string
    rul_hours: number
    rul_days: number
    failure_mode: string
    failure_probability: number
    failure_in_72h: boolean
    risk_level: string
    recommendation: string
    sensor_summary: Record<string, number>
}

interface OperationStats {
    operation_counts: Record<string, number>
    load_capacity: Record<string, { mean: number; max: number }>
    risk_distribution: Record<string, number>
    total_equipment: number
    critical_count: number
    avg_rul: number
}

interface ModelMetrics {
    model_name: string
    architecture: string
    why_bilstm: string
    hyperparameters: Record<string, unknown>
    rul_metrics: Record<string, number | string>
    failure_metrics: Record<string, number>
    model_comparison: Record<string, { R2: number; MAE: number; F1: number }>
}

// ============================================================
// CONSTANTS
// ============================================================
const API_BASE = 'http://localhost:8003'
const REFRESH_INTERVAL = 10000 // 10 seconds

const ASSET_TYPES = ['All', 'STS_CRANE', 'RTG_CRANE', 'STRADDLE_CARRIER', 'YARD_TRACTOR', 'FORKLIFT', 'TRUCK']

const RISK_COLORS: Record<string, string> = {
    low: 'bg-green-900/50 text-green-300 border-green-500',
    medium: 'bg-yellow-900/50 text-yellow-300 border-yellow-500',
    high: 'bg-orange-900/50 text-orange-300 border-orange-500',
    critical: 'bg-red-900/50 text-red-300 border-red-500',
}

const STATE_COLORS: Record<string, string> = {
    idle: '#6B7280',
    moving: '#3B82F6',
    loading: '#22C55E',
    unloading: '#F59E0B',
}

const PIE_COLORS = ['#6B7280', '#3B82F6', '#22C55E', '#F59E0B']

// ============================================================
// COMPONENT
// ============================================================
export default function MaintenancePage() {
    // State
    const [liveData, setLiveData] = useState<EquipmentRecord[]>([])
    const [stats, setStats] = useState<OperationStats | null>(null)
    const [modelInfo, setModelInfo] = useState<ModelMetrics | null>(null)
    const [prediction, setPrediction] = useState<RULPrediction | null>(null)
    const [assetList, setAssetList] = useState<string[]>([])

    const [selectedType, setSelectedType] = useState('All')
    const [searchAssetId, setSearchAssetId] = useState('')
    const [searchAssetType, setSearchAssetType] = useState('')
    const [loading, setLoading] = useState(false)
    const [isStreaming, setIsStreaming] = useState(true)
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

    // Fetch live data
    const fetchLiveData = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/stream?count=5`)
            if (res.ok) {
                const data = await res.json()
                setLiveData(data)
                setLastUpdate(new Date())
            }
        } catch (err) {
            console.error('Stream fetch error:', err)
        }
    }, [])

    // Fetch stats
    const fetchStats = useCallback(async () => {
        try {
            const typeParam = selectedType !== 'All' ? `?asset_type=${selectedType}` : ''
            const res = await fetch(`${API_BASE}/stats${typeParam}`)
            if (res.ok) {
                setStats(await res.json())
            }
        } catch (err) {
            console.error('Stats fetch error:', err)
        }
    }, [selectedType])

    // Fetch model info
    const fetchModelInfo = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/model-info`)
            if (res.ok) {
                setModelInfo(await res.json())
            }
        } catch (err) {
            console.error('Model info fetch error:', err)
        }
    }, [])

    // Fetch asset list
    const fetchAssetList = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/assets`)
            if (res.ok) {
                setAssetList(await res.json())
            }
        } catch (err) {
            console.error('Asset list fetch error:', err)
        }
    }, [])

    // Predict RUL for specific asset
    const predictRUL = async () => {
        if (!searchAssetId) return
        setLoading(true)
        try {
            const typeParam = searchAssetType ? `&asset_type=${searchAssetType}` : ''
            const res = await fetch(`${API_BASE}/predict?asset_id=${searchAssetId}${typeParam}`)
            if (res.ok) {
                setPrediction(await res.json())
            } else {
                alert('Asset not found')
            }
        } catch (err) {
            console.error('Predict error:', err)
        }
        setLoading(false)
    }

    // Initial load
    useEffect(() => {
        fetchLiveData()
        fetchStats()
        fetchModelInfo()
        fetchAssetList()
    }, [fetchLiveData, fetchStats, fetchModelInfo, fetchAssetList])

    // Auto-refresh
    useEffect(() => {
        if (!isStreaming) return
        const interval = setInterval(() => {
            fetchLiveData()
        }, REFRESH_INTERVAL)
        return () => clearInterval(interval)
    }, [isStreaming, fetchLiveData])

    // Refetch stats when filter changes
    useEffect(() => {
        fetchStats()
    }, [selectedType, fetchStats])

    // Transform data for charts
    const operationChartData = stats ? Object.entries(stats.operation_counts).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
        fill: STATE_COLORS[name] || '#888'
    })) : []

    const loadCapacityData = stats ? Object.entries(stats.load_capacity).map(([type, data]) => ({
        type: type.replace('_', ' '),
        max: data.max,
        avg: data.mean
    })).sort((a, b) => b.max - a.max) : []

    // Filtered live data
    const filteredLiveData = selectedType === 'All'
        ? liveData
        : liveData.filter(e => e.asset_type === selectedType)

    return (
        <PageWrapper title="🔧 Smart Maintenance" subtitle="Real-time predictive maintenance with RUL estimation">
            <div className="space-y-6">
                {/* Controls */}
                <div className="flex justify-end items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-sm ${isStreaming ? 'bg-green-900/50 text-green-300' : 'bg-gray-700 text-gray-400'}`}>
                        {isStreaming ? '🟢 Live' : '⏸️ Paused'}
                    </span>
                    <button
                        onClick={() => setIsStreaming(!isStreaming)}
                        className="px-4 py-2 backdrop-blur bg-white/10 border border-white/20 rounded-lg text-white hover:bg-white/20"
                    >
                        {isStreaming ? 'Pause' : 'Resume'}
                    </button>
                </div>

                {/* Filter Buttons */}
                <div className="flex gap-2 flex-wrap">
                    {ASSET_TYPES.map((type) => (
                        <button
                            key={type}
                            onClick={() => setSelectedType(type)}
                            className={`px-4 py-2 rounded-lg text-sm ${selectedType === type
                                ? 'bg-blue-600 text-white'
                                : 'bg-spis-card text-gray-300 border border-spis-border hover:bg-spis-border'}`}
                        >
                            {type.replace('_', ' ')}
                        </button>
                    ))}
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-4 gap-4">
                    <div className="card">
                        <p className="text-sm text-gray-400">Total Equipment</p>
                        <p className="text-2xl font-bold text-white">{stats?.total_equipment || 0}</p>
                    </div>
                    <div className="card border-red-500">
                        <p className="text-sm text-gray-400">Critical Alerts</p>
                        <p className="text-2xl font-bold text-red-400">{stats?.critical_count || 0}</p>
                    </div>
                    <div className="card border-blue-500">
                        <p className="text-sm text-gray-400">Avg RUL</p>
                        <p className="text-2xl font-bold text-blue-400">{stats?.avg_rul?.toFixed(0) || 0} hrs</p>
                    </div>
                    <div className="card border-green-500">
                        <p className="text-sm text-gray-400">Last Update</p>
                        <p className="text-xl font-bold text-green-400">{lastUpdate?.toLocaleTimeString() || '-'}</p>
                    </div>
                </div>

                {/* Live Monitoring Table */}
                <div className="card">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold text-white">📡 Live Equipment Monitor</h3>
                        <p className="text-xs text-gray-500">Auto-refreshes every 10 seconds</p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-spis-border text-left">
                                    <th className="py-2 px-2 text-gray-400">Asset</th>
                                    <th className="py-2 px-2 text-gray-400">Type</th>
                                    <th className="py-2 px-2 text-gray-400">State</th>
                                    <th className="py-2 px-2 text-gray-400">Motor °C</th>
                                    <th className="py-2 px-2 text-gray-400">Gearbox °C</th>
                                    <th className="py-2 px-2 text-gray-400">Pressure</th>
                                    <th className="py-2 px-2 text-gray-400">Vibration</th>
                                    <th className="py-2 px-2 text-gray-400">RUL (hrs)</th>
                                    <th className="py-2 px-2 text-gray-400">Failure Mode</th>
                                    <th className="py-2 px-2 text-gray-400">Risk</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(filteredLiveData.length > 0 ? filteredLiveData : liveData).map((eq, i) => (
                                    <tr key={`${eq.asset_id}-${i}`} className="border-b border-spis-border/50 hover:bg-spis-border/30">
                                        <td className="py-2 px-2 text-white font-medium">{eq.asset_id}</td>
                                        <td className="py-2 px-2 text-gray-300">{eq.asset_type.replace('_', ' ')}</td>
                                        <td className="py-2 px-2">
                                            <span className="px-2 py-0.5 rounded text-xs" style={{ backgroundColor: STATE_COLORS[eq.operation_state] + '40', color: STATE_COLORS[eq.operation_state] }}>
                                                {eq.operation_state}
                                            </span>
                                        </td>
                                        <td className={`py-2 px-2 ${eq.motor_temp_c > 75 ? 'text-red-400' : 'text-gray-300'}`}>{eq.motor_temp_c}°</td>
                                        <td className={`py-2 px-2 ${eq.gearbox_temp_c > 55 ? 'text-yellow-400' : 'text-gray-300'}`}>{eq.gearbox_temp_c}°</td>
                                        <td className="py-2 px-2 text-gray-300">{eq.hydraulic_pressure_bar} bar</td>
                                        <td className={`py-2 px-2 ${eq.vibration_rms > 0.4 ? 'text-orange-400' : 'text-gray-300'}`}>{eq.vibration_rms}</td>
                                        <td className={`py-2 px-2 font-bold ${eq.rul_hours < 100 ? 'text-red-400' : eq.rul_hours < 300 ? 'text-yellow-400' : 'text-green-400'}`}>
                                            {eq.rul_hours}
                                        </td>
                                        <td className="py-2 px-2 text-gray-300">{eq.failure_mode !== 'none' ? eq.failure_mode.replace('_', ' ') : '-'}</td>
                                        <td className="py-2 px-2">
                                            <span className={`px-2 py-0.5 rounded text-xs uppercase border ${RISK_COLORS[eq.risk_level]}`}>
                                                {eq.risk_level}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Equipment Lookup */}
                <div className="card">
                    <h3 className="text-lg font-bold text-white mb-4">🔍 Equipment Lookup</h3>
                    <div className="flex gap-4 items-end mb-4">
                        <div className="flex-1">
                            <label className="block text-sm text-gray-400 mb-1">Asset ID</label>
                            <select
                                value={searchAssetId}
                                onChange={(e) => setSearchAssetId(e.target.value)}
                                className="w-full px-3 py-2 bg-spis-bg border border-spis-border rounded-lg text-white"
                            >
                                <option value="">Select Asset...</option>
                                {assetList.map(id => (
                                    <option key={id} value={id}>{id}</option>
                                ))}
                            </select>
                        </div>
                        <div className="w-48">
                            <label className="block text-sm text-gray-400 mb-1">Type (optional)</label>
                            <select
                                value={searchAssetType}
                                onChange={(e) => setSearchAssetType(e.target.value)}
                                className="w-full px-3 py-2 bg-spis-bg border border-spis-border rounded-lg text-white"
                            >
                                <option value="">Any</option>
                                {ASSET_TYPES.slice(1).map(t => (
                                    <option key={t} value={t}>{t.replace('_', ' ')}</option>
                                ))}
                            </select>
                        </div>
                        <button
                            onClick={predictRUL}
                            disabled={!searchAssetId || loading}
                            className={`px-6 py-2 rounded-lg font-medium ${loading || !searchAssetId ? 'bg-gray-600' : 'bg-blue-600 hover:bg-blue-700'} text-white`}
                        >
                            {loading ? '⏳' : '🔍'} Predict
                        </button>
                    </div>

                    {prediction && (
                        <div className={`p-4 rounded-lg border ${RISK_COLORS[prediction.risk_level]}`}>
                            <div className="grid grid-cols-3 gap-4 mb-4">
                                <div>
                                    <p className="text-sm opacity-70">Asset</p>
                                    <p className="text-xl font-bold">{prediction.asset_id}</p>
                                    <p className="text-sm opacity-70">{prediction.asset_type.replace('_', ' ')}</p>
                                </div>
                                <div>
                                    <p className="text-sm opacity-70">RUL</p>
                                    <p className="text-2xl font-bold">{prediction.rul_hours} hrs</p>
                                    <p className="text-sm opacity-70">({prediction.rul_days} days)</p>
                                </div>
                                <div>
                                    <p className="text-sm opacity-70">Failure Mode</p>
                                    <p className="text-xl font-bold">{prediction.failure_mode.replace('_', ' ')}</p>
                                    <p className="text-sm opacity-70">{(prediction.failure_probability * 100).toFixed(0)}% probability</p>
                                </div>
                            </div>
                            {prediction.failure_in_72h && (
                                <div className="mb-3 p-2 bg-red-700/50 rounded text-red-200 text-sm animate-pulse">
                                    ⚠️ WARNING: High probability of failure within 72 hours!
                                </div>
                            )}
                            <div className="p-3 bg-black/20 rounded">
                                <p className="text-sm">{prediction.recommendation}</p>
                            </div>
                            <div className="mt-3 grid grid-cols-6 gap-2 text-xs">
                                {Object.entries(prediction.sensor_summary).map(([key, val]) => (
                                    <div key={key} className="text-center p-2 bg-black/20 rounded">
                                        <p className="opacity-70">{key.replace('_', ' ')}</p>
                                        <p className="font-bold">{val}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Charts Section */}
                <div className="grid grid-cols-2 gap-6">
                    {/* Operation Status Pie */}
                    <div className="card">
                        <h3 className="text-lg font-bold text-white mb-4">⚡ Operation Status</h3>
                        <ResponsiveContainer width="100%" height={220}>
                            <PieChart>
                                <Pie
                                    data={operationChartData}
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={80}
                                    dataKey="value"
                                    label={({ name, value }) => `${name}: ${value.toLocaleString()}`}
                                    labelLine={false}
                                >
                                    {operationChartData.map((entry, i) => (
                                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Load Capacity Bar */}
                    <div className="card">
                        <h3 className="text-lg font-bold text-white mb-4">📦 Max Load Capacity (tons)</h3>
                        <ResponsiveContainer width="100%" height={220}>
                            <BarChart data={loadCapacityData} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                <XAxis type="number" stroke="#9CA3AF" />
                                <YAxis type="category" dataKey="type" stroke="#9CA3AF" width={100} tick={{ fontSize: 11 }} />
                                <Tooltip contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #374151' }} />
                                <Legend />
                                <Bar dataKey="max" fill="#3B82F6" name="Max" />
                                <Bar dataKey="avg" fill="#22C55E" name="Avg" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Business Recommendations - MOVED ABOVE MODEL */}
                <div className="card">
                    <h3 className="text-lg font-bold text-white mb-4">🎯 Business Recommendations</h3>
                    <div className="grid grid-cols-3 gap-4">
                        <div className="p-4 bg-red-900/30 rounded-lg border border-red-800">
                            <p className="text-2xl mb-2">🚨</p>
                            <h4 className="font-bold text-red-300 mb-2">Critical Equipment</h4>
                            <p className="text-sm text-gray-300">
                                {stats?.critical_count || 0} assets need immediate attention.
                                Schedule emergency inspections for equipment with RUL &lt; 100 hours.
                            </p>
                        </div>
                        <div className="p-4 bg-blue-900/30 rounded-lg border border-blue-800">
                            <p className="text-2xl mb-2">📅</p>
                            <h4 className="font-bold text-blue-300 mb-2">Maintenance Planning</h4>
                            <p className="text-sm text-gray-300">
                                Average RUL is {stats?.avg_rul?.toFixed(0) || 0} hours.
                                Plan preventive maintenance for assets approaching 300-hour threshold.
                            </p>
                        </div>
                        <div className="p-4 bg-green-900/30 rounded-lg border border-green-800">
                            <p className="text-2xl mb-2">💰</p>
                            <h4 className="font-bold text-green-300 mb-2">Cost Optimization</h4>
                            <p className="text-sm text-gray-300">
                                Prioritize STS_CRANE maintenance (max load 68 tons).
                                Downtime cost: ~€15,000/hour. Predictive maintenance saves 40% vs reactive.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Model Explanation - ENHANCED */}
                {modelInfo && (
                    <div className="card">
                        <h3 className="text-lg font-bold text-white mb-4">🔬 Model Explanation</h3>

                        {/* Why BiLSTM */}
                        <div className="mb-6 p-4 bg-blue-900/20 rounded-lg border border-blue-800">
                            <h4 className="font-bold text-blue-400 mb-2">Why We Chose BiLSTM + Attention</h4>
                            <p className="text-sm text-gray-300">{modelInfo.why_bilstm || 'BiLSTM captures both past and future context in sensor sequences for better degradation pattern detection.'}</p>
                        </div>

                        {/* Model Comparison Table */}
                        {modelInfo.model_comparison && (
                            <div className="mb-6">
                                <h4 className="font-bold text-gray-400 mb-3">📊 Model Comparison (LSTM vs BiLSTM)</h4>
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-spis-border">
                                            <th className="py-2 text-left text-gray-400">Model</th>
                                            <th className="py-2 text-center text-gray-400">R² Score</th>
                                            <th className="py-2 text-center text-gray-400">MAE (hours)</th>
                                            <th className="py-2 text-center text-gray-400">F1 Score</th>
                                            <th className="py-2 text-center text-gray-400">Improvement</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {Object.entries(modelInfo.model_comparison).map(([name, metrics], i) => {
                                            const isBest = name === 'BiLSTM_Attention'
                                            const baseline = modelInfo.model_comparison['LSTM']
                                            const improvement = baseline ? ((metrics.R2 - baseline.R2) / baseline.R2 * 100).toFixed(1) : '0'
                                            return (
                                                <tr key={name} className={`border-b border-spis-border/50 ${isBest ? 'bg-green-900/20' : ''}`}>
                                                    <td className="py-2 text-white font-medium">
                                                        {name.replace('_', ' + ')}
                                                        {isBest && <span className="ml-2 text-xs text-green-400">⭐ Best</span>}
                                                    </td>
                                                    <td className="py-2 text-center text-blue-400">{metrics.R2.toFixed(3)}</td>
                                                    <td className="py-2 text-center text-yellow-400">{metrics.MAE.toFixed(1)}</td>
                                                    <td className="py-2 text-center text-green-400">{metrics.F1.toFixed(2)}</td>
                                                    <td className="py-2 text-center text-purple-400">
                                                        {i === 0 ? 'Baseline' : `+${improvement}%`}
                                                    </td>
                                                </tr>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-6">
                            <div>
                                <h4 className="font-bold text-blue-400 mb-2">{modelInfo.model_name} Architecture</h4>
                                <p className="text-sm text-gray-300 mb-4">{modelInfo.architecture}</p>

                                <h5 className="font-bold text-gray-400 mb-2">Hyperparameters</h5>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    {Object.entries(modelInfo.hyperparameters).map(([k, v]) => (
                                        <div key={k} className="flex justify-between">
                                            <span className="text-gray-500">{k.replace(/_/g, ' ')}</span>
                                            <span className="text-gray-300">{String(v)}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <h5 className="font-bold text-gray-400 mb-2">RUL Prediction Metrics</h5>
                                <div className="grid grid-cols-2 gap-2 mb-4 text-sm">
                                    {Object.entries(modelInfo.rul_metrics).map(([k, v]) => (
                                        <div key={k} className="p-2 bg-spis-bg rounded text-center">
                                            <p className="text-xs text-gray-500">{k}</p>
                                            <p className="text-lg font-bold text-blue-400">{v}</p>
                                        </div>
                                    ))}
                                </div>

                                <h5 className="font-bold text-gray-400 mb-2">Failure Classification Metrics</h5>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    {Object.entries(modelInfo.failure_metrics).map(([k, v]) => (
                                        <div key={k} className="p-2 bg-spis-bg rounded text-center">
                                            <p className="text-xs text-gray-500">{k.replace('_', ' ')}</p>
                                            <p className="text-lg font-bold text-green-400">{typeof v === 'number' ? v.toFixed(2) : v}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </PageWrapper>
    )
}
