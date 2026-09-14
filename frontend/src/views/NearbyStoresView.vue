<script setup>
import { computed, onMounted, ref } from "vue"
import StoreMap from "../components/StoreMap.vue"
import FilterBox from "../components/FilterBox.vue"
import { apiErrorMessage, nearbyRegisteredStores, listPaymentMethods } from "../api"

const stores = ref([])
const currentLocation = ref(null)
const loading = ref(true)
const error = ref("")
const paymentMethods = ref([])
const selectedPaymentMethodIds = ref([])
const selectedCategories = ref([])

const NEARBY_RADIUS_METERS = 1000

function distanceMeters(latitude1, longitude1, latitude2, longitude2) {
  const earthRadius = 6371000
  const toRadians = (value) => value * Math.PI / 180

  const lat1 = toRadians(latitude1)
  const lat2 = toRadians(latitude2)
  const deltaLat = toRadians(latitude2 - latitude1)
  const deltaLng = toRadians(longitude2 - longitude1)

  const a = Math.sin(deltaLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLng / 2) ** 2

  return earthRadius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

const nearbyStores = computed(() => {
  if (!currentLocation.value) return []

  return stores.value.filter((store) => {
    if (store.latitude === null || store.longitude === null) return false

    return distanceMeters(
      currentLocation.value.latitude,
      currentLocation.value.longitude,
      Number(store.latitude),
      Number(store.longitude),
    ) <= NEARBY_RADIUS_METERS
  })
})

function getCurrentLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Location information is not supported by this browser."))
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      }),
      reject,
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      },
    )
  })
}

async function fetchNearbyStores() {
  if (!currentLocation.value) return

  const params = {
    latitude: currentLocation.value.latitude,
    longitude: currentLocation.value.longitude,
    radius: NEARBY_RADIUS_METERS,
  }

  if (selectedPaymentMethodIds.value.length > 0) {
    params.payment_methods = selectedPaymentMethodIds.value.join(",")
  }

  if (selectedCategories.value.length > 0) {
    params.categories = selectedCategories.value.join(",")
  }

  stores.value = await nearbyRegisteredStores(params)
}

async function applyFilters() {
  try {
    error.value = ""
    await fetchNearbyStores()
  } catch (err) {
    error.value = apiErrorMessage(err)
  }
}

async function load() {
  loading.value = true
  error.value = ""

  try {
    const [location, methodData] = await Promise.all([
      getCurrentLocation(),
      listPaymentMethods(),
    ])

    currentLocation.value = location
    paymentMethods.value = Array.isArray(methodData)
      ? methodData
      : methodData.results || []

    await fetchNearbyStores()
  } catch (err) {
    if (err?.code === 1) {
      error.value = "Location permission was denied."
    } else if (err?.code === 2) {
      error.value = "Your location could not be determined."
    } else if (err?.code === 3) {
      error.value = "Getting your location timed out."
    } else if (err?.response) {
      error.value = apiErrorMessage(err)
    } else {
      error.value = err?.message || "Could not get your location."
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="nearby-page">
    <div v-if="loading" class="empty-state">Getting your location…</div>

    <p v-else-if="error" class="alert error">{{ error }}</p>

    <template v-else>
      <FilterBox
        :payment-methods="paymentMethods"
        v-model:selected-payment-methods="selectedPaymentMethodIds"
        v-model:selected-categories="selectedCategories"
        @apply="applyFilters"
      />

      <StoreMap
        :stores="nearbyStores"
        :current-location="currentLocation"
      />
    </template>

    <div class="nearby-actions">
      <RouterLink class="button secondary" to="/">Back</RouterLink>
      <RouterLink class="button secondary" to="/stores/new">
        Add a new store
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.nearby-page {
  width: 100%;
  padding-top: 24px;
}

.nearby-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}

@media (max-width: 600px) {
  .nearby-actions {
    flex-direction: column;
  }
}
</style>