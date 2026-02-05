'use client'

import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Sky } from '@react-three/drei'
import { useRef, useState, Suspense } from 'react'
import * as THREE from 'three'

// Tallinn Port berth configuration
const BERTHS = [
    { id: 'B1', name: 'Old City Terminal 1', x: -15, z: -5, length: 8, color: '#3b82f6' },
    { id: 'B2', name: 'Old City Terminal 2', x: -15, z: 5, length: 8, color: '#3b82f6' },
    { id: 'B3', name: 'Muuga Terminal 1', x: 15, z: -5, length: 10, color: '#22c55e' },
    { id: 'B4', name: 'Muuga Terminal 2', x: 15, z: 5, length: 10, color: '#22c55e' },
]

const YARD_BLOCKS = [
    { id: 'Y1', x: -20, z: 0, width: 4, depth: 8 },
    { id: 'Y2', x: 20, z: 0, width: 4, depth: 8 },
    { id: 'Y3', x: 0, z: -15, width: 6, depth: 4 },
]

// Vessel types with colors
const VESSEL_TYPES: Record<string, { color: string; emoji: string }> = {
    cargo: { color: '#f59e0b', emoji: '📦' },
    tanker: { color: '#ef4444', emoji: '⛽' },
    passenger: { color: '#8b5cf6', emoji: '🛳️' },
    ferry: { color: '#06b6d4', emoji: '⛴️' },
    fishing: { color: '#10b981', emoji: '🎣' },
    tug: { color: '#6b7280', emoji: '🚤' },
}

interface VesselData {
    id: string
    name: string
    type: string
    position: [number, number, number]
    isMoving: boolean
    targetPosition?: [number, number, number]
}

// Animated Vessel Component
function Vessel({ position, type, isMoving, targetPosition, speed = 0.02 }: {
    position: [number, number, number]
    type: string
    name: string
    isMoving: boolean
    targetPosition?: [number, number, number]
    speed?: number
}) {
    const groupRef = useRef<THREE.Group>(null)

    useFrame((state) => {
        if (groupRef.current && isMoving && targetPosition) {
            const pos = groupRef.current.position
            const dx = targetPosition[0] - pos.x
            const dz = targetPosition[2] - pos.z
            const dist = Math.sqrt(dx * dx + dz * dz)

            if (dist > 0.1) {
                pos.x += (dx / dist) * speed
                pos.z += (dz / dist) * speed
                groupRef.current.rotation.y = Math.atan2(dx, dz)
            }
        }
        if (groupRef.current) {
            groupRef.current.position.y = 0.3 + Math.sin(state.clock.elapsedTime * 2) * 0.05
        }
    })

    const vesselColor = VESSEL_TYPES[type]?.color || '#3b82f6'

    return (
        <group ref={groupRef} position={[position[0], 0.3, position[2]]}>
            {/* Vessel hull */}
            <mesh castShadow>
                <boxGeometry args={[2, 0.6, 0.8]} />
                <meshStandardMaterial color={vesselColor} metalness={0.3} roughness={0.7} />
            </mesh>
            {/* Bridge */}
            <mesh position={[-0.5, 0.5, 0]} castShadow>
                <boxGeometry args={[0.6, 0.4, 0.5]} />
                <meshStandardMaterial color="#1e293b" />
            </mesh>
            {/* Funnel/Stack */}
            <mesh position={[-0.7, 0.7, 0]} castShadow>
                <cylinderGeometry args={[0.1, 0.1, 0.3, 8]} />
                <meshStandardMaterial color="#475569" />
            </mesh>
        </group>
    )
}

