import { createRouter, createWebHashHistory } from 'vue-router'
import LoginView from '../views/auth/LoginView.vue'
import RegisterView from '../views/auth/RegisterView.vue'
import EvalView from '../views/evaluator/EvalView.vue'
import ResultView from '../views/evaluator/ResultView.vue'
import AdminLayout from '../views/admin/AdminLayout.vue'
import AdminOverview from '../views/admin/AdminOverview.vue'
import SceneManage from '../views/admin/SceneManage.vue'
import ModelManage from '../views/admin/ModelManage.vue'
import ImageManage from '../views/admin/ImageManage.vue'
import PairManage from '../views/admin/PairManage.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: LoginView },
  { path: '/register', name: 'Register', component: RegisterView },
  { path: '/eval', name: 'Eval', component: EvalView },
  { path: '/result', name: 'Result', component: ResultView },
  {
    path: '/admin',
    component: AdminLayout,
    children: [
      { path: '', redirect: '/admin/overview' },
      { path: 'overview', name: 'AdminOverview', component: AdminOverview },
      { path: 'scenes', name: 'SceneManage', component: SceneManage },
      { path: 'models', name: 'ModelManage', component: ModelManage },
      { path: 'images', name: 'ImageManage', component: ImageManage },
      { path: 'pairs', name: 'PairManage', component: PairManage },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('blind_eval_token')
  if (!['Login', 'Register'].includes(to.name) && !token) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
