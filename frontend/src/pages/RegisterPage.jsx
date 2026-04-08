import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { Shield, AlertCircle, Camera, ScanFace } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../utils/api'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'intern' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [cameraReady, setCameraReady] = useState(false)
  const [cameraError, setCameraError] = useState('')
  const [faceCaptured, setFaceCaptured] = useState(false)
  const [faceImageBase64, setFaceImageBase64] = useState('')

  useEffect(() => {
    let mounted = true

    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false,
        })
        streamRef.current = stream
        if (videoRef.current && mounted) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
          setCameraReady(true)
          setCameraError('')
        }
      } catch (err) {
        setCameraError(
          err?.name === 'NotAllowedError'
            ? 'Camera permission denied. Please allow camera access to register your face.'
            : 'Unable to access camera on this device/browser.'
        )
      }
    }

    startCamera()
    return () => {
      mounted = false
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  const captureFace = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) {
      setError('Camera is not ready yet. Please wait a moment and try again.')
      return
    }

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const imageBase64 = canvas.toDataURL('image/jpeg', 0.9)

    setFaceImageBase64(imageBase64)
    setFaceCaptured(true)
    setError('')
    toast.success('Face captured successfully')
  }

  const handleSubmit = async e => {
    e.preventDefault()
    setError('')
    if (!faceImageBase64) {
      setError('Capture your face before creating the account.')
      return
    }
    setLoading(true)
    try {
      await register(form)
      await api.post('/face/register', { image_base64: faceImageBase64 })
      toast.success('Account created!')
      navigate('/welcome', { replace: true })
    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen overflow-y-auto flex items-start justify-center bg-bg-900 grid-bg px-4 py-6 sm:items-center sm:py-4">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-purple/5 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 32 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md flex-none my-auto"
      >
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent/10 border border-accent/30 mb-4 shadow-glow">
            <Shield size={24} className="text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create Account</h1>
          <p className="text-slate-500 mt-1 text-sm">Join SecureAI Platform</p>
        </div>

        <div className="glass rounded-2xl p-8 shadow-card">
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm mb-4"
            >
              <AlertCircle size={14} />{error}
            </motion.div>
          )}

          {cameraError && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm mb-4"
            >
              <AlertCircle size={14} />{cameraError}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: 'username', label: 'Username', type: 'text', placeholder: 'john_doe' },
              { key: 'email', label: 'Email', type: 'email', placeholder: 'john@company.com' },
              { key: 'password', label: 'Password', type: 'password', placeholder: '••••••••' },
            ].map(({ key, label, type, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">{label}</label>
                <input
                  type={type}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full px-4 py-3 rounded-xl bg-bg-800 border border-white/8 text-white placeholder-slate-600 focus:outline-none focus:border-accent/50 focus:shadow-glow transition-all text-sm font-mono"
                  placeholder={placeholder}
                  required
                />
              </div>
            ))}

            <div>
              <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">Role</label>
              <select
                value={form.role}
                onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                className="w-full px-4 py-3 rounded-xl bg-bg-800 border border-white/8 text-white focus:outline-none focus:border-accent/50 transition-all text-sm"
              >
                <option value="intern">Intern</option>
                <option value="hr">HR</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">Face Registration</label>
              <div className="rounded-xl overflow-hidden border border-white/10 bg-bg-800">
                <video ref={videoRef} autoPlay playsInline muted className="w-full h-56 object-cover" />
              </div>
              <canvas ref={canvasRef} className="hidden" />
              <div className="mt-3 flex items-center justify-between gap-3">
                <p className={`text-xs ${faceCaptured ? 'text-success' : 'text-slate-500'}`}>
                  {faceCaptured ? 'Face captured. You can create the account now.' : 'Capture your face once to complete registration.'}
                </p>
                <button
                  type="button"
                  onClick={captureFace}
                  disabled={!cameraReady || loading}
                  className="shrink-0 px-4 py-2 rounded-xl border border-accent/30 bg-accent/10 text-accent font-semibold hover:bg-accent/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {faceCaptured ? <Camera size={15} className="inline mr-2" /> : <ScanFace size={15} className="inline mr-2" />}
                  {faceCaptured ? 'Retake Face' : 'Capture Face'}
                </button>
              </div>
            </div>

            <motion.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              type="submit"
              disabled={loading || !faceImageBase64}
              className="w-full py-3 rounded-xl bg-accent text-bg-900 font-bold text-sm tracking-wide hover:bg-accent-dim transition-all disabled:opacity-50 shadow-glow"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </motion.button>
          </form>

          <p className="text-center text-slate-500 text-xs mt-4">
            Already have an account?{' '}
            <Link to="/login" className="text-accent hover:underline">Sign in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
