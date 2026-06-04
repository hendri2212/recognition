<template>
    <section class="page-width workflow-page register-page">
        <div class="workflow-heading">
            <div>
                <p class="eyebrow">Face registry</p>
                <h1>Registrasi identitas wajah</h1>
            </div>
            <p>
                Siapkan data wajah dari kamera atau file gambar untuk menunjukkan proses enrollment
                sebelum recognition dijalankan.
            </p>
        </div>

        <div class="register-grid">
            <form class="workflow-panel form-panel" @submit.prevent="register">
                <div class="field-block">
                    <label for="name" class="form-label">Nama lengkap</label>
                    <input v-model="name" id="name" class="form-control" type="text"
                        placeholder="Masukkan nama" required />
                </div>

                <div class="field-block">
                    <label for="fileUpload" class="form-label">Upload gambar</label>
                    <input id="fileUpload" type="file" class="form-control" accept="image/*"
                        @change="onFileChange" />
                </div>

                <div class="action-row">
                    <button class="btn btn-outline-info" type="button" @click="openCameraExternal">
                        <i class="bi bi-camera-video"></i>
                        Buka kamera
                    </button>
                    <button v-if="!file" class="btn btn-warning" type="button" @click="capture"
                        :disabled="!stream">
                        <i class="bi bi-camera"></i>
                        Capture
                    </button>
                    <button v-if="!file && captured" class="btn btn-outline-secondary" type="button"
                        @click="downloadCapture">
                        <i class="bi bi-download"></i>
                        Unduh capture
                    </button>
                </div>

                <button class="btn btn-primary submit-button" type="submit" :disabled="loading">
                    <span v-if="loading" class="spinner-border spinner-border-sm"></span>
                    {{ loading ? 'Mendaftarkan...' : 'Simpan registrasi' }}
                </button>
            </form>

            <aside class="workflow-panel preview-panel">
                <div class="panel-head">
                    <div>
                        <p class="eyebrow">Input preview</p>
                        <h2>Sumber wajah</h2>
                    </div>
                    <span class="source-state">{{ sourceLabel }}</span>
                </div>

                <div class="media-stage">
                    <video v-if="!file && !captured" ref="video" autoplay playsinline></video>
                    <canvas ref="canvas"></canvas>
                    <img v-if="file && previewUrl" :src="previewUrl" alt="Preview registrasi wajah" />
                    <div v-if="!file && !captured && !stream" class="empty-stage">
                        Kamera belum aktif atau file belum dipilih.
                    </div>
                </div>

                <div v-if="result" class="result-block">
                    <strong>Status registrasi</strong>
                    <pre>{{ result }}</pre>
                </div>
            </aside>
        </div>
    </section>
</template>

<script setup>
import { computed, onUnmounted, ref } from 'vue'

const name = ref('')
const result = ref('')
const video = ref(null)
const canvas = ref(null)
const file = ref(null)
const previewUrl = ref(null)
const loading = ref(false)
const stream = ref(null)
const captured = ref(false)

const sourceLabel = computed(() => {
    if (file.value) return 'File upload'
    if (captured.value) return 'Camera capture'
    if (stream.value) return 'Live camera'
    return 'Waiting input'
})

const openCameraExternal = async () => {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices()
        const cameras = devices.filter(d => d.kind === 'videoinput')
        const externalKeywords = ['usb', 'external', 'hd', 'logitech', 'creative', 'c922']
        const external = cameras.find(c =>
            c.label && externalKeywords.some(key => c.label.toLowerCase().includes(key))
        )
        const deviceId = external?.deviceId || cameras[0]?.deviceId
        if (!deviceId) {
            result.value = 'Tidak ada kamera yang terdeteksi.'
            return
        }
        if (stream.value) {
            stream.value.getTracks().forEach(t => t.stop())
        }
        stream.value = await navigator.mediaDevices.getUserMedia({
            video: { deviceId: { exact: deviceId }, width: 320, height: 240, aspectRatio: 4 / 3 }
        })
        video.value.srcObject = stream.value
        await new Promise(resolve => {
            video.value.onloadedmetadata = () => resolve()
        })
        captured.value = false
        file.value = null
        previewUrl.value = null
    } catch (err) {
        console.error(err)
        result.value = 'Gagal membuka kamera: ' + err.message
    }
}

const onFileChange = event => {
    const selected = event.target.files[0]
    if (selected) {
        file.value = selected
        if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
        previewUrl.value = URL.createObjectURL(selected)
        captured.value = true
        if (stream.value) {
            stream.value.getTracks().forEach(t => t.stop())
            stream.value = null
        }
    }
}

