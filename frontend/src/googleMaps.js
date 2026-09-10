import {
  importLibrary,
  setOptions,
} from "@googlemaps/js-api-loader"

let configured = false

export function loadGoogleMapsLibrary(name) {
  if (!configured) {
    const apiKey =
      import.meta.env.VITE_GOOGLE_MAPS_API_KEY

    if (!apiKey) {
      throw new Error(
        "VITE_GOOGLE_MAPS_API_KEY is not set."
      )
    }

    setOptions({
      key: apiKey,
      v: "weekly",
    })

    configured = true
  }

  return importLibrary(name)
}