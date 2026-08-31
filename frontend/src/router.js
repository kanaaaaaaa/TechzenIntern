import { createRouter, createWebHistory } from "vue-router"

import HomeView from "./views/HomeView.vue"
import StoreDetailView from "./views/StoreDetailView.vue"
import StoreFormView from "./views/StoreFormView.vue"
import StoreListView from "./views/StoreListView.vue"


const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/stores", name: "stores", component: StoreListView },
    { path: "/stores/new", name: "store-new", component: StoreFormView },
    { path: "/stores/:id", name: "store-detail", component: StoreDetailView, props: true },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router