// Berth Component
function Berth({ x, z, length, color }: { x: number; z: number; length: number; color: string }) {
    return (
        <group position={[x, 0, z]}>
            {/* Berth platform */}
            <mesh receiveShadow position={[0, 0.1, 0]}>
                <boxGeometry args={[length, 0.3, 2]} />
                <meshStandardMaterial color={color} metalness={0.1} roughness={0.8} />
            </mesh>
            {/* Crane tower */}
            <mesh position={[0, 2, 0.5]} castShadow>
                <boxGeometry args={[0.3, 4, 0.3]} />
                <meshStandardMaterial color="#fbbf24" />
            </mesh>
            {/* Crane arm */}
            <mesh position={[0, 4, -0.5]} castShadow>
                <boxGeometry args={[0.2, 0.2, 3]} />
                <meshStandardMaterial color="#fbbf24" />
            </mesh>
        </group>
    )
}

// Yard Block with containers
function YardBlock({ x, z, width, depth }: { x: number; z: number; width: number; depth: number }) {
    const colors = ['#ef4444', '#3b82f6', '#22c55e', '#f59e0b', '#8b5cf6']
    const containers: JSX.Element[] = []

    // Use deterministic positions based on index
    for (let i = 0; i < 6; i++) {
        for (let j = 0; j < 3; j++) {
            const stackHeight = ((i + j) % 3) + 1
            for (let k = 0; k < stackHeight; k++) {
                containers.push(
                    <mesh
                        key={`container-${i}-${j}-${k}`}
                        position={[
                            x - width / 2 + 0.5 + i * 0.7,
                            0.3 + k * 0.4,
                            z - depth / 2 + 0.5 + j * 0.7
                        ]}
                        castShadow
                    >
                        <boxGeometry args={[0.6, 0.35, 0.25]} />
                        <meshStandardMaterial color={colors[(i + j + k) % colors.length]} />
                    </mesh>
                )
            }
        }
    }

    return (
        <group>
            {/* Yard ground */}
            <mesh receiveShadow position={[x, 0.05, z]}>
                <boxGeometry args={[width, 0.1, depth]} />
                <meshStandardMaterial color="#475569" />
            </mesh>
            {containers}
        </group>
    )
}

// Water plane
function Water() {
    return (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
            <planeGeometry args={[100, 100]} />
            <meshStandardMaterial
                color="#0ea5e9"
                transparent
                opacity={0.85}
                metalness={0.2}
                roughness={0.3}
            />
        </mesh>
    )
}

// Main 3D Scene
function Scene({ vessels }: { vessels: VesselData[] }) {
    return (
        <>
            {/* Lighting */}
            <ambientLight intensity={0.5} />
            <directionalLight
                position={[20, 30, 10]}
                intensity={1}
                castShadow
            />

            {/* Sky */}
            <Sky sunPosition={[100, 20, 100]} />

            {/* Water */}
            <Water />

            {/* Berths */}
            {BERTHS.map((berth) => (
                <Berth key={berth.id} x={berth.x} z={berth.z} length={berth.length} color={berth.color} />
            ))}

            {/* Yard Blocks */}
            {YARD_BLOCKS.map((yard) => (
                <YardBlock key={yard.id} x={yard.x} z={yard.z} width={yard.width} depth={yard.depth} />
            ))}

            {/* Vessels */}
            {vessels.map((vessel) => (
                <Vessel
                    key={vessel.id}
                    position={vessel.position}
                    type={vessel.type}
                    name={vessel.name}
                    isMoving={vessel.isMoving}
                    targetPosition={vessel.targetPosition}
                />
            ))}

            {/* Camera controls */}
            <OrbitControls
                enablePan={true}
                enableZoom={true}
                enableRotate={true}
                minPolarAngle={0.2}
                maxPolarAngle={Math.PI / 2.2}
                minDistance={10}
                maxDistance={80}
            />
        </>
    )
}

