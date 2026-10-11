# Map Source

`china-provinces.json` was downloaded on 2026-10-01 from the DataV geographic boundary endpoint:

https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json

The footprint overview renders these boundaries as SVG using a Lambert conformal conic projection (standard parallels 25° and 47°, central meridian 105°). It includes Taiwan, Hong Kong, Macao and a South China Sea inset. Visited provinces are identified by point-in-polygon checks that support MultiPolygon islands and polygon holes. The location editor continues to use Leaflet for city search and precise picking. No tile or geocoding service is needed at runtime. Locations are stored as latitude and longitude. This is a memory visualization, not a navigation map.

Located records are sorted by their event dates and grouped by calendar month. The chronological route mode connects records within each month. The home-origin mode connects one saved home location independently to each unique destination in the current scope (all footprints or the selected month). Destinations at the home coordinates are skipped; repeated visits share a route, while each original record remains in the journey list. Animated dashes and SVG airplane silhouettes can be paused or played at 1× / 2×; airplanes rotate to follow the path direction. These curves visualize memories, not actual airline routes.

Home locations can be selected using the local city index or entered as latitude/longitude. They are stored in localStorage under `shiguangji-footprint-home-<userId>` and isolated by account on the same browser; no server-side home address is stored or inferred. The home location is included in the map projection extent when the home-origin mode is active, and it uses a distinct house marker. It does not add visits or dates to statistics.

Points at the same coordinates (rounded to three decimal places) share one city marker. Statistics use unique marker locations, visited province regions and dates containing located records. The overview supports desktop map/detail columns, zoom, dragging, year filtering from the timeline and opening the original record. Reduced-motion preferences pause playback by default.

`china-cities.json` contains 370 local city/region centers. It was generated on 2026-10-01 from the province child-boundary properties (`name`, `adcode`, `center`, `centroid`) at the same DataV endpoint. Municipalities, Hong Kong and Macao use their province centers. DataV does not supply Taiwan city centers; Taipei retains the application's previous coordinate. This index covers prefecture cities, prefectures and directly administered regions, not every county or scenic attraction.

Regenerate with `node scripts/build-city-index.cjs` from the project root. Generation requires network access; runtime city/province search uses the local JSON. Selecting a result records its center; map picking and coordinate inputs remain available for precise locations.
