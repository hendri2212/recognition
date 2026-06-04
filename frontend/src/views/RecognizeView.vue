<template>
    <section class="page-width workflow-page recognize-page">
        <div class="workflow-heading">
            <div>
                <p class="eyebrow">Live recognition</p>
                <h1>Uji recognition dari kamera</h1>
            </div>
            <div class="command-bar" role="group" aria-label="Kontrol recognition">
                <button class="btn btn-primary" @click="openCameraExternal" title="Buka kamera">
                    <i class="bi bi-camera-video"></i>
                    Buka kamera
                </button>
                <button class="btn btn-warning" @click="captureAndRecognize" title="Capture dan analisis wajah">
                    <i class="bi bi-bounding-box"></i>
                    Recognize
                </button>
                <button class="btn btn-outline-secondary" @click="downloadCapture" title="Unduh capture terakhir">
                    <i class="bi bi-download"></i>
                </button>
                <button class="btn btn-outline-danger" @click="startRecognition" title="Mulai auto recognize">
                    <i class="bi bi-play-fill"></i>
                </button>
                <button class="btn btn-dark" @click="stopRecognition" title="Hentikan recognition">
                    <i class="bi bi-stop-fill"></i>
                </button>
            </div>
        </div>

        <div class="recognize-grid">
            <div class="workflow-panel live-panel">
                <div class="panel-head">
                    <div>
                        <p class="eyebrow">Capture workspace</p>
                        <h2>Camera feed</h2>
                    </div>
                    <span>{{ recognitionState }}</span>
                </div>

                <div class="media-grid">
                    <figure>
                        <video ref="video" autoplay playsinline></video>
                        <figcaption>Live input</figcaption>
                    </figure>
                    <figure>
                        <canvas ref="canvas"></canvas>
                        <figcaption>Capture result</figcaption>
                    </figure>
                </div>
            </div>

            <aside class="workflow-panel result-panel">
                <p class="eyebrow">Detection output</p>
                <h2>Identitas terdeteksi</h2>

                <div v-if="detections.length" class="identity-list">
                    <article v-for="(det, idx) in detections" :key="'det-' + idx">
                        <strong class="text-capitalize">{{ det.name }}</strong>
                        <span>
                            <template v-if="det.age !== undefined && det.age !== null">{{ det.age }} tahun</template>
                            <template v-if="(det.age !== undefined && det.age !== null) && det.gender"> | </template>
                            <template v-if="det.gender">{{ formatGender(det.gender) }}</template>
                        </span>
                    </article>
                </div>
                <div v-else class="empty-result">
                    Belum ada identitas. Buka kamera lalu jalankan recognition.
                </div>

                <div v-if="error" class="alert alert-danger mb-0">{{ error }}</div>
            </aside>
        </div>
    </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const video = ref(null)
const canvas = ref(null)
const detections = ref([])
const error = ref('')
let stream = null
let intervalId = null

const recognitionState = computed(() => {
    if (intervalId) return 'Auto recognition aktif'
    if (stream) return 'Kamera aktif'
    return 'Menunggu kamera'
})

function formatGender(g) {
    return (g || '').toString().trim().toLowerCase().replace(/^\w/, c => c.toUpperCase())
}

function speak(text) {
    if (!('speechSynthesis' in window)) {
        console.warn('Browser tidak mendukung Speech Synthesis API')
        return
    }

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'id-ID'
    utterance.rate = 0.8
    utterance.pitch = 1
    utterance.volume = 1

    const voices = speechSynthesis.getVoices()
    const indonesianVoice = voices.find(voice =>
        voice.lang.includes('id') ||
        voice.lang.includes('ID') ||
        voice.name.toLowerCase().includes('indonesia')
    )

    if (indonesianVoice) utterance.voice = indonesianVoice
    utterance.onerror = event => console.error('Error TTS:', event.error)
    speechSynthesis.speak(utterance)
}

const loadVoices = () => {
    return new Promise(resolve => {
        let voices = speechSynthesis.getVoices()
        if (voices.length) {
            resolve(voices)
        } else {
            speechSynthesis.addEventListener('voiceschanged', () => {
                voices = speechSynthesis.getVoices()
                resolve(voices)
            }, { once: true })
        }
    })
}

onMounted(async () => {
    try {
        await loadVoices()
    } catch (err) {
        console.error('Error loading voices:', err)
    }
})

