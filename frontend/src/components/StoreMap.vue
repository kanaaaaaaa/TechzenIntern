<script setup>
import { onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { loadGoogleMapsLibrary } from "../googleMaps"

const router = useRouter()

const props = defineProps({
  stores: {
    type: Array,
    default: () => [],
  },
  currentLocation: {
    type: Object,
    default: null,
  },
})

const statusSymbols = {
  accepted: "〇",
  not_accepted: "×",
  unknown: "？",
}

const mapElement = ref(null)
const mapError = ref("")

let map = null
let AdvancedMarkerElement = null
let PinElement = null
let infoWindow = null
let currentLocationMarker = null
let markers = []

function hasLocation(store) {
  return store.latitude !== null &&
    store.latitude !== undefined &&
    store.longitude !== null &&
    store.longitude !== undefined &&
    Number.isFinite(Number(store.latitude)) &&
    Number.isFinite(Number(store.longitude))
}

function clearMarkers() {
  markers.forEach((marker) => {
    marker.map = null
  })
  markers = []
}

function openStoreInfo(marker, store) {
  const content = document.createElement("div")
  content.style.padding = "0 4px 4px"

  const name = document.createElement("button")
  name.type = "button"
  name.textContent = store.name
  name.style.border = "0"
  name.style.padding = "0"
  name.style.margin = "0"
  name.style.background = "transparent"
  name.style.fontWeight = "700"
  name.style.fontSize = "18px"
  name.style.lineHeight = "1.2"
  name.style.cursor = "pointer"
  name.style.textDecoration = "underline"

  name.addEventListener("click", () => {
    router.push({
      name: "stores",
      query: { q: store.name },
    })
  })

  content.appendChild(name)
  
  if (store.category) {
    const category = document.createElement("div")

    category.textContent = store.category
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase())

    category.style.display = "block"
    category.style.width = "fit-content"
    category.style.marginTop = "8px"
    category.style.padding = "3px 8px"
    category.style.borderRadius = "4px"
    category.style.background = "#eef5ef"
    category.style.color = "#2f6f50"
    category.style.fontSize = "11px"
    category.style.fontWeight = "700"

    content.appendChild(category)
  }

  if (store.payment_methods?.length) {
    const methods = document.createElement("div")
    methods.className = "method-tags"
    methods.style.marginTop = "8px"

    store.payment_methods.forEach((item) => {
      const tag = document.createElement("span")
      tag.className = item.status
      tag.textContent =
        `${statusSymbols[item.status] || "？"}｜${item.payment_method.name}`

      methods.appendChild(tag)
    })

    content.appendChild(methods)
  }

  infoWindow.setContent(content)
  infoWindow.open({
    map,
    anchor: marker,
  })
}

function drawCurrentLocation() {
  if (currentLocationMarker) {
    currentLocationMarker.map = null
    currentLocationMarker = null
  }

  if (!props.currentLocation) return

  const pin = new PinElement({
    background: "#4285F4",
    borderColor: "#FFFFFF",
    glyphColor: "#FFFFFF",
    glyphText: "●",
    scale: 1.3,
  })

  currentLocationMarker = new AdvancedMarkerElement({
    map,
    position: {
      lat: props.currentLocation.latitude,
      lng: props.currentLocation.longitude,
    },
    title: "Current location",
  })

  currentLocationMarker.append(pin)

  currentLocationMarker.addListener("click", () => {
    const content = document.createElement("strong")
    content.textContent = "Your current location"

    infoWindow.setContent(content)
    infoWindow.open({
      map,
      anchor: currentLocationMarker,
    })
  })
}

function fitCurrentArea() {
  if (!map || !props.currentLocation) return

  const latitude = props.currentLocation.latitude
  const longitude = props.currentLocation.longitude
  const radius = 100

  const latitudeDelta = radius / 111320
  const longitudeDelta =
    radius / (111320 * Math.cos(latitude * Math.PI / 180))

  map.fitBounds({
    north: latitude + latitudeDelta,
    south: latitude - latitudeDelta,
    east: longitude + longitudeDelta,
    west: longitude - longitudeDelta,
  }, 0)
}

function drawMarkers() {
  if (!map || !AdvancedMarkerElement) return

  clearMarkers()

  props.stores.forEach((store) => {
    if (!hasLocation(store)) return

    const marker = new AdvancedMarkerElement({
      map,
      position: {
        lat: Number(store.latitude),
        lng: Number(store.longitude),
      },
      title: store.name,
    })

    marker.addListener("click", () => {
      openStoreInfo(marker, store)
    })

    markers.push(marker)
  })

  drawCurrentLocation()
  fitCurrentArea()
}

async function initializeMap() {
  try {
    const mapsLibrary = await loadGoogleMapsLibrary("maps")
    const markerLibrary = await loadGoogleMapsLibrary("marker")

    AdvancedMarkerElement = markerLibrary.AdvancedMarkerElement
    PinElement = markerLibrary.PinElement
    infoWindow = new mapsLibrary.InfoWindow()

    const center = props.currentLocation
      ? {
          lat: props.currentLocation.latitude,
          lng: props.currentLocation.longitude,
        }
      : {
          lat: 16.0544,
          lng: 108.2022,
        }

    map = new mapsLibrary.Map(mapElement.value, {
      center,
      zoom: 18,
      mapId: "DEMO_MAP_ID",
    })

    drawMarkers()
  } catch (err) {
    console.error(err)
    mapError.value = "Failed to load Google Maps."
  }
}

watch(() => props.stores, drawMarkers, { deep: true })
watch(() => props.currentLocation, drawMarkers, { deep: true })

onMounted(initializeMap)
</script>

<template>
  <p v-if="mapError" class="alert error">
    {{ mapError }}
  </p>

  <div
    ref="mapElement"
    class="nearby-map"
  />
</template>

<style scoped>
.nearby-map {
  width: 100%;
  height: 620px;
  border-radius: 12px;
  overflow: hidden;
}

:global(.gm-style-iw-chr) {
  height: 20px;
}

@media (max-width: 800px) {
  .nearby-map {
    height: 520px;
  }
}
</style>