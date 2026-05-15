import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'home',
            component: HomeView,
        },
        {
            path: '/register',
            name: 'register',
            component: () => import('../views/RegisterView.vue'),
        },
        {
            path: '/recognize',
            name: 'recognize',
            component: () => import('../views/RecognizeView.vue'),
        },
        {
            path: '/violation',
            name: 'violation',
            component: () => import('../views/ViolationView.vue'),
        }

    ],
})

export default router
