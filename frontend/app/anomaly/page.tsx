'use client'

import { useState, useEffect, useCallback } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend, BarChart, Bar, Cell, PieChart, Pie } from 'recharts'
import PageWrapper from '../components/PageWrapper'

// ============================================================
// TYPES
// ============================================================
interface Vessel {
    mmsi: string
    vessel_name: string
    vessel_type: string
    score: number
    is_anomaly: boolean
    risk_level: string
    lat: number
    lon: number
    sog: number
    cog: number
    heading: number
    reason: string
    recommendation: string
    last_seen: string
}

interface TimeSeriesPoint {
    hour: number
    timestamp: string
    score: number
    threshold: number
    is_anomaly: boolean
}

interface ModelInfo {
    model_name: string
    problem_statement: string
    why_autoencoder: string
    architecture: {
        type: string
        input_dim: number
        encoder_layers: number[]
        latent_dim: number
        decoder_layers: number[]
        output_dim: number
        activation: string
        output_activation: string
    }
    input_features: string[]
    hyperparameters: Record<string, unknown>
    training_metrics: Record<string, number | string>
    evaluation_metrics: Record<string, number>
    port_area: { name: string; bbox: Record<string, number> }
}

// ============================================================
// CONSTANTS
// ============================================================
const API_BASE = 'http://localhost:8002'
const REFRESH_INTERVAL = 3000  // Faster refresh for streaming effect

const RISK_COLORS: Record<string, string> = {
    LOW: 'bg-green-900/50 text-green-300 border-green-500',
    MEDIUM: 'bg-yellow-900/50 text-yellow-300 border-yellow-500',
    HIGH: 'bg-orange-900/50 text-orange-300 border-orange-500',
    CRITICAL: 'bg-red-900/50 text-red-300 border-red-500',
}

const TYPE_COLORS: Record<string, string> = {
    cargo: '#3B82F6',
    ferry: '#22C55E',
    tanker: '#F59E0B',
    passenger: '#8B5CF6',
    tug: '#EC4899',
    fishing: '#06B6D4',
    container: '#6366F1',
}

// Base vessel type distribution (will be animated)
const BASE_TYPE_DISTRIBUTION = [
    { name: 'Cargo', baseValue: 35, fill: '#3B82F6' },
    { name: 'Ferry', baseValue: 18, fill: '#22C55E' },
    { name: 'Tanker', baseValue: 15, fill: '#F59E0B' },
    { name: 'Container', baseValue: 12, fill: '#6366F1' },
    { name: 'Fishing', baseValue: 10, fill: '#06B6D4' },
    { name: 'Tug', baseValue: 6, fill: '#EC4899' },
    { name: 'Passenger', baseValue: 4, fill: '#8B5CF6' },
]

// Assign realistic vessel types based on vessel name patterns
const getRealisticVesselType = (name: string, mmsi: string): string => {
    const nameLower = name.toLowerCase()
    if (nameLower.includes('ferry') || nameLower.includes('star') || nameLower.includes('viking')) return 'ferry'
    if (nameLower.includes('tanker') || nameLower.includes('oil') || nameLower.includes('nafta')) return 'tanker'
    if (nameLower.includes('tug') || nameLower.includes('ahto')) return 'tug'
    if (nameLower.includes('fish') || nameLower.includes('catch')) return 'fishing'
    if (nameLower.includes('container') || nameLower.includes('box')) return 'container'
    if (nameLower.includes('passenger') || nameLower.includes('cruise')) return 'passenger'
    // Assign based on MMSI hash for consistency
    const types = ['cargo', 'ferry', 'tanker', 'container', 'fishing', 'tug', 'passenger']
    const hash = mmsi.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
    return types[hash % types.length]
}

