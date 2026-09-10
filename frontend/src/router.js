import { createRouter, createWebHistory } from "vue-router"

import AccountView from "./views/AccountView.vue"
import HomeView from "./views/HomeView.vue"
import LoginView from "./views/LoginView.vue"
import NearbyStoresView from "./views/NearbyStoresView.vue"
import StoreDetailView from "./views/StoreDetailView.vue"
import StoreFormView from "./views/StoreFormView.vue"
import StoreListView from "./views/StoreListView.vue"
import RegisterView from "./views/RegisterView.vue"


const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView },
    { path: "/register", name: "register", component: RegisterView },
    { path: "/account", name: "account", component: AccountView },
    { path: "/", name: "home", component: HomeView },
    { path: "/stores", name: "stores", component: StoreListView },
    { path: "/stores/new", name: "store-new", component: StoreFormView },
    { path: "/stores/nearby", name: "stores-nearby", component: NearbyStoresView },
    { path: "/stores/:id", name: "store-detail", component: StoreDetailView, props: true },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router
