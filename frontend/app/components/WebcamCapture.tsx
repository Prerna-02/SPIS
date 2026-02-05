'use client'

import { useRef, useState, useCallback, useEffect } from 'react'

interface WebcamCaptureProps {
    onCapture: (imageBase64: string) => void
    buttonLabel?: string
    className?: string
}

export default function WebcamCapture({ onCapture, buttonLabel = 'Capture', className = '' }: WebcamCaptureProps) {
    const videoRef = useRef<HTMLVideoElement>(null)
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const [stream, setStream] = useState<MediaStream | null>(null)
    const [isActive, setIsActive] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const startCamera = useCallback(async () => {
        try {
            setError(null)
            const mediaStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: 640, height: 480 }
            })
            setStream(mediaStream)
            setIsActive(true)

            // Need to wait for next render, then set srcObject and play
            setTimeout(() => {
                if (videoRef.current) {
                    videoRef.current.srcObject = mediaStream
                    videoRef.current.onloadedmetadata = () => {
                        videoRef.current?.play().catch(console.error)
                    }
                }
            }, 100)
        } catch (err) {
            setError('Camera access denied or not available')
            console.error('Camera error:', err)
        }
    }, [])

    const stopCamera = useCallback(() => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop())
            setStream(null)
        }
        setIsActive(false)
    }, [stream])

    const captureImage = useCallback(() => {
        if (!videoRef.current || !canvasRef.current) return

        const video = videoRef.current
        const canvas = canvasRef.current
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight

        const ctx = canvas.getContext('2d')
        if (!ctx) return

        ctx.drawImage(video, 0, 0)
        const imageData = canvas.toDataURL('image/jpeg', 0.8)

        onCapture(imageData)
        stopCamera()
    }, [onCapture, stopCamera])

    useEffect(() => {
        return () => {
            if (stream) {
                stream.getTracks().forEach(track => track.stop())
            }
        }
    }, [stream])

    return (
        <div className={`webcam-capture ${className}`}>
            {error && (
                <div className="bg-red-900/50 border border-red-500 rounded-lg p-3 text-red-300 text-sm mb-3">
                    {error}
                </div>
            )}

            {!isActive ? (
                <button
                    type="button"
                    onClick={startCamera}
                    className="w-full py-3 px-4 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                >
                    <span>📷</span> Enable Camera
                </button>
            ) : (
                <div className="space-y-3">
                    <div className="relative rounded-lg overflow-hidden bg-gray-900 border border-gray-700">
                        <video
                            ref={videoRef}
                            autoPlay
                            playsInline
                            muted
                            className="w-full"
                        />
                        <div className="absolute top-2 right-2">
                            <span className="animate-pulse text-red-500 text-xl">●</span>
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <button
                            type="button"
                            onClick={captureImage}
                            className="flex-1 py-2 px-4 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
                        >
                            {buttonLabel}
                        </button>
                        <button
                            type="button"
                            onClick={stopCamera}
                            className="py-2 px-4 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            <canvas ref={canvasRef} className="hidden" />
        </div>
    )
}
