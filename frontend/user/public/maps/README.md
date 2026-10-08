# Map Source

`china-provinces.json` was downloaded on 2026-10-01 from the DataV geographic boundary endpoint:

https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json

The application renders these province boundaries locally using Leaflet. No tile or geocoding service is needed at runtime. Locations are stored as latitude and longitude. This is a memory visualization, not a navigation map.

`china-cities.json` contains 370 local city/region centers. It was generated on 2026-10-01 from the province child-boundary properties (`name`, `adcode`, `center`, `centroid`) at the same DataV endpoint. Municipalities, Hong Kong and Macao use their province centers. DataV does not supply Taiwan city centers; Taipei retains the application's previous coordinate. This index covers prefecture cities, prefectures and directly administered regions, not every county or scenic attraction.

Regenerate with `node scripts/build-city-index.cjs` from the project root. Generation requires network access; runtime city/province search uses the local JSON. Selecting a result records its center; map picking and coordinate inputs remain available for precise locations.
