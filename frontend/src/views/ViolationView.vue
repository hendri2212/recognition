<template>
    <div class="container py-4">
        <h3 class="fw-bold mb-3">Traffic & Overload Violation</h3>

        <!-- Controls -->
        <div class="card p-3 mb-3">
            <div class="row g-3 align-items-end">
                <div class="col-md-3">
                    <label class="form-label">Mode Deteksi</label>
                    <select v-model="mode" class="form-select">
                        <option value="traffic">Traffic Violations (/traffic)</option>
                        <option value="traffic-video">Traffic Video (/traffic-video)</option>
                        <option value="over">Truck Overload (/over)</option>
                    </select>
                </div>

                <div class="col-md-5">
                    <label class="form-label">{{ mode === 'traffic-video' ? 'Upload Video' : 'Upload Gambar' }}</label>
                    <input ref="fileInputEl" type="file" :accept="mode === 'traffic-video' ? 'video/*' : 'image/*'"
                        class="form-control" @change="onFileChange" />
                </div>

                <div class="col-md-4 d-flex gap-2">
                    <button class="btn btn-primary w-50" :disabled="!file || loading" @click="analyze">
                        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                        Analisis
                    </button>
                    <button class="btn btn-outline-secondary w-50" :disabled="loading && !hasPreview" @click="resetAll">
                        Reset
                    </button>
                </div>
            </div>
            <div v-if="error" class="alert alert-danger mt-3 mb-0">{{ error }}</div>
            <div v-if="info" class="alert alert-info mt-3 mb-0">{{ info }}</div>
            <div v-if="isTrafficMode" class="mt-3">
                <label class="form-label">Analisis Class</label>
                <div class="traffic-class-grid">
                    <label v-for="item in trafficClassOptions" :key="item.value" class="form-check mb-0">
                        <input v-model="selectedTrafficClasses" class="form-check-input" type="checkbox"
                            :value="item.value" />
                        <span class="form-check-label">{{ item.label }}</span>
                    </label>
                </div>
                <div class="mt-2 d-flex gap-2">
                    <button type="button" class="btn btn-sm btn-outline-secondary" @click="selectAllTrafficClasses">
                        Pilih Semua
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" @click="clearTrafficClasses">
                        Kosongkan
                    </button>
                </div>
            </div>
            <div v-if="mode === 'traffic-video'" class="row g-3 mt-1">
                <div class="col-sm-6 col-md-3">
                    <label class="form-label">Sample FPS</label>
                    <input v-model.number="videoSampleFps" type="number" class="form-control" min="0.1" max="10"
                        step="0.1" />
                </div>
                <div class="col-sm-6 col-md-3">
                    <label class="form-label">Max Frames</label>
                    <input v-model.number="videoMaxFrames" type="number" class="form-control" min="1" max="1000"
                        step="1" />
                </div>
            </div>
        </div>

        <!-- Preview + Canvas -->
        <div class="row">
            <div class="col-lg-7 mb-3">
                <div class="card p-2">
                    <div class="text-muted small px-2 pt-2">Preview</div>
                    <div class="position-relative text-center">
                        <video v-if="previewUrl && mode === 'traffic-video'" :src="previewUrl" controls
                            class="img-fluid" style="max-height: 520px;"></video>
                        <img v-else-if="previewUrl" :src="previewUrl" ref="imgEl" @load="drawBoxes" class="img-fluid"
                            alt="preview" style="max-height: 520px; object-fit: contain;" />
                        <!-- Canvas overlay -->
                        <canvas v-show="previewUrl && mode !== 'traffic-video'" ref="canvasEl"
                            class="position-absolute top-0 start-0"
                            style="pointer-events:none;"></canvas>
                        <div v-if="!previewUrl" class="p-5 text-center text-muted">
                            Belum ada file. Silakan upload terlebih dahulu.
                        </div>
                    </div>
                </div>
            </div>

            <!-- Hasil Deteksi -->
            <div class="col-lg-5 mb-3">
                <div class="card p-3 h-100">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="mb-0">Hasil Deteksi</h6>
                        <span class="badge bg-secondary">{{ resultCountLabel }}</span>
                    </div>

                    <!-- Traffic results -->
                    <div v-if="mode === 'traffic'">
                        <div v-if="trafficResults.length === 0" class="text-muted small">Belum ada hasil.</div>
                        <ul class="list-group">
                            <li v-for="(d, idx) in trafficResults" :key="'tr-' + idx"
                                class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <div class="fw-semibold">{{ d.label }}</div>
                                    <span v-if="d.helmet_violation" class="badge bg-danger mb-1">NO HELMET</span>
                                    <div class="text-muted small">box: [{{ d.box.join(', ') }}]</div>
                                </div>
                                <span class="badge bg-primary rounded-pill">#{{ idx + 1 }}</span>
                            </li>
                        </ul>
                    </div>

                    <!-- Overload results -->
                    <div v-else-if="mode === 'over'">
                        <div v-if="overResults.length === 0" class="text-muted small">Belum ada hasil.</div>
                        <ul class="list-group">
                            <li v-for="(t, idx) in overResults" :key="'ov-' + idx"
                                class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <div class="fw-semibold">
                                        {{ t.label }}
                                        <span class="ms-2 badge" :class="t.overload ? 'bg-danger' : 'bg-success'">{{
                                            t.overload ? 'OVERLOAD' : 'Normal' }}</span>
                                    </div>
                                    <div class="text-muted small">box: [{{ t.box.join(', ') }}]</div>
                                </div>
                                <span class="badge bg-primary rounded-pill">#{{ idx + 1 }}</span>
                            </li>
                        </ul>
                    </div>

                    <!-- Video results -->
                    <div v-else>
                        <div v-if="videoFrames.length === 0" class="text-muted small">Belum ada hasil.</div>
                        <ul class="list-group video-result-list">
                            <li v-for="frame in videoFramesWithDetections" :key="'vf-' + frame.frame"
                                class="list-group-item">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div class="fw-semibold">Frame {{ frame.frame }}</div>
                                    <span class="badge bg-secondary">{{ frame.time }}s</span>
                                </div>
                                <div class="text-muted small mt-1">
                                    {{ frame.detections.map(d => d.label).join(', ') }}
                                </div>
                            </li>
                        </ul>
                    </div>

                    <!-- Aksi tambahan -->
                    <div class="mt-3 d-flex gap-2">
                        <button class="btn btn-outline-primary" :disabled="!previewUrl || mode === 'traffic-video'"
                            @click="downloadAnnotated">
                            Unduh Gambar + Box
                        </button>
                        <button class="btn btn-outline-secondary" :disabled="!previewUrl" @click="clearBoxes">
                            Hapus Box
                        </button>
                    </div>

                    <!-- Ringkasan -->
                    <div class="mt-3">
                        <div class="small text-muted">Ringkasan:</div>
                        <div class="border rounded p-2 bg-light"
                            style="white-space:pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;">
                            {{ summaryText }}
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'

