<template>
    <div class="card">
        <div class="card-header">
            <h3 class="card-title mb-0">Register Wajah</h3>
        </div>
        <div class="card-body">
            <form @submit.prevent="register">
                <div class="mb-3">
                    <label for="form-label">Nama Lengkap</label>
                    <input class="form-control" v-model="name" id="name" type="text" placeholder="Nama" required />
                </div>
                <div class="mb-3">
                    <label class="form-label">Metode Input Gambar</label>
                    <div class="input-group">
                        <input type="file" class="form-control" id="fileUpload" aria-describedby="inputGroupFileAddon04" aria-label="Upload" accept="image/*" @change="onFileChange" />
                        <button class="btn btn-outline-secondary" type="button" id="inputGroupFileAddon04">Button</button>
                    </div>
                </div>
                <div class="mb-3">
                    <button class="btn btn-info text-white" type="button" @click="openCameraExternal">Open Camera</button>
                </div>
                <div class="mb-3">
                    <div class="d-flex">
                        <video v-if="!file && !captured" ref="video" autoplay playsinline
                            style="width:320px; height:240px; border:1px solid #ccc;"></video>
                        <canvas ref="canvas" style="display:block; width:320px; height:240px"></canvas>
                        <img v-if="file && previewUrl" :src="previewUrl" alt="Preview"
                                style="width:320px; height:240px; object-fit:cover; border:1px solid #ccc;" />
                    </div>
                </div>
                <div class="mb-3">
                    <div class="btn-group" role="group" aria-label="Basic example">
                        <button class="btn btn-warning" v-if="!file" type="button" @click="capture" :disabled="!stream">
                            Capture
                        </button>
                        <button class="btn btn-secondary" v-if="!file && captured" type="button" @click="downloadCapture">
                            Download Capture
                        </button>
                    </div>
                </div>
                <div class="form-group">
                    <button class="btn btn-primary" type="submit" :disabled="loading">
                        {{ loading ? 'Mendaftar...' : 'Register' }}
                    </button>
                </div>
            </form>
        </div>
        <div class="card-footer">
            <div v-if="result">
                <pre>{{ result }}</pre>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'

const name = ref('hendri')
const result = ref('')
const video = ref(null)
const canvas = ref(null)
const file = ref(null)
const previewUrl = ref(null)
const loading = ref(false)
const stream = ref(null)
const captured = ref(false)

const openCameraExternal = async () => {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices()
        const cameras = devices.filter(d => d.kind === 'videoinput')
        const externalKeywords = ['usb', 'external', 'hd', 'logitech', 'creative', 'c922']
        let external = cameras.find(c =>
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
        // Gunakan URL backend yang benar
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
        if (dataJson) {
            result.value = JSON.stringify(dataJson, null, 2)
        } else {
            result.value = resText
        }
        // Reset form
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
</script>