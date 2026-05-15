<template>
    <div class="card">
        <div class="card-header">
            <div class="d-flex justify-content-between align-items-center">
                <h3 class="card-title mb-0">Live Face Recognition</h3>
                <div class="btn-group" role="group" aria-label="Basic example">
                    <button class="btn btn-sm btn-primary" @click="openCameraExternal">Open Camera</button>
                    <button class="btn btn-sm btn-warning" @click="captureAndRecognize">Recognize</button>
                    <button class="btn btn-sm btn-secondary" @click="downloadCapture">Download Capture</button>
                    <button class="btn btn-sm btn-danger" @click="startRecognition">Auto Recognize</button>
                    <button class="btn btn-sm btn-dark" @click="stopRecognition">Stop Recognize</button>
                </div>
            </div>
        </div>
        <div class="card-body shadow">
            <div class="d-flex">
                <video ref="video" autoplay playsinline style="width:320px;height:240px;" />
                <canvas ref="canvas" class="ms-3" style="width:320px;height:240px;display:block;" />
                <div class="text-start ms-3">
                    <label class="fw-bold">Nama Lengkap</label>
                    <div v-if="names.length">
                        <div class="text-capitalize" v-for="name in names" :key="name">{{ name }}</div>
                        <div v-if="detections.length" class="text-muted small">
                            <div v-for="(det, idx) in detections" :key="'meta-'+idx">
                                <span v-if="det.age !== undefined && det.age !== null">{{ det.age }}</span>
                                <span v-if="(det.age !== undefined && det.age !== null) && det.gender"> • </span>
                                <span v-if="det.gender">{{ formatGender(det.gender) }}</span>
                            </div>
                        </div>
                    </div>
                    <div>{{ error }}</div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const video = ref(null);
const canvas = ref(null);
const names = ref([]);
const detections = ref([]);
const error = ref('');
let stream = null;

// Format gender nicely in UI
function formatGender(g) {
    return (g || '').toString().trim().toLowerCase().replace(/^\w/, c => c.toUpperCase());
}

let intervalId = null;

// Fungsi TTS dengan bahasa Indonesia
function speak(text) {
    if (!('speechSynthesis' in window)) {
        console.warn('Browser tidak mendukung Speech Synthesis API');
        return;
    }
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Konfigurasi untuk bahasa Indonesia
    utterance.lang = 'id-ID';
    utterance.rate = 0.8;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    // Cari voice bahasa Indonesia yang tersedia
    const voices = speechSynthesis.getVoices();
    const indonesianVoice = voices.find(voice => 
        voice.lang.includes('id') || 
        voice.lang.includes('ID') ||
        voice.name.toLowerCase().includes('indonesia')
    );
    
    if (indonesianVoice) {
        utterance.voice = indonesianVoice;
    }
    
    // Event handlers untuk debugging (opsional)
    utterance.onstart = () => {
        console.log('TTS mulai berbicara:', text);
    };
    
    utterance.onerror = (event) => {
        console.error('Error TTS:', event.error);
    };
    
    // Jalankan TTS
    speechSynthesis.speak(utterance);
}

// Fungsi untuk memuat voice yang tersedia
const loadVoices = () => {
    return new Promise((resolve) => {
        let voices = speechSynthesis.getVoices();
        if (voices.length) {
            resolve(voices);
        } else {
            speechSynthesis.addEventListener('voiceschanged', () => {
                voices = speechSynthesis.getVoices();
                resolve(voices);
            });
        }
    });
};

// Load voices saat komponen dimount
onMounted(async () => {
    try {
        const voices = await loadVoices();
        const indonesianVoices = voices.filter(voice => 
            voice.lang.includes('id') || 
            voice.lang.includes('ID') ||
            voice.name.toLowerCase().includes('indonesia')
        );
        
        if (indonesianVoices.length > 0) {
            console.log('Voice Indonesia tersedia:', indonesianVoices.map(v => v.name));
        } else {
            console.log('Tidak ada voice Indonesia, menggunakan voice default dengan lang id-ID');
        }
    } catch (err) {
        console.error('Error loading voices:', err);
    }
});

const openCameraExternal = async () => {
    await navigator.mediaDevices.getUserMedia({ video: true });
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter(device => device.kind === 'videoinput');
    const externalKeywords = ['usb', 'external', 'hd', 'logitech', 'creative', 'c922'];
    let externalCamera = cameras.find(cam =>
        cam.label && externalKeywords.some(keyword =>
            cam.label.toLowerCase().includes(keyword)
        )
    );
    let deviceId = externalCamera?.deviceId || (cameras[1]?.deviceId || cameras[0]?.deviceId);
    if (!deviceId) {
        error.value = 'Tidak ada kamera external yang terdeteksi!';
        return;
    }
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
    stream = await navigator.mediaDevices.getUserMedia({
        video: {
            deviceId: { exact: deviceId },
            width: 320,
            height: 240,
            aspectRatio: 4 / 3
        }
    });
    video.value.srcObject = stream;
    await new Promise(resolve => {
        video.value.onloadedmetadata = () => {
            canvas.value.width = video.value.videoWidth;
            canvas.value.height = video.value.videoHeight;
            resolve();
        };
    });
};

const captureAndRecognize = async () => {
    canvas.value.width = video.value.videoWidth;
    canvas.value.height = video.value.videoHeight;
    const ctx = canvas.value.getContext('2d');
    ctx.clearRect(0, 0, canvas.value.width, canvas.value.height);
    ctx.drawImage(
        video.value,
        0, 0, video.value.videoWidth, video.value.videoHeight,
        0, 0, canvas.value.width, canvas.value.height
    );
    await new Promise(resolve => {
        canvas.value.toBlob(async blob => {
            const formData = new FormData();
            formData.append('file', blob, 'stream.png');
            try {
                const res = await fetch('http://localhost:8000/recognize', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                detections.value = (Array.isArray(data) ? data : (data?.results ?? []))
                    .map(r => ({ name: r?.name ?? 'unknown', age: r?.age ?? null, gender: r?.gender ?? '', box: r?.box, distance: r?.distance }));
                names.value = data.map(f => f.name);
                error.value = '';
                // **Panggil TTS berbahasa Indonesia untuk setiap nama yang valid**
                data.forEach(item => {
                    if (item.name && item.name !== 'unknown') {
                        speak(item.name);
                    }
                });
            } catch (err) {
                error.value = "Gagal mengenali wajah: " + err;
            }
            resolve();
        }, 'image/png');
    });
};

const downloadCapture = () => {
    const link = document.createElement('a');
    link.download = `recognize_capture_${Date.now()}.png`;
    link.href = canvas.value.toDataURL('image/png');
    link.click();
};

const startRecognition = () => {
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(captureAndRecognize, 500);
};

const stopRecognition = () => {
    if (intervalId) clearInterval(intervalId);
    if (stream) stream.getTracks().forEach(track => track.stop());
};
</script>