// ====== Konfigurasi ======
// Ganti sesuai environment (bisa gunakan import.meta.env.VITE_API_BASE_URL)
const BACKEND_URL = 'http://localhost:8000'

// ====== State ======
const mode = ref('traffic')                // 'traffic' | 'over'
const file = ref(null)
const fileInputEl = ref(null)
const previewUrl = ref(null)
const imgEl = ref(null)
const canvasEl = ref(null)
const loading = ref(false)
const error = ref('')
const info = ref('')
const videoSampleFps = ref(1)
const videoMaxFrames = ref(120)

const trafficClassOptions = [
    { value: 'person', label: 'person' },
    { value: 'car', label: 'car' },
    { value: 'truck', label: 'truck' },
    { value: 'bus', label: 'bus' },
    { value: 'motorcycle', label: 'motorcycle' },
    { value: 'cell_phone', label: 'cell_phone' },
    { value: 'helmet', label: 'helmet' },
    { value: 'no_helmet', label: 'no_helmet' },
    { value: 'rider', label: 'rider' },
]
const selectedTrafficClasses = ref(trafficClassOptions.map(item => item.value))

// hasil
const trafficResults = ref([]) // [{label, box:[x1,y1,x2,y2]}]
const overResults = ref([])    // [{label, box:[x1,y1,x2,y2], overload:bool}]
const videoFrames = ref([])
const videoSummary = ref(null)

// ====== Computed ======
const hasPreview = computed(() => !!previewUrl.value)
const isTrafficMode = computed(() => mode.value === 'traffic' || mode.value === 'traffic-video')
const videoFramesWithDetections = computed(() => videoFrames.value.filter(frame => frame.detections?.length))
const resultCountLabel = computed(() => {
    if (mode.value === 'traffic') return `${trafficResults.value.length} objek`
    if (mode.value === 'traffic-video') {
        const detections = videoSummary.value?.detections || 0
        return `${detections} deteksi`
    }
    return `${overResults.value.length} truk`
})

