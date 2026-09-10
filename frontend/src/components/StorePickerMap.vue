<script setup>
import { nextTick, ref } from "vue"
import { apiErrorMessage, nearbyPlaces } from "../api"
import { loadGoogleMapsLibrary } from "../googleMaps"

const emit = defineEmits(["select-place"])
const mapElement = ref(null)
const places = ref([])
const searching = ref(false)
const showMap = ref(false)
const mapError = ref("")
const locationMessage = ref("")

let map = null
let AdvancedMarkerElement = null
let PinElement = null
let InfoWindow = null
let infoWindow = null
let currentLocationMarker = null
let markers = []

function clearMarkers() {
  markers.forEach((marker) => { marker.map = null })
  markers = []
}

function selectPlace(place) {
  emit("select-place", place)
  locationMessage.value = `${place.name} was added to the form.`
  infoWindow?.close()
}

function openPlaceInfo(marker, place) {
  const content = document.createElement("div")
  content.style.minWidth = "180px"
  content.style.padding = "4px"

  const name = document.createElement("strong")
  name.textContent = place.name || "Unnamed place"
  name.style.display = "block"
  name.style.marginBottom = "6px"
  content.appendChild(name)

  if (place.address) {
    const address = document.createElement("div")
    address.textContent = place.address
    address.style.fontSize = "12px"
    address.style.marginBottom = "8px"
    content.appendChild(address)
  }

  const button = document.createElement("button")
  button.type = "button"
  button.textContent = "Use this store"
  button.className = "button primary"
  button.addEventListener("click", () => selectPlace(place))
  content.appendChild(button)

  infoWindow.setContent(content)
  infoWindow.open({ map, anchor: marker })
}

function showCurrentLocation(latitude, longitude) {
  if (currentLocationMarker) {
    currentLocationMarker.map = null
    currentLocationMarker = null
  }

  const currentPin = new PinElement({
    background: "#4285F4",
    borderColor: "#FFFFFF",
    glyphColor: "#FFFFFF",
    glyphText: "●",
    scale: 1.3,
  })

  currentLocationMarker = new AdvancedMarkerElement({
    map,
    position: { lat: latitude, lng: longitude },
    title: "Current location",
  })

  currentLocationMarker.append(currentPin)

  currentLocationMarker.addListener("click", () => {
    const content = document.createElement("strong")
    content.textContent = "Your current location"

    infoWindow.setContent(content)
    infoWindow.open({ map, anchor: currentLocationMarker })
  })
}

function drawPlaceMarkers() {
  if (!map || !AdvancedMarkerElement) return

  clearMarkers()

  places.value.forEach((place) => {
    if (place.latitude === null || place.latitude === undefined ||
        place.longitude === null || place.longitude === undefined) return

    const latitude = Number(place.latitude)
    const longitude = Number(place.longitude)

    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return

    const marker = new AdvancedMarkerElement({
      map,
      position: { lat: latitude, lng: longitude },
      title: place.name || "Unnamed place",
    })

    marker.addListener("click", () => openPlaceInfo(marker, place))
    markers.push(marker)
  })
}

function locationErrorMessage(error) {
  if (error.code === 1) return "Location permission was denied. You can still enter the store manually."
  if (error.code === 2) return "Your location could not be determined. You can still enter the store manually."
  if (error.code === 3) return "Getting your location timed out. You can still enter the store manually."
  return "Could not get your location. You can still enter the store manually."
}

async function searchPlaces(latitude, longitude) {
  try {
    places.value = await nearbyPlaces({ latitude, longitude, radius: 100 })
    drawPlaceMarkers()

    locationMessage.value = places.value.length
      ? `${places.value.length} nearby places found. Click a pin to see the store name.`
      : "No nearby places were found."
  } catch (err) {
    mapError.value = apiErrorMessage(err)
  } finally {
    searching.value = false
  }
}

async function initializeMap() {
  if (map) return true

  try {
    const mapsLibrary = await loadGoogleMapsLibrary("maps")
    const markerLibrary = await loadGoogleMapsLibrary("marker")

    const { Map } = mapsLibrary

    InfoWindow = mapsLibrary.InfoWindow
    AdvancedMarkerElement = markerLibrary.AdvancedMarkerElement
    PinElement = markerLibrary.PinElement
    infoWindow = new InfoWindow()

    map = new Map(mapElement.value, {
      center: { lat: 16.0544, lng: 108.2022 },
      zoom: 14,
      mapId: "DEMO_MAP_ID",
    })

    return true
  } catch (err) {
    console.error(err)
    mapError.value = "Failed to load Google Maps."
    return false
  }
}

async function findNearbyStores() {
  mapError.value = ""
  locationMessage.value = ""

  if (!navigator.geolocation) {
    mapError.value = "Location information is not supported by this browser."
    return
  }

  searching.value = true
  showMap.value = true

  await nextTick()

  const ready = await initializeMap()

  if (!ready) {
    searching.value = false
    return
  }

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const latitude = position.coords.latitude
      const longitude = position.coords.longitude

      const radius = 100
      const latitudeDelta = radius / 111320
      const longitudeDelta = radius / (111320 * Math.cos(latitude * Math.PI / 180))

      map.fitBounds({
        north: latitude + latitudeDelta,
        south: latitude - latitudeDelta,
        east: longitude + longitudeDelta,
        west: longitude - longitudeDelta,
      }, 0)

      showCurrentLocation(latitude, longitude)
      await searchPlaces(latitude, longitude)
    },
    (error) => {
      searching.value = false
      mapError.value = locationErrorMessage(error)
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 60000,
    },
  )
}
</script>

<template>
  <div class="store-picker">
    <div class="store-picker-heading">
      <div>
        <strong>Don't know the store name?</strong>
        <p>Find stores near your current location.</p>
      </div>

      <button class="button secondary" type="button" :disabled="searching" @click="findNearbyStores">
        {{ searching ? "Searching…" : "Find nearby stores" }}
      </button>
    </div>

    <p v-if="mapError" class="alert error">{{ mapError }}</p>
    <p v-if="locationMessage" class="section-note">{{ locationMessage }}</p>

    <div v-if="showMap" ref="mapElement" class="store-picker-map" />
  </div>
</template>

<style scoped>
.store-picker {
  margin-top: 24px;
}

.store-picker-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.store-picker-heading p {
  margin: 4px 0 0;
}

.store-picker-map {
  width: 100%;
  height: 420px;
  margin-top: 12px;
  border-radius: 12px;
  overflow: hidden;
}

@media (max-width: 800px) {
  .store-picker-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .store-picker-map {
    height: 360px;
  }
}
</style>