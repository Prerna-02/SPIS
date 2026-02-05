'use client'

import { useState, useEffect, useCallback } from 'react'
import PageWrapper from '../components/PageWrapper'

// ============================================================
// TYPES
// ============================================================
interface Vessel {
    mmsi: string
    status: string
    zone: string
    lat?: number
    lon?: number
    sog?: number
    eta_to_port?: string
}

interface Berth {
    berth_id: string
    terminal: string
    capacity_class: string
    max_vessels: number
}

interface Asset {
    asset_id: string
    asset_type: string
    operation_state: string
    health_score: number
}

interface Snapshot {
    vessels: {
        approaching: Vessel[]
        waiting: Vessel[]
        berthed: Vessel[]
        total: number
    }
    berths: Berth[]
    assets: Asset[]
    summary: {
        vessels_approaching: number
        vessels_waiting: number
        vessels_berthed: number
        berths_total: number
        assets_total: number
    }
}

interface Assignment {
    vessel_mmsi: string
    vessel_name: string
    berth_id: string
    start_time: string
    end_time: string
    delay_hours: number
}

interface Impact {
    vessel_mmsi: string
    vessel_name: string
    delay_hours: number
    reason: string
}

interface Plan {
    plan_id: string
    objective_score: number
    total_delay_hours: number
    assignments: Assignment[]
    impacts: Impact[]
}

interface ModelInfo {
    knowledge_graph: {
        problem_statement: string
        why_kg: string[]
        entities: { name: string; description: string; properties: string[] }[]
        relationships: string[]
        business_value: string
    }
    cpsat_optimizer: {
        problem_statement: string
        why_cpsat: string[]
        alternatives_considered: Record<string, string>
        constraints: { hard: string[]; soft: string[] }
    }
    objective_score: {
        description: string
        components: { name: string; weight: number; description: string }[]
        formula: string
    }
    cascade_impact: {
        concept: string
        how_kg_helps: string
        visualization: string
    }
}

// ============================================================
// CONSTANTS
// ============================================================
const API_BASE = 'http://localhost:8000'
const TABS = ['Knowledge Graph', 'Scenario Builder', 'Optimizer & Cascade']