const summaryText = computed(() => {
    if (mode.value === 'traffic') {
        if (!trafficResults.value.length) return 'Tidak ada deteksi kendaraan.'
        const byLabel = trafficResults.value.reduce((acc, d) => {
            acc[d.label] = (acc[d.label] || 0) + 1
            return acc
        }, {})
        const parts = Object.entries(byLabel).map(([k, v]) => `${k}: ${v}`)
        const helmetViolations = trafficResults.value.filter(d => d.helmet_violation).length
        return `Deteksi traffic: ${parts.join(', ')}\nPelanggaran tanpa helm: ${helmetViolations}`
    }
    if (mode.value === 'traffic-video') {
        if (!videoSummary.value) return 'Belum ada analisis video.'
        const framesWithDetection = videoFramesWithDetections.value.length
        return `Frame dianalisis: ${videoSummary.value.frames_analyzed}\nFrame dengan deteksi: ${framesWithDetection}\nTotal deteksi: ${videoSummary.value.detections}\nPelanggaran tanpa helm: ${videoSummary.value.helmet_violations}\nSample FPS: ${videoSummary.value.sample_fps}`
    }
    if (!overResults.value.length) return 'Tidak ada deteksi truk.'
    const total = overResults.value.length
    const over = overResults.value.filter(t => t.overload).length
    return `Total truk: ${total}\nOverload terindikasi: ${over}\nNormal: ${total - over}`
})

// ====== Handlers ======
function onFileChange(e) {
    const f = e.target.files?.[0]
    resetResults()
    error.value = ''
    info.value = ''
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    if (f) {
        file.value = f
        previewUrl.value = URL.createObjectURL(f)
        // gambar akan memanggil @load -> drawBoxes()
    } else {
        file.value = null
        previewUrl.value = null
        clearBoxes()
    }
}

function resetResults() {
    trafficResults.value = []
    overResults.value = []
    videoFrames.value = []
    videoSummary.value = null
}

function selectAllTrafficClasses() {
    selectedTrafficClasses.value = trafficClassOptions.map(item => item.value)
}

function clearTrafficClasses() {
    selectedTrafficClasses.value = []
}

function resetAll() {
    resetResults()
    error.value = ''
    info.value = ''
    file.value = null
    if (fileInputEl.value) fileInputEl.value.value = ''
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
    clearBoxes()
}

watch(mode, () => {
    resetAll()
})

async function analyze() {
    if (!file.value) {
        error.value = 'Silakan upload gambar terlebih dahulu.'
        return
    }
    loading.value = true
    error.value = ''
    info.value = 'Mengirim gambar untuk dianalisis...'

    try {
        const form = new FormData()
        form.append('file', file.value)
        if (isTrafficMode.value) {
            if (!selectedTrafficClasses.value.length) {
                error.value = 'Pilih minimal satu class untuk dianalisis.'
                return
            }
            form.append('classes', selectedTrafficClasses.value.join(','))
        }
        if (mode.value === 'traffic-video') {
            form.append('sample_fps', String(videoSampleFps.value || 1))
            form.append('max_frames', String(videoMaxFrames.value || 120))
        }

        const endpoint = mode.value === 'traffic'
            ? '/traffic'
            : mode.value === 'traffic-video'
                ? '/traffic-video'
                : '/over'
        const res = await fetch(`${BACKEND_URL}${endpoint}`, {
            method: 'POST',
            body: form
        })

        const text = await res.text()
        if (!res.ok) {
            // tangani kemungkinan FastAPI mengembalikan string error
            try {
                const errObj = JSON.parse(text)
                throw new Error(errObj.detail || text)
            } catch {
                throw new Error(text)
            }
        }

        let data = {}
        try { data = JSON.parse(text) } catch { data = {} }

        if (mode.value === 'traffic') {
            trafficResults.value = Array.isArray(data.detections) ? data.detections : []
            if (!trafficResults.value.length && data.debug) {
                const pass = data.debug.fallback_pass || data.debug.first_pass
                const labels = pass?.filtered_labels ? Object.entries(pass.filtered_labels) : []
                if (labels.length) {
                    const labelText = labels.map(([k, v]) => `${k}: ${v}`).join(', ')
                    info.value = `Analisis selesai, tetapi tidak ada class traffic yang lolos filter. Objek lain terdeteksi: ${labelText}.`
                } else {
                    info.value = 'Analisis selesai, tetapi YOLO tidak menemukan objek traffic pada gambar ini.'
                }
            }
        } else if (mode.value === 'traffic-video') {
            videoFrames.value = Array.isArray(data.frames) ? data.frames : []
            videoSummary.value = data.summary || null
        } else {
            overResults.value = Array.isArray(data.trucks) ? data.trucks : []
        }

        await nextTick()
        drawBoxes()
        if (!info.value.startsWith('Analisis selesai')) {
            info.value = 'Analisis selesai.'
        }
    } catch (e) {
        error.value = 'Gagal menganalisis: ' + (e?.message || e)
    } finally {
        loading.value = false
    }
}