const capture = () => {
    if (!stream.value) return
    const ctx = canvas.value.getContext('2d')
    canvas.value.width = video.value.videoWidth
    canvas.value.height = video.value.videoHeight
    ctx.drawImage(video.value, 0, 0)
    captured.value = true
    file.value = null
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
}

const downloadCapture = () => {
    canvas.value.toBlob(blob => {
        const link = document.createElement('a')
        link.download = `capture_${Date.now()}.png`
        link.href = URL.createObjectURL(blob)
        link.click()
    }, 'image/png')
}

const register = async () => {
    loading.value = true
    result.value = ''
    try {
        const formData = new FormData()
        formData.append('name', name.value)
        if (file.value) {
            formData.append('file', file.value)
        } else if (captured.value) {
            await new Promise(resolve => {
                canvas.value.toBlob(blob => {
                    formData.append('file', blob, 'face.png')
                    resolve()
                }, 'image/png')
            })
        } else {
            throw new Error('Silakan upload gambar atau capture menggunakan kamera')
        }
        const res = await fetch('http://localhost:8000/register', { method: 'POST', body: formData })
        const resText = await res.text()
        if (!res.ok) {
            let errMsg = resText
            try {
                const errObj = JSON.parse(resText)
                errMsg = errObj.detail || resText
            } catch { }
            throw new Error(errMsg)
        }
        let dataJson = null
        try {
            dataJson = JSON.parse(resText)
        } catch { }
        result.value = dataJson ? JSON.stringify(dataJson, null, 2) : resText
        name.value = ''
        file.value = null
        previewUrl.value = null
        captured.value = false
        if (stream.value) {
            stream.value.getTracks().forEach(t => t.stop())
            stream.value = null
        }
    } catch (err) {
        console.error(err)
        result.value = 'Error: ' + err.message
    } finally {
        loading.value = false
    }
}

onUnmounted(() => {
    if (stream.value) stream.value.getTracks().forEach(t => t.stop())
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<style scoped>
.workflow-heading {
    display: grid;
    grid-template-columns: minmax(320px, 0.92fr) minmax(340px, 0.7fr);
    gap: 28px;
    align-items: end;
    margin-bottom: 26px;
}

.workflow-heading h1 {
    margin: 0;
    font-size: 54px;
    line-height: 1.08;
}

.workflow-heading p:last-child {
    margin: 0 0 6px;
    color: var(--muted);
    font-size: 17px;
    line-height: 1.6;
}

.register-grid {
    display: grid;
    grid-template-columns: minmax(320px, 0.8fr) minmax(420px, 1fr);
    gap: 22px;
}

.form-panel,
.preview-panel {
    padding: 28px;
}

.field-block + .field-block {
    margin-top: 20px;
}

.form-label {
    color: var(--ink);
    font-weight: 700;
}

.form-control {
    min-height: 52px;
    border-color: var(--line);
    border-radius: 8px;
}

.action-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 24px 0;
}

.action-row .btn,
.submit-button {
    display: inline-flex;
    min-height: 48px;
    align-items: center;
    justify-content: center;
    gap: 9px;
    border-radius: 8px;
}

.submit-button {
    width: 100%;
}

.panel-head {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 20px;
}

.panel-head h2 {
    margin: 0;
    font-size: 28px;
}

.source-state {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
    color: var(--muted);
    padding: 9px 12px;
    white-space: nowrap;
}

.media-stage {
    position: relative;
    display: grid;
    min-height: 420px;
    place-items: center;
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: #0d1823;
}

.media-stage video,
.media-stage canvas,
.media-stage img {
    grid-area: 1 / 1;
    width: min(100%, 640px);
    max-height: 520px;
    object-fit: contain;
}

.empty-stage {
    position: absolute;
    inset: auto 24px 24px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.92);
    color: var(--muted);
    padding: 14px;
    text-align: center;
}

.result-block {
    margin-top: 18px;
}

.result-block strong {
    display: block;
    margin-bottom: 10px;
}

pre {
    max-height: 240px;
    margin: 0;
    overflow: auto;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
    padding: 16px;
    color: var(--ink);
    white-space: pre-wrap;
}

@media (max-width: 920px) {
    .workflow-heading,
    .register-grid {
        grid-template-columns: 1fr;
    }

    .workflow-heading h1 {
        font-size: 44px;
    }
}

@media (max-width: 620px) {
    .form-panel,
    .preview-panel {
        padding: 20px;
    }

    .panel-head {
        flex-direction: column;
    }

    .media-stage {
        min-height: 320px;
    }

    .workflow-heading h1 {
        font-size: 36px;
    }
}
</style>