// ============================================================
// COMPONENT
// ============================================================
export default function OptimizationPage() {
    const [activeTab, setActiveTab] = useState(0)
    const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
    const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null)
    const [plan, setPlan] = useState<Plan | null>(null)
    const [running, setRunning] = useState(false)
    const [scenarioId, setScenarioId] = useState<string | null>(null)
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
    const [error, setError] = useState<string | null>(null)

    // Scenario form state
    const [extraVessel, setExtraVessel] = useState({
        eta: '',
        containers_est: 150,
        cargo_priority: 'general'
    })

    // Fetch snapshot
    const fetchSnapshot = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/kg/snapshot`)
            if (res.ok) {
                const data = await res.json()
                setSnapshot(data)
                setLastUpdate(new Date())
                setError(null)
            }
        } catch (err) {
            console.error('Snapshot fetch error:', err)
            setError('Failed to fetch snapshot')
        }
    }, [])

    // Fetch model info
    const fetchModelInfo = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/kg/model-info`)
            if (res.ok) {
                setModelInfo(await res.json())
            }
        } catch (err) {
            console.error('Model info fetch error:', err)
        }
    }, [])

    // Initial load
    useEffect(() => {
        fetchSnapshot()
        fetchModelInfo()
    }, [fetchSnapshot, fetchModelInfo])

    // Auto-refresh snapshot
    useEffect(() => {
        const interval = setInterval(fetchSnapshot, 15000)
        return () => clearInterval(interval)
    }, [fetchSnapshot])

    // Create scenario
    const createScenario = async () => {
        setError(null)
        try {
            const res = await fetch(`${API_BASE}/optimizer/scenario`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    extra_vessel: {
                        eta: extraVessel.eta || new Date(Date.now() + 3 * 3600000).toISOString(),
                        containers_est: extraVessel.containers_est,
                        cargo_priority: extraVessel.cargo_priority
                    },
                    allow_overtime: false,
                    max_wait_hours: 24,
                    risk_tolerance: 'medium'
                })
            })
            if (res.ok) {
                const data = await res.json()
                setScenarioId(data.scenario_id)
                setActiveTab(2) // Switch to optimizer tab
            } else {
                setError('Failed to create scenario')
            }
        } catch (err) {
            console.error('Create scenario error:', err)
            setError('Failed to create scenario: ' + (err as Error).message)
        }
    }

    // Run optimization
    const runOptimization = async () => {
        setRunning(true)
        setError(null)
        try {
            // Create a quick scenario if none exists
            let sid = scenarioId
            if (!sid) {
                const createRes = await fetch(`${API_BASE}/optimizer/scenario`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        extra_vessel: {
                            eta: new Date(Date.now() + 2 * 3600000).toISOString(),
                            containers_est: 200,
                            cargo_priority: 'electronics'
                        }
                    })
                })
                if (createRes.ok) {
                    const data = await createRes.json()
                    sid = data.scenario_id
                    setScenarioId(sid)
                }
            }

            if (sid) {
                const res = await fetch(`${API_BASE}/optimizer/run?scenario_id=${sid}`, { method: 'POST' })
                if (res.ok) {
                    const data = await res.json()
                    // Fetch full plan details from /plans/{plan_id}
                    if (data.plans && data.plans.length > 0) {
                        const bestPlanSummary = data.plans[0]

                        // Fetch detailed plan with assignments
                        const planRes = await fetch(`${API_BASE}/plans/${bestPlanSummary.plan_id}`)
                        if (planRes.ok) {
                            const fullPlan = await planRes.json()
                            setPlan({
                                plan_id: fullPlan.plan_id,
                                // Score is already 0-100 from backend
                                objective_score: fullPlan.objective_score > 1 ? fullPlan.objective_score : fullPlan.objective_score * 100,
                                total_delay_hours: fullPlan.total_delay_hours,
                                assignments: fullPlan.assignments.map((a: { vessel_mmsi: string; berth_id: string; formatted_start: string; formatted_end: string; delay_minutes: number; is_extra_vessel?: boolean }) => ({
                                    vessel_mmsi: a.vessel_mmsi,
                                    vessel_name: a.is_extra_vessel ? `EXTRA-${a.vessel_mmsi.slice(-4)}` : `VESSEL-${a.vessel_mmsi.slice(-4)}`,
                                    berth_id: a.berth_id,
                                    start_time: a.formatted_start,
                                    end_time: a.formatted_end,
                                    delay_hours: a.delay_minutes / 60
                                })),
                                impacts: fullPlan.impacts.map((i: { vessel_mmsi: string; delay_hours: number; reason: string }) => ({
                                    vessel_mmsi: i.vessel_mmsi,
                                    vessel_name: `VESSEL-${i.vessel_mmsi.slice(-4)}`,
                                    delay_hours: i.delay_hours,
                                    reason: i.reason
                                }))
                            })
                        } else {
                            // Fallback: use summary data
                            setPlan({
                                plan_id: bestPlanSummary.plan_id,
                                objective_score: bestPlanSummary.objective_score > 1 ? bestPlanSummary.objective_score : bestPlanSummary.objective_score * 100,
                                total_delay_hours: bestPlanSummary.total_delay_hours,
                                assignments: [],
                                impacts: []
                            })
                            setError('Plan details not available - showing summary only')
                        }
                    }
                } else {
                    setError('Optimization failed')
                }
            }
        } catch (err) {
            console.error('Optimization error:', err)
            setError('Optimization error: ' + (err as Error).message)
        } finally {
            setRunning(false)
        }
    }

    return (
        <PageWrapper title="🗺️ Knowledge Graph + Optimization" subtitle="Intelligent berth assignment with cascade impact analysis">
            <div className="space-y-6">
                {/* Controls */}
                <div className="flex justify-end items-center gap-3">
                    <span className="text-sm text-sky-100">
                        Last update: {lastUpdate?.toLocaleTimeString() || '-'}
                    </span>
                    <button
                        onClick={fetchSnapshot}
                        className="px-4 py-2 backdrop-blur bg-white/10 border border-white/20 rounded-lg text-white hover:bg-white/20"
                    >
                        🔄 Refresh
                    </button>
                </div>

                {/* Error Banner */}
                {error && (
                    <div className="p-4 bg-red-900/30 border border-red-500 rounded-lg text-red-300">
                        ⚠️ {error}
                    </div>
                )}

                {/* Tabs */}
                <div className="flex gap-2 border-b border-spis-border pb-2">
                    {TABS.map((tab, i) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(i)}
                            className={`px-6 py-3 rounded-t-lg font-medium transition ${activeTab === i
                                ? 'bg-blue-600 text-white'
                                : 'bg-spis-card text-gray-400 hover:bg-spis-border hover:text-white'
                                }`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                {/* ============================================================ */}
                {/* TAB 1: KNOWLEDGE GRAPH */}
                {/* ============================================================ */}
                {activeTab === 0 && modelInfo && (
                    <div className="space-y-6">
                        {/* Problem Statement */}
                        <div className="card border-purple-500">
                            <h3 className="text-xl font-bold text-purple-400 mb-3">📋 Why Knowledge Graph?</h3>
                            <p className="text-gray-300 leading-relaxed">{modelInfo.knowledge_graph.problem_statement}</p>
                        </div>

                        {/* Key Benefits */}
                        <div className="card">
                            <h3 className="text-lg font-bold text-white mb-4">🎯 Key Benefits</h3>
                            <div className="grid grid-cols-2 gap-4">
                                {modelInfo.knowledge_graph.why_kg.map((benefit, i) => (
                                    <div key={i} className="flex items-start gap-3 p-3 bg-spis-bg rounded-lg">
                                        <span className="text-green-400 text-xl">✓</span>
                                        <span className="text-gray-300">{benefit}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Interactive Graph Visualization */}
                        <div className="card">
                            <h3 className="text-lg font-bold text-white mb-4">🔗 Knowledge Graph Visualization</h3>
                            <div className="bg-spis-bg rounded-lg p-4 relative" style={{ height: '400px' }}>
                                <svg width="100%" height="100%" viewBox="0 0 800 380">
                                    {/* Zone Nodes - Hubs */}
                                    <circle cx="200" cy="190" r="45" fill="#9333ea" opacity="0.9" />
                                    <text x="200" y="195" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">BERTH</text>

                                    <circle cx="600" cy="190" r="45" fill="#9333ea" opacity="0.9" />
                                    <text x="600" y="195" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">ANCHORAGE</text>

                                    <circle cx="400" cy="60" r="35" fill="#ec4899" opacity="0.8" />
                                    <text x="400" y="65" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">APPROACH</text>

                                    {/* Vessels connected to BERTH zone */}
                                    {snapshot?.vessels.berthed.map((v, i) => {
                                        const angle = (i * 60 - 90) * Math.PI / 180
                                        const x = 200 + 120 * Math.cos(angle)
                                        const y = 190 + 100 * Math.sin(angle)
                                        return (
                                            <g key={v.mmsi}>
                                                <line x1="200" y1="190" x2={x} y2={y} stroke="#6366f1" strokeWidth="2" opacity="0.7" />
                                                <circle cx={x} cy={y} r="28" fill="#1e3a8a" stroke="#3b82f6" strokeWidth="2" />
                                                <text x={x} y={y - 5} textAnchor="middle" fill="#93c5fd" fontSize="9">VESSEL</text>
                                                <text x={x} y={y + 8} textAnchor="middle" fill="white" fontSize="8">{v.mmsi.slice(-4)}</text>
                                            </g>
                                        )
                                    })}

                                    {/* Vessels connected to ANCHORAGE */}
                                    {snapshot?.vessels.waiting.map((v, i) => {
                                        const angle = (i * 45 - 60) * Math.PI / 180
                                        const x = 600 + 120 * Math.cos(angle)
                                        const y = 190 + 100 * Math.sin(angle)
                                        return (
                                            <g key={v.mmsi}>
                                                <line x1="600" y1="190" x2={x} y2={y} stroke="#f59e0b" strokeWidth="2" opacity="0.7" />
                                                <circle cx={x} cy={y} r="28" fill="#78350f" stroke="#f59e0b" strokeWidth="2" />
                                                <text x={x} y={y - 5} textAnchor="middle" fill="#fcd34d" fontSize="9">WAITING</text>
                                                <text x={x} y={y + 8} textAnchor="middle" fill="white" fontSize="8">{v.mmsi.slice(-4)}</text>
                                            </g>
                                        )
                                    })}

                                    {/* Vessels connected to APPROACH */}
                                    {snapshot?.vessels.approaching.slice(0, 4).map((v, i) => {
                                        const angle = (i * 50 - 75) * Math.PI / 180
                                        const x = 400 + 90 * Math.cos(angle)
                                        const y = 60 + 80 * Math.sin(angle)
                                        return (
                                            <g key={v.mmsi}>
                                                <line x1="400" y1="60" x2={x} y2={y} stroke="#22c55e" strokeWidth="2" opacity="0.7" />
                                                <circle cx={x} cy={y} r="25" fill="#14532d" stroke="#22c55e" strokeWidth="2" />
                                                <text x={x} y={y - 5} textAnchor="middle" fill="#86efac" fontSize="8">APPROACH</text>
                                                <text x={x} y={y + 7} textAnchor="middle" fill="white" fontSize="8">{v.mmsi.slice(-4)}</text>
                                            </g>
                                        )
                                    })}

                                    {/* Berths connected to BERTH zone */}
                                    {snapshot?.berths.slice(0, 4).map((b, i) => {
                                        const angle = (i * 45 + 135) * Math.PI / 180
                                        const x = 200 + 130 * Math.cos(angle)
                                        const y = 190 + 110 * Math.sin(angle)
                                        return (
                                            <g key={b.berth_id}>
                                                <line x1="200" y1="190" x2={x} y2={y} stroke="#10b981" strokeWidth="2" opacity="0.7" />
                                                <rect x={x - 30} y={y - 18} width="60" height="36" rx="6" fill="#064e3b" stroke="#10b981" strokeWidth="2" />
                                                <text x={x} y={y - 2} textAnchor="middle" fill="#6ee7b7" fontSize="9">BERTH</text>
                                                <text x={x} y={y + 10} textAnchor="middle" fill="white" fontSize="8">{b.berth_id.split('_')[1] || b.berth_id}</text>
                                            </g>
                                        )
                                    })}

                                    {/* Zone connections */}
                                    <line x1="245" y1="190" x2="355" y2="95" stroke="#a855f7" strokeWidth="2" strokeDasharray="5,5" opacity="0.5" />
                                    <line x1="445" y1="95" x2="555" y2="190" stroke="#a855f7" strokeWidth="2" strokeDasharray="5,5" opacity="0.5" />

                                    {/* Legend */}
                                    <g transform="translate(650, 320)">
                                        <circle cx="0" cy="0" r="8" fill="#9333ea" />
                                        <text x="15" y="4" fill="#d8b4fe" fontSize="10">Zone</text>
                                        <circle cx="0" cy="20" r="8" fill="#1e3a8a" stroke="#3b82f6" strokeWidth="1" />
                                        <text x="15" y="24" fill="#93c5fd" fontSize="10">Vessel</text>
                                        <rect x="-8" y="32" width="16" height="12" rx="2" fill="#064e3b" stroke="#10b981" strokeWidth="1" />
                                        <text x="15" y="44" fill="#6ee7b7" fontSize="10">Berth</text>
                                    </g>
                                </svg>
                            </div>
                            <p className="text-sm text-gray-400 mt-2 text-center">
                                💡 Live graph from Neo4j showing zones, vessels, and berths
                            </p>
                        </div>

                        {/* Entity Cards */}
                        <div className="card">
                            <h3 className="text-lg font-bold text-white mb-4">📦 Entity Types</h3>
                            <div className="grid grid-cols-5 gap-3">
                                {modelInfo.knowledge_graph.entities.map((entity) => (
                                    <div key={entity.name} className={`p-3 rounded-lg text-center ${entity.name === 'Vessel' ? 'bg-blue-900/50 border border-blue-500' :
                                        entity.name === 'Berth' ? 'bg-green-900/50 border border-green-500' :
                                            entity.name === 'Asset' ? 'bg-yellow-900/50 border border-yellow-500' :
                                                entity.name === 'YardBlock' ? 'bg-purple-900/50 border border-purple-500' :
                                                    'bg-gray-700 border border-gray-500'
                                        }`}>
                                        <p className={`font-bold ${entity.name === 'Vessel' ? 'text-blue-300' :
                                            entity.name === 'Berth' ? 'text-green-300' :
                                                entity.name === 'Asset' ? 'text-yellow-300' :
                                                    entity.name === 'YardBlock' ? 'text-purple-300' :
                                                        'text-gray-300'
                                            }`}>{entity.name}</p>
                                        <p className="text-xs text-gray-400 mt-1">{entity.description}</p>
                                    </div>
                                ))}
                            </div>
                            <div className="mt-4 grid grid-cols-2 gap-2">
                                {modelInfo.knowledge_graph.relationships.map((rel, i) => (
                                    <code key={i} className="text-sm text-cyan-400 bg-spis-bg p-2 rounded">{rel}</code>
                                ))}
                            </div>
                        </div>

                        {/* Live Snapshot */}
                        {snapshot && (
                            <div className="card border-blue-500">
                                <h3 className="text-lg font-bold text-blue-400 mb-4">📊 Live Port Snapshot (Neo4j)</h3>
                                <div className="grid grid-cols-5 gap-4 mb-6">
                                    <div className="p-4 bg-blue-900/20 rounded-lg text-center">
                                        <p className="text-3xl font-bold text-blue-400">{snapshot.summary.vessels_approaching}</p>
                                        <p className="text-sm text-gray-400">Approaching</p>
                                    </div>
                                    <div className="p-4 bg-yellow-900/20 rounded-lg text-center">
                                        <p className="text-3xl font-bold text-yellow-400">{snapshot.summary.vessels_waiting}</p>
                                        <p className="text-sm text-gray-400">Waiting</p>
                                    </div>
                                    <div className="p-4 bg-green-900/20 rounded-lg text-center">
                                        <p className="text-3xl font-bold text-green-400">{snapshot.summary.vessels_berthed}</p>
                                        <p className="text-sm text-gray-400">Berthed</p>
                                    </div>
                                    <div className="p-4 bg-purple-900/20 rounded-lg text-center">
                                        <p className="text-3xl font-bold text-purple-400">{snapshot.summary.berths_total}</p>
                                        <p className="text-sm text-gray-400">Berths</p>
                                    </div>
                                    <div className="p-4 bg-cyan-900/20 rounded-lg text-center">
                                        <p className="text-3xl font-bold text-cyan-400">{snapshot.summary.assets_total}</p>
                                        <p className="text-sm text-gray-400">Assets</p>
                                    </div>
                                </div>

                                {/* Vessel List */}
                                <div className="grid grid-cols-3 gap-4">
                                    <div>
                                        <h4 className="text-sm font-bold text-blue-400 mb-2">Approaching ({snapshot.vessels.approaching.length})</h4>
                                        {snapshot.vessels.approaching.map(v => (
                                            <div key={v.mmsi} className="p-2 bg-spis-bg rounded mb-1">
                                                <span className="font-mono text-sm text-white">{v.mmsi}</span>
                                                <span className="text-xs text-gray-400 ml-2">{v.zone}</span>
                                            </div>
                                        ))}
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-bold text-yellow-400 mb-2">Waiting ({snapshot.vessels.waiting.length})</h4>
                                        {snapshot.vessels.waiting.map(v => (
                                            <div key={v.mmsi} className="p-2 bg-spis-bg rounded mb-1">
                                                <span className="font-mono text-sm text-white">{v.mmsi}</span>
                                            </div>
                                        ))}
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-bold text-green-400 mb-2">Berthed ({snapshot.vessels.berthed.length})</h4>
                                        {snapshot.vessels.berthed.map(v => (
                                            <div key={v.mmsi} className="p-2 bg-spis-bg rounded mb-1">
                                                <span className="font-mono text-sm text-white">{v.mmsi}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Business Value */}
                        <div className="card border-green-500">
                            <h3 className="text-lg font-bold text-green-400 mb-3">💡 Business Value</h3>
                            <p className="text-gray-300">{modelInfo.knowledge_graph.business_value}</p>
                        </div>
                    </div>
                )}

                {/* ============================================================ */}
                {/* TAB 2: SCENARIO BUILDER */}
                {/* ============================================================ */}
                {activeTab === 1 && (
                    <div className="space-y-6">
                        {/* Explanation */}
                        <div className="card border-purple-500">
                            <h3 className="text-xl font-bold text-purple-400 mb-3">🧪 What-If Scenario Builder</h3>
                            <p className="text-gray-300">
                                Add a hypothetical vessel to see how the port would handle it. This helps answer questions like:
                                &quot;If a large container ship arrives unexpectedly, which berth should it use? Which vessels will be delayed?&quot;
                            </p>
                        </div>

                        {/* Current Port Status */}
                        {snapshot && (
                            <div className="card">
                                <h3 className="text-lg font-bold text-white mb-4">📊 Current Port Status</h3>
                                <div className="grid grid-cols-4 gap-4">
                                    <div className="text-center">
                                        <p className="text-4xl font-bold text-blue-400">{snapshot.summary.vessels_approaching + snapshot.summary.vessels_waiting}</p>
                                        <p className="text-sm text-gray-400">Vessels Incoming</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="text-4xl font-bold text-green-400">{snapshot.summary.berths_total - snapshot.summary.vessels_berthed}</p>
                                        <p className="text-sm text-gray-400">Berths Available</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="text-4xl font-bold text-yellow-400">{snapshot.summary.vessels_berthed}</p>
                                        <p className="text-sm text-gray-400">Berths Occupied</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="text-4xl font-bold text-cyan-400">{snapshot.summary.assets_total}</p>
                                        <p className="text-sm text-gray-400">Active Assets</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Add Hypothetical Vessel Form */}
                        <div className="card border-blue-500">
                            <h3 className="text-lg font-bold text-blue-400 mb-4">➕ Add Hypothetical Vessel</h3>
                            <div className="grid grid-cols-3 gap-6">
                                <div>
                                    <label className="block text-sm text-gray-400 mb-2">Expected Arrival (ETA)</label>
                                    <input
                                        type="datetime-local"
                                        value={extraVessel.eta}
                                        onChange={(e) => setExtraVessel({ ...extraVessel, eta: e.target.value })}
                                        className="w-full p-3 bg-spis-bg border border-spis-border rounded-lg text-white"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-gray-400 mb-2">Estimated Containers (TEU)</label>
                                    <input
                                        type="number"
                                        value={extraVessel.containers_est}
                                        onChange={(e) => setExtraVessel({ ...extraVessel, containers_est: parseInt(e.target.value) })}
                                        className="w-full p-3 bg-spis-bg border border-spis-border rounded-lg text-white"
                                        min={50}
                                        max={500}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-gray-400 mb-2">Cargo Priority</label>
                                    <select
                                        value={extraVessel.cargo_priority}
                                        onChange={(e) => setExtraVessel({ ...extraVessel, cargo_priority: e.target.value })}
                                        className="w-full p-3 bg-spis-bg border border-spis-border rounded-lg text-white"
                                    >
                                        <option value="general">General Cargo</option>
                                        <option value="electronics">Electronics</option>
                                        <option value="food">Perishable Food</option>
                                        <option value="pharma">Pharmaceuticals (Urgent)</option>
                                    </select>
                                </div>
                            </div>
                            <button
                                onClick={createScenario}
                                className="mt-6 px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition"
                            >
                                🚀 Create Scenario & Optimize
                            </button>
                        </div>

                        {/* Scenario Created */}
                        {scenarioId && (
                            <div className="card border-green-500">
                                <p className="text-green-400">✅ Scenario created: <code className="bg-spis-bg px-2 py-1 rounded">{scenarioId}</code></p>
                                <p className="text-sm text-gray-400 mt-2">Switch to the &quot;Optimizer & Cascade&quot; tab to run optimization.</p>
                            </div>
                        )}
                    </div>
                )}

                {/* ============================================================ */}
                {/* TAB 3: OPTIMIZER & CASCADE */}
                {/* ============================================================ */}
                {activeTab === 2 && modelInfo && (
                    <div className="space-y-6">
                        {/* CP-SAT Explanation */}
                        <div className="card border-purple-500">
                            <h3 className="text-xl font-bold text-purple-400 mb-3">⚡ Why CP-SAT Optimizer?</h3>
                            <p className="text-gray-300 mb-4">{modelInfo.cpsat_optimizer.problem_statement}</p>
                            <div className="grid grid-cols-2 gap-4">
                                {modelInfo.cpsat_optimizer.why_cpsat.map((reason, i) => (
                                    <div key={i} className="flex items-start gap-3 p-3 bg-spis-bg rounded-lg">
                                        <span className="text-purple-400 text-xl">{i + 1}.</span>
                                        <span className="text-gray-300">{reason}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Alternatives Comparison */}
                        <div className="card">
                            <h3 className="text-lg font-bold text-white mb-4">🔄 Alternatives Considered</h3>
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-spis-border">
                                        <th className="text-left py-2 text-gray-400">Method</th>
                                        <th className="text-left py-2 text-gray-400">Trade-off</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {Object.entries(modelInfo.cpsat_optimizer.alternatives_considered).map(([method, tradeoff]) => (
                                        <tr key={method} className={`border-b border-spis-border/50 ${method === 'CP-SAT' ? 'bg-green-900/20' : ''}`}>
                                            <td className={`py-3 ${method === 'CP-SAT' ? 'text-green-400 font-bold' : 'text-white'}`}>{method}</td>
                                            <td className="py-3 text-gray-300">{tradeoff}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Constraints */}
                        <div className="grid grid-cols-2 gap-6">
                            <div className="card border-red-500">
                                <h3 className="text-lg font-bold text-red-400 mb-3">🚫 Hard Constraints (Must Satisfy)</h3>
                                <ul className="space-y-2">
                                    {modelInfo.cpsat_optimizer.constraints.hard.map((c, i) => (
                                        <li key={i} className="flex items-center gap-2 text-gray-300">
                                            <span className="text-red-400">◆</span> {c}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="card border-yellow-500">
                                <h3 className="text-lg font-bold text-yellow-400 mb-3">📈 Soft Constraints (Optimize)</h3>
                                <ul className="space-y-2">
                                    {modelInfo.cpsat_optimizer.constraints.soft.map((c, i) => (
                                        <li key={i} className="flex items-center gap-2 text-gray-300">
                                            <span className="text-yellow-400">◇</span> {c}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Objective Score Breakdown */}
                        <div className="card border-blue-500">
                            <h3 className="text-lg font-bold text-blue-400 mb-3">🎯 Objective Score Breakdown</h3>
                            <p className="text-gray-300 mb-4">{modelInfo.objective_score.description}</p>
                            <div className="grid grid-cols-4 gap-4 mb-4">
                                {modelInfo.objective_score.components.map((comp, i) => (
                                    <div key={i} className="p-4 bg-spis-bg rounded-lg text-center">
                                        <p className="text-2xl font-bold text-blue-400">{(comp.weight * 100).toFixed(0)}%</p>
                                        <p className="text-sm font-medium text-white">{comp.name}</p>
                                        <p className="text-xs text-gray-400 mt-1">{comp.description}</p>
                                    </div>
                                ))}
                            </div>
                            <code className="block p-3 bg-spis-bg rounded text-cyan-400 text-sm">{modelInfo.objective_score.formula}</code>
                        </div>

                        {/* Run Optimization */}
                        <div className="card">
                            <div className="flex justify-between items-center">
                                <div>
                                    <h3 className="text-lg font-bold text-white">🚀 Run Optimization</h3>
                                    <p className="text-sm text-gray-400">
                                        {scenarioId ? `Scenario: ${scenarioId}` : 'No scenario - will create default'}
                                    </p>
                                </div>
                                <button
                                    onClick={runOptimization}
                                    disabled={running}
                                    className={`px-8 py-3 rounded-lg font-bold text-lg transition ${running ? 'bg-gray-600 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'
                                        } text-white`}
                                >
                                    {running ? '⏳ Optimizing...' : '▶️ Run Optimizer'}
                                </button>
                            </div>
                        </div>

                        {/* Results */}
                        {plan && (
                            <>
                                {/* Score Card */}
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="card border-green-500">
                                        <p className="text-sm text-gray-400">Objective Score</p>
                                        <p className="text-4xl font-bold text-green-400">{plan.objective_score.toFixed(1)}</p>
                                    </div>
                                    <div className="card">
                                        <p className="text-sm text-gray-400">Vessels Assigned</p>
                                        <p className="text-4xl font-bold text-blue-400">{plan.assignments.length}</p>
                                    </div>
                                    <div className="card border-yellow-500">
                                        <p className="text-sm text-gray-400">Total Delay</p>
                                        <p className="text-4xl font-bold text-yellow-400">{plan.total_delay_hours.toFixed(1)}h</p>
                                    </div>
                                </div>

                                {/* Berth Timeline - Scrollable */}
                                <div className="card">
                                    <h3 className="text-lg font-bold text-white mb-4">📅 Berth Timeline (scroll →)</h3>
                                    <div className="space-y-3">
                                        {['OLDCITY_B1', 'OLDCITY_B2', 'MUUGA_B1', 'MUUGA_B2'].map((berth) => {
                                            const berthAssignments = plan.assignments.filter(a => a.berth_id === berth)
                                            // Sort by start time
                                            berthAssignments.sort((x, y) => {
                                                const xStart = parseInt(x.start_time?.split(':')[0] || '0') * 60 + parseInt(x.start_time?.split(':')[1] || '0')
                                                const yStart = parseInt(y.start_time?.split(':')[0] || '0') * 60 + parseInt(y.start_time?.split(':')[1] || '0')
                                                return xStart - yStart
                                            })
                                            return (
                                                <div key={berth} className="flex items-center gap-4">
                                                    <span className="w-24 text-sm text-gray-400 font-mono flex-shrink-0">{berth}</span>
                                                    <div className="flex-1 overflow-x-auto">
                                                        <div className="flex gap-1 min-w-max h-10">
                                                            {berthAssignments.map((a, i) => (
                                                                <div
                                                                    key={i}
                                                                    className={`h-full rounded px-2 flex items-center justify-center ${a.delay_hours > 0 ? 'bg-yellow-600' : 'bg-green-600'}`}
                                                                    style={{ minWidth: '100px' }}
                                                                    title={`${a.vessel_name || a.vessel_mmsi}\n${a.start_time} - ${a.end_time}\nDelay: ${a.delay_hours?.toFixed(1) || 0}h`}
                                                                >
                                                                    <span className="text-xs text-white font-medium truncate">
                                                                        {a.vessel_name?.slice(0, 12) || a.vessel_mmsi?.slice(-6)}
                                                                    </span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>
                                    <p className="text-xs text-gray-500 mt-2">Green = on-time, Yellow = delayed. Hover for details.</p>
                                </div>

                                {/* Assignments Table */}
                                <div className="card">
                                    <h3 className="text-lg font-bold text-white mb-4">🚢 Assignments</h3>
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-spis-border">
                                                <th className="text-left py-2 text-gray-400">MMSI</th>
                                                <th className="text-left py-2 text-gray-400">Vessel</th>
                                                <th className="text-left py-2 text-gray-400">Berth</th>
                                                <th className="text-left py-2 text-gray-400">Window</th>
                                                <th className="text-right py-2 text-gray-400">Delay</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {plan.assignments.map((a, i) => (
                                                <tr key={i} className="border-b border-spis-border/50">
                                                    <td className="py-2 font-mono text-gray-300">{a.vessel_mmsi}</td>
                                                    <td className="py-2 text-white">{a.vessel_name}</td>
                                                    <td className="py-2 text-blue-400">{a.berth_id}</td>
                                                    <td className="py-2 text-gray-300">{a.start_time} - {a.end_time}</td>
                                                    <td className="py-2 text-right">
                                                        <span className={a.delay_hours > 0 ? 'text-yellow-400' : 'text-green-400'}>
                                                            {a.delay_hours > 0 ? `+${a.delay_hours.toFixed(1)}h` : '—'}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                {/* Cascade Impact */}
                                {plan.impacts.length > 0 && (
                                    <div className="card border-yellow-500">
                                        <h3 className="text-xl font-bold text-yellow-400 mb-4">⚡ Cascade Impact</h3>
                                        <p className="text-gray-300 mb-4">{modelInfo.cascade_impact.concept}</p>
                                        <div className="space-y-3">
                                            {plan.impacts.map((impact, i) => (
                                                <div key={i} className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-4 flex justify-between items-center">
                                                    <div>
                                                        <p className="text-white font-bold">{impact.vessel_name}</p>
                                                        <p className="text-sm text-gray-400">MMSI: {impact.vessel_mmsi}</p>
                                                        <p className="text-sm text-yellow-200 mt-1">🔗 {impact.reason}</p>
                                                    </div>
                                                    <span className="text-2xl font-bold text-yellow-400">+{impact.delay_hours.toFixed(1)}h</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}

                        {/* Business Recommendations */}
                        <div className="card border-green-500">
                            <h3 className="text-lg font-bold text-green-400 mb-4">💡 Business Recommendations</h3>
                            <div className="grid grid-cols-3 gap-4">
                                <div className="p-4 bg-green-900/20 rounded-lg">
                                    <p className="text-2xl mb-2">📊</p>
                                    <h4 className="font-bold text-green-300 mb-2">Monitor Delays</h4>
                                    <p className="text-sm text-gray-300">Track cumulative delay hours. If exceeding 10h/day, consider adding temporary berth capacity.</p>
                                </div>
                                <div className="p-4 bg-blue-900/20 rounded-lg">
                                    <p className="text-2xl mb-2">🔄</p>
                                    <h4 className="font-bold text-blue-300 mb-2">Re-optimize on Change</h4>
                                    <p className="text-sm text-gray-300">Run optimizer when: new vessel arrives, ETA changes by &gt;2h, or crane breaks down.</p>
                                </div>
                                <div className="p-4 bg-purple-900/20 rounded-lg">
                                    <p className="text-2xl mb-2">🎯</p>
                                    <h4 className="font-bold text-purple-300 mb-2">Priority Cargo First</h4>
                                    <p className="text-sm text-gray-300">Pharma and perishables get berth priority. Use scenario builder to test new arrivals.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </PageWrapper>
    )
}