// ====== Drawing helpers ======
function clearBoxes() {
    const cvs = canvasEl.value
    if (!cvs) return
    const ctx = cvs.getContext('2d')
    ctx.clearRect(0, 0, cvs.width, cvs.height)
}

function drawBoxes() {
    const img = imgEl.value
    const cvs = canvasEl.value
    if (!img || !cvs) return
    // Samakan ukuran canvas dengan ukuran gambar yang sudah dirender
    const rect = img.getBoundingClientRect()
    cvs.width = rect.width
    cvs.height = rect.height
    cvs.style.width = rect.width + 'px'
    cvs.style.height = rect.height + 'px'
    cvs.style.left = img.offsetLeft + 'px'
    cvs.style.top = img.offsetTop + 'px'

    const ctx = cvs.getContext('2d')
    ctx.clearRect(0, 0, cvs.width, cvs.height)
    ctx.lineWidth = 2

    // Hitung faktor skala dari ukuran asli gambar ke ukuran tampil
    const naturalW = img.naturalWidth
    const naturalH = img.naturalHeight
    const scaleX = rect.width / naturalW
    const scaleY = rect.height / naturalH

    // Helper untuk menggambar satu box
    const drawOne = (b, color = 'red', label = '') => {
        const [x1, y1, x2, y2] = b
        const sx1 = x1 * scaleX
        const sy1 = y1 * scaleY
        const sx2 = x2 * scaleX
        const sy2 = y2 * scaleY
        const w = sx2 - sx1
        const h = sy2 - sy1

        ctx.strokeStyle = color
        ctx.strokeRect(sx1, sy1, w, h)

        if (label) {
            ctx.font = '12px ui-monospace, monospace'
            ctx.fillStyle = color
            const textWidth = ctx.measureText(label).width + 8
            ctx.fillRect(sx1, Math.max(0, sy1 - 16), textWidth, 16)
            ctx.fillStyle = '#fff'
            ctx.fillText(label, sx1 + 4, Math.max(10, sy1 - 4))
        }
    }

    if (mode.value === 'traffic') {
        trafficResults.value.forEach((d) => {
            drawOne(d.box, d.helmet_violation ? '#dc3545' : '#0d6efd', d.label)
        })
    } else {
        overResults.value.forEach((t) => {
            drawOne(t.box, t.overload ? '#dc3545' : '#198754', t.overload ? 'OVER' : 'OK') // merah/hijau
        })
    }
}

// ====== Unduh hasil anotasi ======
function downloadAnnotated() {
    if (mode.value === 'traffic-video') return
    const img = imgEl.value
    const overlay = canvasEl.value
    if (!img || !overlay) return

    // Buat canvas gabungan untuk disimpan
    const off = document.createElement('canvas')
    off.width = overlay.width
    off.height = overlay.height
    const ctx = off.getContext('2d')

    // Gambar gambar dasar dan overlay
    // Untuk akurasi, gambar image yang sudah discale ke ukuran overlay
    const temp = document.createElement('canvas')
    temp.width = overlay.width
    temp.height = overlay.height
    const tctx = temp.getContext('2d')

    // Render img ke temp
    tctx.drawImage(img, 0, 0, overlay.width, overlay.height)
    // Salin temp ke off
    ctx.drawImage(temp, 0, 0)
    // Salin overlay ke off
    ctx.drawImage(overlay, 0, 0)

    const link = document.createElement('a')
    link.download = `violation_${Date.now()}.png`
    link.href = off.toDataURL('image/png')
    link.click()
}
</script>

<style scoped>
.container {
    max-width: 1200px;
}

.card {
    border-radius: 12px;
}

.traffic-class-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 8px 14px;
}

.video-result-list {
    max-height: 360px;
    overflow: auto;
}
</style>