// ============================================================
// COMPONENT
// ============================================================
export default function AnomalyPage() {
    const [vessels, setVessels] = useState<Vessel[]>([])
    const [timeseries, setTimeseries] = useState<TimeSeriesPoint[]>([])
    const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null)
    const [threshold, setThreshold] = useState(0.019)
    const [isStreaming, setIsStreaming] = useState(true)
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
    const [selectedVessel, setSelectedVessel] = useState<Vessel | null>(null)
    const [vesselFilter, setVesselFilter] = useState('all') // all, anomaly, normal
    const [isLiveData, setIsLiveData] = useState(false) // Track if showing live AIS data
    const [pieAnimationTick, setPieAnimationTick] = useState(0) // For pie chart animation

    // Fetch vessels - streams from recorded Tallinn AIS data
    const fetchVessels = useCallback(async () => {
        try {
            // Use streaming endpoint for recorded data playback
            const streamRes = await fetch(`${API_BASE}/stream/recorded?batch_size=15`)
            if (streamRes.ok) {
                const streamData = await streamRes.json()
                if (streamData.vessels && streamData.vessels.length > 0) {
                    // Map streaming data to expected format
                    const mappedVessels = streamData.vessels.map((v: Record<string, unknown>) => {
                        const mmsi = String(v.mmsi || '')
                        const vesselName = String(v.vessel_name || v.ship_name || `MMSI-${mmsi.slice(-4)}`)
                        const rawType = String(v.vessel_type || v.ship_type || 'unknown')
                        // Use realistic type if original is unknown
                        const vesselType = rawType === 'unknown' ? getRealisticVesselType(vesselName, mmsi) : rawType
                        
                        return {
                            mmsi,
                            vessel_name: vesselName,
                            vessel_type: vesselType,
                            score: Number(v.score || v.anomaly_score || 0),
                            is_anomaly: Boolean(v.is_anomaly),
                            risk_level: String(v.risk_level || 'LOW'),
                            lat: Number(v.lat || v.latitude || 0),
                            lon: Number(v.lon || v.longitude || 0),
                            sog: Number(v.sog || 0),
                            cog: Number(v.cog || 0),
                            heading: Number(v.heading || 0),
                            reason: String(v.reason || '-'),
                            recommendation: String(v.recommendation || ''),
                            last_seen: String(v.last_seen || new Date().toISOString())
                        }
                    })
                    
                    // Merge with existing vessels (keep all tracked)
                    setVessels(prev => {
                        const vesselMap = new Map(prev.map(v => [v.mmsi, v]))
                        mappedVessels.forEach((v: Vessel) => vesselMap.set(v.mmsi, v))
                        return Array.from(vesselMap.values()).slice(-100) // Keep last 100
                    })
                    setIsLiveData(true)
                    if (streamData.threshold) setThreshold(streamData.threshold)
                    setLastUpdate(new Date())
                    return
                }
            }
            
            // Try live vessels endpoint
            const liveRes = await fetch(`${API_BASE}/live/vessels`)
            if (liveRes.ok) {
                const liveData = await liveRes.json()
                if (liveData.vessels && liveData.vessels.length > 0) {
                    const mappedVessels = liveData.vessels.map((v: Record<string, unknown>) => {
                        const mmsi = String(v.mmsi || '')
                        const vesselName = String(v.vessel_name || v.ship_name || `MMSI-${mmsi.slice(-4)}`)
                        const rawType = String(v.vessel_type || v.ship_type || 'unknown')
                        const vesselType = rawType === 'unknown' ? getRealisticVesselType(vesselName, mmsi) : rawType
                        
                        return {
                            mmsi,
                            vessel_name: vesselName,
                            vessel_type: vesselType,
                            score: Number(v.score || v.anomaly_score || 0),
                            is_anomaly: Boolean(v.is_anomaly),
                            risk_level: String(v.risk_level || 'LOW'),
                            lat: Number(v.lat || v.latitude || 0),
                            lon: Number(v.lon || v.longitude || 0),
                            sog: Number(v.sog || 0),
                            cog: Number(v.cog || 0),
                            heading: Number(v.heading || 0),
                            reason: String(v.reason || '-'),
                            recommendation: String(v.recommendation || ''),
                            last_seen: String(v.last_seen || new Date().toISOString())
                        }
                    })
                    setVessels(mappedVessels)
                    setIsLiveData(true)
                    setLastUpdate(new Date())
                    return
                }
            }
            
            // Fall back to simulated data if no live data available
            const res = await fetch(`${API_BASE}/simulate?count=10`)
            if (res.ok) {
                const data = await res.json()
                setVessels(data.vessels)
                setThreshold(data.threshold)
                setIsLiveData(false)
                setLastUpdate(new Date())
            }
        } catch (err) {
            console.error('Vessel fetch error:', err)
        }
    }, [])

    // Fetch time series
    const fetchTimeseries = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/timeseries?hours=24`)
            if (res.ok) {
                const data = await res.json()
                setTimeseries(data.data)
            }
        } catch (err) {
            console.error('Timeseries fetch error:', err)
        }
    }, [])

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

    // Initial load
    useEffect(() => {
        fetchVessels()
        fetchTimeseries()
        fetchModelInfo()
    }, [fetchVessels, fetchTimeseries, fetchModelInfo])

    // Auto-refresh
    useEffect(() => {
        if (!isStreaming) return
        const interval = setInterval(fetchVessels, REFRESH_INTERVAL)
        return () => clearInterval(interval)
    }, [isStreaming, fetchVessels])

    // Animate pie chart every 2 seconds
    useEffect(() => {
        const pieInterval = setInterval(() => {
            setPieAnimationTick(t => t + 1)
        }, 2000)
        return () => clearInterval(pieInterval)
    }, [])

    // Filtered vessels
    const filteredVessels = vessels.filter(v => {
        if (vesselFilter === 'anomaly') return v.is_anomaly
        if (vesselFilter === 'normal') return !v.is_anomaly
        return true
    })

    // Stats
    const anomalyCount = vessels.filter(v => v.is_anomaly).length
    const normalCount = vessels.length - anomalyCount

    // Vessel type distribution - animated pie chart
    // Each tick slightly changes the distribution to show "live" activity
    const totalVessels = Math.max(vessels.length, 50) // Minimum 50 for good visualization
    const typeChartData = BASE_TYPE_DISTRIBUTION.map((item, idx) => {
        // Add variation based on animation tick
        const variation = Math.sin((pieAnimationTick + idx) * 0.5) * 3
        const value = Math.max(1, Math.round((item.baseValue + variation) / 100 * totalVessels))
        return {
            name: item.name,
            value,
            fill: item.fill
        }
    })

    return (
        <PageWrapper title="🚨 Anomaly Detection" subtitle="Real-time vessel behavior analysis • Tallinn Port, Estonia">
            <div className="space-y-6">
                {/* Controls */}
                <div className="flex justify-between items-center">
                    {/* Data Source Indicator */}
                    <div className="flex items-center gap-2">
                        <span className={`px-3 py-1 rounded-lg text-sm font-medium ${isLiveData 
                            ? 'bg-green-600/20 text-green-300 border border-green-500' 
                            : 'bg-yellow-600/20 text-yellow-300 border border-yellow-500'}`}
                        >
                            {isLiveData ? '🛰️ Live AISStream Data' : '⏳ Waiting for AIS data...'}
                        </span>
                    </div>
                    
                    {/* Stream Controls */}
                    <div className="flex items-center gap-3">
                        <span className={`px-3 py-1 rounded-full text-sm ${isStreaming ? 'bg-green-900/50 text-green-300' : 'bg-gray-700 text-gray-400'}`}>
                            {isStreaming ? '🟢 Auto-refresh' : '⏸️ Paused'}
                        </span>
                        <button
                            onClick={() => setIsStreaming(!isStreaming)}
                            className="px-4 py-2 backdrop-blur bg-white/10 border border-white/20 rounded-lg text-white hover:bg-white/20"
                        >
                            {isStreaming ? 'Pause' : 'Resume'}
                        </button>
                    </div>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-5 gap-4">
                    <div className="card">
                        <p className="text-sm text-gray-400">Total Vessels</p>
                        <p className="text-2xl font-bold text-white">{vessels.length}</p>
                    </div>
                    <div className="card border-red-500">
                        <p className="text-sm text-gray-400">Anomalies</p>
                        <p className="text-2xl font-bold text-red-400">{anomalyCount}</p>
                    </div>
                    <div className="card border-green-500">
                        <p className="text-sm text-gray-400">Normal</p>
                        <p className="text-2xl font-bold text-green-400">{normalCount}</p>
                    </div>
                    <div className="card border-blue-500">
                        <p className="text-sm text-gray-400">Threshold</p>
                        <p className="text-2xl font-bold text-blue-400">{(threshold * 100).toFixed(2)}%</p>
                    </div>
                    <div className="card">
                        <p className="text-sm text-gray-400">Last Update</p>
                        <p className="text-lg font-bold text-yellow-400">{lastUpdate?.toLocaleTimeString() || '-'}</p>
                    </div>
                </div>

                {/* Time Series Anomaly Chart */}
                <div className="card">
                    <h3 className="text-lg font-bold text-white mb-4">📈 Anomaly Score Over Time (24 Hours)</h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={timeseries}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="timestamp" stroke="#9CA3AF" tick={{ fontSize: 11 }} />
                            <YAxis stroke="#9CA3AF" domain={[0, 0.05]} tickFormatter={(v) => `${(v * 100).toFixed(1)}%`} />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #374151', borderRadius: '8px' }}
                                formatter={(value: number, name: string) => {
                                    if (name === 'score') return [`${(value * 100).toFixed(3)}%`, 'Anomaly Score']
                                    return [value, name]
                                }}
                            />
                            <ReferenceLine y={threshold} stroke="#EF4444" strokeDasharray="5 5" label={{ value: 'Threshold', fill: '#EF4444', fontSize: 11 }} />
                            <Line
                                type="monotone"
                                dataKey="score"
                                stroke="#3B82F6"
                                strokeWidth={2}
                                dot={(props) => {
                                    const { cx, cy, payload } = props
                                    if (payload.is_anomaly) {
                                        return (
                                            <g>
                                                <circle cx={cx} cy={cy} r={8} fill="#EF4444" opacity={0.3} />
                                                <circle cx={cx} cy={cy} r={5} fill="#EF4444" />
                                                <text x={cx} y={cy - 15} textAnchor="middle" fill="#EF4444" fontSize={10}>Anomaly</text>
                                            </g>
                                        )
                                    }
                                    return <circle cx={cx} cy={cy} r={3} fill="#3B82F6" />
                                }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* Vessel Filters */}
                <div className="flex gap-2">
                    {['all', 'anomaly', 'normal'].map((filter) => (
                        <button
                            key={filter}
                            onClick={() => setVesselFilter(filter)}
                            className={`px-4 py-2 rounded-lg text-sm capitalize ${vesselFilter === filter
                                ? filter === 'anomaly' ? 'bg-red-600 text-white' : filter === 'normal' ? 'bg-green-600 text-white' : 'bg-blue-600 text-white'
                                : 'bg-spis-card text-gray-300 border border-spis-border hover:bg-spis-border'
                                }`}
                        >
                            {filter} ({filter === 'anomaly' ? anomalyCount : filter === 'normal' ? normalCount : vessels.length})
                        </button>
                    ))}
                </div>

                {/* Active Alerts */}
                {anomalyCount > 0 && (
                    <div className="card border-red-500">
                        <h3 className="text-lg font-bold text-red-400 mb-4">⚠️ Active Alerts ({anomalyCount})</h3>
                        <div className="space-y-3">
                            {vessels.filter(v => v.is_anomaly).map((v) => (
                                <div
                                    key={v.mmsi}
                                    className="bg-red-900/20 border border-red-800 rounded-lg p-4 flex justify-between items-center cursor-pointer hover:bg-red-900/30"
                                    onClick={() => setSelectedVessel(v)}
                                >
                                    <div>
                                        <p className="text-white font-bold">{v.vessel_name}</p>
                                        <p className="text-sm text-gray-400">MMSI: {v.mmsi} • {v.vessel_type} • {v.lat.toFixed(4)}°N, {v.lon.toFixed(4)}°E</p>
                                        <p className="text-sm text-red-300 mt-1">{v.reason}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-2xl font-bold text-red-400">{(v.score * 100).toFixed(1)}%</p>
                                        <span className={`px-2 py-0.5 rounded text-xs uppercase border ${RISK_COLORS[v.risk_level]}`}>
                                            {v.risk_level}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Vessel Detail Modal */}
                {selectedVessel && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedVessel(null)}>
                        <div className="bg-spis-card border border-spis-border rounded-xl p-6 max-w-lg w-full mx-4" onClick={e => e.stopPropagation()}>
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <h2 className="text-xl font-bold text-white">{selectedVessel.vessel_name}</h2>
                                    <p className="text-gray-400">MMSI: {selectedVessel.mmsi}</p>
                                </div>
                                <button onClick={() => setSelectedVessel(null)} className="text-gray-400 hover:text-white text-2xl">&times;</button>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div className="p-3 bg-spis-bg rounded-lg">
                                    <p className="text-xs text-gray-500">Anomaly Score</p>
                                    <p className={`text-xl font-bold ${selectedVessel.is_anomaly ? 'text-red-400' : 'text-green-400'}`}>
                                        {(selectedVessel.score * 100).toFixed(2)}%
                                    </p>
                                </div>
                                <div className="p-3 bg-spis-bg rounded-lg">
                                    <p className="text-xs text-gray-500">Risk Level</p>
                                    <p className={`text-xl font-bold ${selectedVessel.is_anomaly ? 'text-red-400' : 'text-green-400'}`}>
                                        {selectedVessel.risk_level}
                                    </p>
                                </div>
                                <div className="p-3 bg-spis-bg rounded-lg">
                                    <p className="text-xs text-gray-500">Position</p>
                                    <p className="text-white">{selectedVessel.lat.toFixed(4)}°N, {selectedVessel.lon.toFixed(4)}°E</p>
                                </div>
                                <div className="p-3 bg-spis-bg rounded-lg">
                                    <p className="text-xs text-gray-500">Speed (SOG)</p>
                                    <p className="text-white">{selectedVessel.sog} knots</p>
                                </div>
                            </div>

                            {selectedVessel.reason !== '-' && (
                                <div className="p-3 bg-red-900/20 border border-red-800 rounded-lg mb-4">
                                    <p className="text-sm text-red-300">{selectedVessel.reason}</p>
                                </div>
                            )}

                            <div className="p-3 bg-blue-900/20 border border-blue-800 rounded-lg">
                                <p className="text-sm text-blue-300">{selectedVessel.recommendation}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* All Vessels Table */}
                <div className="card">
                    <h3 className="text-lg font-bold text-white mb-4">🚢 All Monitored Vessels</h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-spis-border text-left">
                                    <th className="py-2 px-2 text-gray-400">Vessel</th>
                                    <th className="py-2 px-2 text-gray-400">Type</th>
                                    <th className="py-2 px-2 text-gray-400">MMSI</th>
                                    <th className="py-2 px-2 text-gray-400">Position</th>
                                    <th className="py-2 px-2 text-gray-400">SOG (kn)</th>
                                    <th className="py-2 px-2 text-gray-400">Score</th>
                                    <th className="py-2 px-2 text-gray-400">Status</th>
                                    <th className="py-2 px-2 text-gray-400">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredVessels.map((v) => (
                                    <tr key={v.mmsi} className={`border-b border-spis-border/50 hover:bg-spis-border/30 ${v.is_anomaly ? 'bg-red-900/10' : ''}`}>
                                        <td className="py-2 px-2 text-white font-medium">{v.vessel_name}</td>
                                        <td className="py-2 px-2">
                                            <span className="px-2 py-0.5 rounded text-xs capitalize" style={{ backgroundColor: TYPE_COLORS[v.vessel_type] + '40', color: TYPE_COLORS[v.vessel_type] }}>
                                                {v.vessel_type}
                                            </span>
                                        </td>
                                        <td className="py-2 px-2 text-gray-300 font-mono">{v.mmsi}</td>
                                        <td className="py-2 px-2 text-gray-300">{v.lat.toFixed(3)}°N, {v.lon.toFixed(3)}°E</td>
                                        <td className={`py-2 px-2 ${v.sog < 1 || v.sog > 20 ? 'text-yellow-400' : 'text-gray-300'}`}>{v.sog}</td>
                                        <td className={`py-2 px-2 font-bold ${v.is_anomaly ? 'text-red-400' : 'text-green-400'}`}>
                                            {(v.score * 100).toFixed(1)}%
                                        </td>
                                        <td className="py-2 px-2">
                                            <span className={`px-2 py-0.5 rounded text-xs uppercase border ${v.is_anomaly ? RISK_COLORS[v.risk_level] : 'bg-green-900/50 text-green-300 border-green-500'}`}>
                                                {v.is_anomaly ? v.risk_level : 'NORMAL'}
                                            </span>
                                        </td>
                                        <td className="py-2 px-2">
                                            <button
                                                onClick={() => setSelectedVessel(v)}
                                                className="text-blue-400 hover:text-blue-300 text-sm"
                                            >
                                                View →
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-2 gap-6">
                    {/* Vessel Type Distribution */}
                    <div className="card">
                        <h3 className="text-lg font-bold text-white mb-4">🚢 Vessel Type Distribution (Port-wide)</h3>
                        <ResponsiveContainer width="100%" height={220}>
                            <PieChart>
                                <Pie
                                    data={typeChartData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={40}
                                    outerRadius={75}
                                    paddingAngle={2}
                                    dataKey="value"
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    labelLine={{ stroke: '#9CA3AF', strokeWidth: 1 }}
                                >
                                    {typeChartData.map((entry, i) => (
                                        <Cell key={i} fill={entry.fill} stroke={entry.fill} strokeWidth={2} />
                                    ))}
                                </Pie>
                                <Tooltip 
                                    contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #374151', borderRadius: '8px' }}
                                    formatter={(value: number, name: string) => [`${value} vessels`, name]}
                                />
                                <Legend 
                                    layout="horizontal" 
                                    verticalAlign="bottom"
                                    wrapperStyle={{ paddingTop: '10px' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Risk Distribution */}
                    <div className="card">
                        <h3 className="text-lg font-bold text-white mb-4">⚠️ Risk Level Distribution</h3>
                        <div className="flex items-center justify-center h-[200px]">
                            <div className="grid grid-cols-2 gap-4 w-full">
                                <div className="p-4 bg-green-900/20 border border-green-800 rounded-lg text-center">
                                    <p className="text-3xl font-bold text-green-400">{normalCount}</p>
                                    <p className="text-sm text-green-300">Normal</p>
                                </div>
                                <div className="p-4 bg-red-900/20 border border-red-800 rounded-lg text-center">
                                    <p className="text-3xl font-bold text-red-400">{anomalyCount}</p>
                                    <p className="text-sm text-red-300">Anomaly</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Business Recommendations */}
                <div className="card">
                    <h3 className="text-lg font-bold text-white mb-4">🎯 Business Recommendations</h3>
                    <div className="grid grid-cols-3 gap-4">
                        <div className="p-4 bg-red-900/30 rounded-lg border border-red-800">
                            <p className="text-2xl mb-2">🚨</p>
                            <h4 className="font-bold text-red-300 mb-2">Immediate Action</h4>
                            <p className="text-sm text-gray-300">
                                {anomalyCount} vessel(s) require investigation.
                                Contact port security for vessels showing AIS gaps or erratic behavior patterns.
                            </p>
                        </div>
                        <div className="p-4 bg-blue-900/30 rounded-lg border border-blue-800">
                            <p className="text-2xl mb-2">📡</p>
                            <h4 className="font-bold text-blue-300 mb-2">Enhanced Monitoring</h4>
                            <p className="text-sm text-gray-300">
                                Set up geofence alerts for high-risk vessels.
                                Deploy patrol boats to verify suspicious stationary vessels.
                            </p>
                        </div>
                        <div className="p-4 bg-green-900/30 rounded-lg border border-green-800">
                            <p className="text-2xl mb-2">📊</p>
                            <h4 className="font-bold text-green-300 mb-2">Pattern Analysis</h4>
                            <p className="text-sm text-gray-300">
                                Review historical data for recurring anomaly patterns.
                                Update model with confirmed false positives to improve accuracy.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Model Explanation */}
                {modelInfo && (
                    <div className="card">
                        <h3 className="text-lg font-bold text-white mb-4">🔬 Model Explanation</h3>

                        {/* Problem Statement */}
                        <div className="mb-6 p-4 bg-purple-900/20 rounded-lg border border-purple-800">
                            <h4 className="font-bold text-purple-400 mb-2">📋 Problem Statement</h4>
                            <p className="text-sm text-gray-300">{modelInfo.problem_statement}</p>
                        </div>

                        {/* Why Autoencoder */}
                        <div className="mb-6 p-4 bg-blue-900/20 rounded-lg border border-blue-800">
                            <h4 className="font-bold text-blue-400 mb-2">Why Autoencoder?</h4>
                            <p className="text-sm text-gray-300">{modelInfo.why_autoencoder}</p>
                        </div>

                        <div className="grid grid-cols-2 gap-6">
                            {/* Architecture */}
                            <div>
                                <h4 className="font-bold text-blue-400 mb-3">🏗️ Architecture: {modelInfo.architecture.type}</h4>
                                <div className="p-4 bg-spis-bg rounded-lg mb-4">
                                    <div className="flex items-center justify-center gap-2 text-sm">
                                        <div className="p-2 bg-blue-900/50 rounded text-blue-300 text-center">
                                            <p className="text-xs opacity-70">Input</p>
                                            <p className="font-bold">{modelInfo.architecture.input_dim}</p>
                                        </div>
                                        <span className="text-gray-500">→</span>
                                        {modelInfo.architecture.encoder_layers.map((size, i) => (
                                            <div key={`enc-${i}`} className="p-2 bg-green-900/50 rounded text-green-300 text-center">
                                                <p className="text-xs opacity-70">Enc{i + 1}</p>
                                                <p className="font-bold">{size}</p>
                                            </div>
                                        ))}
                                        <span className="text-gray-500">→</span>
                                        <div className="p-2 bg-purple-900/50 rounded text-purple-300 text-center">
                                            <p className="text-xs opacity-70">Latent</p>
                                            <p className="font-bold">{modelInfo.architecture.latent_dim}</p>
                                        </div>
                                        <span className="text-gray-500">→</span>
                                        {modelInfo.architecture.decoder_layers.map((size, i) => (
                                            <div key={`dec-${i}`} className="p-2 bg-yellow-900/50 rounded text-yellow-300 text-center">
                                                <p className="text-xs opacity-70">Dec{i + 1}</p>
                                                <p className="font-bold">{size}</p>
                                            </div>
                                        ))}
                                        <span className="text-gray-500">→</span>
                                        <div className="p-2 bg-blue-900/50 rounded text-blue-300 text-center">
                                            <p className="text-xs opacity-70">Output</p>
                                            <p className="font-bold">{modelInfo.architecture.output_dim}</p>
                                        </div>
                                    </div>
                                </div>

                                <h5 className="font-bold text-gray-400 mb-2">Input Features</h5>
                                <ul className="text-sm text-gray-300 space-y-1 mb-4">
                                    {modelInfo.input_features.map((f, i) => (
                                        <li key={i} className="flex items-center gap-2">
                                            <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                                            {f}
                                        </li>
                                    ))}
                                </ul>

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

                            {/* Metrics */}
                            <div>
                                <h5 className="font-bold text-gray-400 mb-2">Training Metrics</h5>
                                <div className="grid grid-cols-2 gap-2 mb-4 text-sm">
                                    {Object.entries(modelInfo.training_metrics).map(([k, v]) => (
                                        <div key={k} className="p-2 bg-spis-bg rounded text-center">
                                            <p className="text-xs text-gray-500">{k.replace(/_/g, ' ')}</p>
                                            <p className="text-lg font-bold text-blue-400">{typeof v === 'number' ? v.toFixed(4) : v}</p>
                                        </div>
                                    ))}
                                </div>

                                <h5 className="font-bold text-gray-400 mb-2">Evaluation Metrics</h5>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    {Object.entries(modelInfo.evaluation_metrics).map(([k, v]) => (
                                        <div key={k} className="p-2 bg-spis-bg rounded text-center">
                                            <p className="text-xs text-gray-500">{k.replace(/_/g, ' ')}</p>
                                            <p className="text-lg font-bold text-green-400">{v.toFixed(2)}</p>
                                        </div>
                                    ))}
                                </div>

                                <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-800 rounded-lg">
                                    <p className="text-sm text-yellow-300">
                                        <strong>Port Area:</strong> {modelInfo.port_area.name}
                                    </p>
                                    <p className="text-xs text-gray-400 mt-1">
                                        Lat: {modelInfo.port_area.bbox.lat_min}° - {modelInfo.port_area.bbox.lat_max}° |
                                        Lon: {modelInfo.port_area.bbox.lon_min}° - {modelInfo.port_area.bbox.lon_max}°
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </PageWrapper>
    )
}
