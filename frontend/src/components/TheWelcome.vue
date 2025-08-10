<template>
    <div class="welcome">
        <h1>Welcome to Face Recognition App</h1>
        <p>
            This application allows you to register faces and recognize them using your webcam.
            It is built with Vue.js and uses the MediaDevices API for camera access.
        </p>
        <p>
            You can navigate to the <router-link to="/register">Register</router-link> page to add new faces,
            or go to the <router-link to="/recognize">Recognition</router-link> page to test face recognition.
        </p>
    </div>
</template>