const openCameraExternal = async () => {
    try {
        await navigator.mediaDevices.getUserMedia({ video: true })
        const devices = await navigator.mediaDevices.enumerateDevices()
        const cameras = devices.filter(device => device.kind === 'videoinput')
        const externalKeywords = ['usb', 'external', 'hd', 'logitech', 'creative', 'c922']
        const externalCamera = cameras.find(cam =>
            cam.label && externalKeywords.some(keyword => cam.label.toLowerCase().includes(keyword))
        )
        const deviceId = externalCamera?.deviceId || cameras[1]?.deviceId || cameras[0]?.deviceId
        if (!deviceId) {
            error.value = 'Tidak ada kamera external yang terdeteksi!'
            return
        }
        if (stream) stream.getTracks().forEach(track => track.stop())
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                deviceId: { exact: deviceId },
                width: 320,
                height: 240,
                aspectRatio: 4 / 3
            }
        })
        video.value.srcObject = stream
        await new Promise(resolve => {
            video.value.onloadedmetadata = () => {
                canvas.value.width = video.value.videoWidth
                canvas.value.height = video.value.videoHeight
                resolve()
            }
        })
        error.value = ''
    } catch (err) {
        error.value = 'Gagal membuka kamera: ' + (err?.message || err)
    }
}

const captureAndRecognize = async () => {
    if (!video.value?.videoWidth) {
        error.value = 'Buka kamera sebelum menjalankan recognition.'
        return
    }
    canvas.value.width = video.value.videoWidth
    canvas.value.height = video.value.videoHeight
    const ctx = canvas.value.getContext('2d')
    ctx.clearRect(0, 0, canvas.value.width, canvas.value.height)
    ctx.drawImage(video.value, 0, 0, video.value.videoWidth, video.value.videoHeight)

    await new Promise(resolve => {
        canvas.value.toBlob(async blob => {
            const formData = new FormData()
            formData.append('file', blob, 'stream.png')
            try {
                const res = await fetch('http://localhost:8000/recognize', {
                    method: 'POST',
                    body: formData
                })
                const data = await res.json()
                const results = Array.isArray(data) ? data : (data?.results ?? [])
                detections.value = results.map(r => ({
                    name: r?.name ?? 'unknown',
                    age: r?.age ?? null,
                    gender: r?.gender ?? '',
                    box: r?.box,
                    distance: r?.distance
                }))
                error.value = ''
                results.forEach(item => {
                    if (item.name && item.name !== 'unknown') speak(item.name)
                })
            } catch (err) {
                error.value = 'Gagal mengenali wajah: ' + err
            }
            resolve()
        }, 'image/png')
    })
}

const downloadCapture = () => {
    const link = document.createElement('a')
    link.download = `recognize_capture_${Date.now()}.png`
    link.href = canvas.value.toDataURL('image/png')
    link.click()
}

const startRecognition = () => {
    if (intervalId) clearInterval(intervalId)
    intervalId = setInterval(captureAndRecognize, 500)
}

const stopRecognition = () => {
    if (intervalId) clearInterval(intervalId)
    intervalId = null
    if (stream) stream.getTracks().forEach(track => track.stop())
    stream = null
}

onUnmounted(() => {
    stopRecognition()
})
</script>

<style scoped>
.workflow-heading {
    display: grid;
    grid-template-columns: minmax(320px, 1fr) auto;
    gap: 24px;
    align-items: end;
    margin-bottom: 26px;
}

.workflow-heading h1 {
    margin: 0;
    font-size: 54px;
    line-height: 1.08;
}

.command-bar {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;
}

.command-bar .btn {
    display: inline-flex;
    min-width: 52px;
    min-height: 52px;
    align-items: center;
    justify-content: center;
    gap: 9px;
    border-radius: 8px;
}

.recognize-grid {
    display: grid;
    grid-template-columns: minmax(560px, 1.35fr) minmax(320px, 0.65fr);
    gap: 22px;
}

.live-panel,
.result-panel {
    padding: 28px;
}

.panel-head {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 20px;
}

.panel-head h2,
.result-panel h2 {
    margin: 0;
    font-size: 28px;
}

.panel-head span {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
    color: var(--muted);
    padding: 9px 12px;
}

.media-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
}

figure {
    margin: 0;
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: #0d1823;
}

video,
canvas {
    display: block;
    width: 100%;
    aspect-ratio: 4 / 3;
    object-fit: contain;
}

figcaption {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    background: #142535;
    color: rgba(255, 255, 255, 0.74);
    padding: 12px 14px;
    font-size: 13px;
}

.identity-list {
    display: grid;
    gap: 12px;
    margin: 24px 0;
}

.identity-list article,
.empty-result {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
    padding: 18px;
}

.identity-list strong,
.identity-list span {
    display: block;
}

.identity-list strong {
    font-size: 22px;
}

.identity-list span {
    margin-top: 5px;
    color: var(--muted);
}

.empty-result {
    margin: 24px 0;
    color: var(--muted);
    line-height: 1.6;
}

@media (max-width: 980px) {
    .workflow-heading,
    .recognize-grid {
        grid-template-columns: 1fr;
    }

    .command-bar {
        justify-content: flex-start;
    }

    .workflow-heading h1 {
        font-size: 44px;
    }
}

@media (max-width: 680px) {
    .live-panel,
    .result-panel {
        padding: 20px;
    }

    .media-grid {
        grid-template-columns: 1fr;
    }

    .panel-head {
        flex-direction: column;
    }

    .workflow-heading h1 {
        font-size: 36px;
    }
}
</style>