// Main exported component
export default function Port3D() {
    const [vessels, setVessels] = useState<VesselData[]>([
        { id: '1', name: 'BALTIC QUEEN', type: 'passenger', position: [-25, 0, 0], isMoving: false },
        { id: '2', name: 'CARGO STAR', type: 'cargo', position: [10, 0, -12], isMoving: false },
        { id: '3', name: 'NORDIC TANKER', type: 'tanker', position: [-10, 0, 15], isMoving: false },
    ])

    const [isSimulating, setIsSimulating] = useState(false)

    const handleSimulate = () => {
        setIsSimulating(true)
        setVessels(prev => prev.map((v, i) => ({
            ...v,
            isMoving: true,
            targetPosition: BERTHS[i % BERTHS.length]
                ? [BERTHS[i % BERTHS.length].x - 5, 0, BERTHS[i % BERTHS.length].z] as [number, number, number]
                : v.position
        })))

        setTimeout(() => {
            setVessels(prev => prev.map(v => ({ ...v, isMoving: false })))
            setIsSimulating(false)
        }, 10000)
    }

    const handleDepart = () => {
        setVessels(prev => {
            if (prev.length === 0) return prev
            const updated = [...prev]
            updated[0] = {
                ...updated[0],
                isMoving: true,
                targetPosition: [40, 0, 0] as [number, number, number]
            }
            return updated
        })

        setTimeout(() => {
            setVessels(prev => prev.slice(1))
        }, 5000)
    }

    const handleAddVessel = () => {
        const types = Object.keys(VESSEL_TYPES)
        const names = ['SEA SPIRIT', 'OCEAN VOYAGER', 'HARBOR KING', 'WAVE RUNNER', 'NORDIC EXPRESS']
        const randomBerth = BERTHS[Math.floor(Math.random() * BERTHS.length)]

        const newVessel: VesselData = {
            id: Date.now().toString(),
            name: names[Math.floor(Math.random() * names.length)],
            type: types[Math.floor(Math.random() * types.length)],
            position: [-35, 0, Math.random() * 20 - 10] as [number, number, number],
            isMoving: true,
            targetPosition: [randomBerth.x - 5, 0, randomBerth.z] as [number, number, number]
        }

        setVessels(prev => [...prev, newVessel])
    }

    return (
        <div className="w-full h-full relative">
            {/* Control Panel */}
            <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
                <button
                    onClick={handleSimulate}
                    disabled={isSimulating}
                    className="px-4 py-2 bg-sky-500 hover:bg-sky-600 disabled:bg-gray-500 text-white rounded-lg font-medium shadow-lg transition flex items-center gap-2"
                >
                    <span>▶️</span>
                    {isSimulating ? 'Simulating...' : 'Simulate Approach'}
                </button>
                <button
                    onClick={handleDepart}
                    className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium shadow-lg transition flex items-center gap-2"
                >
                    <span>🚢</span> Vessel Departs
                </button>
                <button
                    onClick={handleAddVessel}
                    className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium shadow-lg transition flex items-center gap-2"
                >
                    <span>➕</span> Add Vessel
                </button>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 left-4 z-10 bg-slate-900/80 backdrop-blur-sm rounded-lg p-3 text-white text-sm">
                <div className="font-bold mb-2">Vessel Types</div>
                <div className="grid grid-cols-2 gap-1">
                    {Object.entries(VESSEL_TYPES).map(([type, { color, emoji }]) => (
                        <div key={type} className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded" style={{ backgroundColor: color }} />
                            <span>{emoji} {type}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Stats */}
            <div className="absolute top-4 right-4 z-10 bg-slate-900/80 backdrop-blur-sm rounded-lg p-3 text-white">
                <div className="text-lg font-bold">Port Tallinn</div>
                <div className="text-sm text-slate-300">Active Vessels: {vessels.length}</div>
                <div className="text-sm text-slate-300">Berths: {BERTHS.length}</div>
            </div>

            {/* 3D Canvas */}
            <Canvas
                shadows
                camera={{ position: [30, 25, 30], fov: 50 }}
                style={{ background: 'linear-gradient(to bottom, #38bdf8, #0284c7)' }}
            >
                <Suspense fallback={null}>
                    <Scene vessels={vessels} />
                </Suspense>
            </Canvas>
        </div>
    )
}
