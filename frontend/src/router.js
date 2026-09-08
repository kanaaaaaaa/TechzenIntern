import { createRouter, createWebHistory } from "vue-router"

import { isUnlocked } from "./auth"
import HomeView from "./views/HomeView.vue"
import LoginView from "./views/LoginView.vue"
import StoreDetailView from "./views/StoreDetailView.vue"
import StoreFormView from "./views/StoreFormView.vue"
import StoreListView from "./views/StoreListView.vue"
import RegisterView from "./views/RegisterView.vue"


const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/register", name: "register", component: RegisterView, meta: { public: true } },
    { path: "/", name: "home", component: HomeView },
    { path: "/stores", name: "stores", component: StoreListView },
    { path: "/stores/new", name: "store-new", component: StoreFormView },
    { path: "/stores/:id", name: "store-detail", component: StoreDetailView, props: true },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  if (to.meta.public || isUnlocked()) return true
  return { name: "login", query: to.fullPath === "/" ? {} : { next: to.fullPath } }
})

export default router
