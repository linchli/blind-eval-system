import { createRouter, createWebHashHistory } from 'vue-router'
import LoginView from '../views/auth/LoginView.vue'
import RegisterView from '../views/auth/RegisterView.vue'
import EvalView from '../views/evaluator/EvalView.vue'
import ResultView from '../views/evaluator/ResultView.vue'
import RankingView from '../views/evaluator/RankingView.vue'
import AdminLayout from '../views/admin/AdminLayout.vue'
import AdminOverview from '../views/admin/AdminOverview.vue'
import SceneManage from '../views/admin/SceneManage.vue'
import DeviceManage from '../views/admin/DeviceManage.vue'
import ImageManage from '../views/admin/ImageManage.vue'
import PairManage from '../views/admin/PairManage.vue'
import UserManage from '../views/admin/UserManage.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: LoginView },
  { path: '/register', name: 'Register', component: RegisterView },
  { path: '/reset-password', name: 'ResetPassword', component: () => import('../views/auth/ResetPasswordView.vue') },
  { path: '/eval', name: 'Eval', component: EvalView },
  { path: '/result', name: 'Result', component: ResultView },
  { path: '/ranking', name: 'Ranking', component: RankingView },
  {
    path: '/admin',
    component: AdminLayout,
    children: [
      { path: '', redirect: '/admin/overview' },
      { path: 'overview', name: 'AdminOverview', component: AdminOverview },
      { path: 'scenes', name: 'SceneManage', component: SceneManage },
      { path: 'devices', name: 'DeviceManage', component: DeviceManage },
      { path: 'images', name: 'ImageManage', component: ImageManage },
      { path: 'pairs', name: 'PairManage', component: PairManage },
      { path: 'users', name: 'UserManage', component: UserManage },
      { path: 'cleaning', name: 'CleaningManage', component: () => import('../views/admin/CleaningView.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'ranking', name: 'AdminRanking', component: RankingView, meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'batch-upload', name: 'BatchUpload', component: () => import('../views/admin/BatchUpload.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('blind_eval_token')
  // 不需要登录的页面
  const publicPages = ['Login', 'Register', 'Ranking', 'ResetPassword']
  if (!publicPages.includes(to.name) && !token) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
