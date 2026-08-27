import { Fragment } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { useEffect, useMemo } from 'react'

const CARGO = '#d94f3d'
const DECOY = '#4a8fb8'
const CHECKPOINT = '#e8a54b'

function FitBounds({ bounds }) {
  const map = useMap()
  useEffect(() => {
    if (!bounds) return
    const { south, north, west, east } = bounds
    if ([south, north, west, east].some((v) => v == null)) return
    map.fitBounds(
      [
        [south, west],
        [north, east],
      ],
      { padding: [40, 40] },
    )
  }, [bounds, map])
  return null
}

function positionAlong(waypoints, t) {
  if (!waypoints?.length) return null
  if (t <= waypoints[0].t) return [waypoints[0].lat, waypoints[0].lng]
  const last = waypoints[waypoints.length - 1]
  if (t >= last.t) return [last.lat, last.lng]
  for (let i = 0; i < waypoints.length - 1; i++) {
    const a = waypoints[i]
    const b = waypoints[i + 1]
    if (t >= a.t && t <= b.t) {
      const u = (t - a.t) / Math.max(1e-6, b.t - a.t)
      return [a.lat + (b.lat - a.lat) * u, a.lng + (b.lng - a.lng) * u]
    }
  }
  return [last.lat, last.lng]
}

function nearestWaypoint(waypoints, t) {
  if (!waypoints?.length) return null
  let best = waypoints[0]
  let bestDist = Math.abs(waypoints[0].t - t)
  for (const w of waypoints) {
    const d = Math.abs(w.t - t)
    if (d < bestDist) {
      best = w
      bestDist = d
    }
  }
  return best
}

export default function MapView({
  graph,
  trajectories,
  observerMode,
  playTime,
  checkpoints,
}) {
  const center = useMemo(() => {
    if (graph?.meta?.center) return [graph.meta.center.lat, graph.meta.center.lng]
    if (graph?.bounds) {
      return [
        (graph.bounds.north + graph.bounds.south) / 2,
        (graph.bounds.east + graph.bounds.west) / 2,
      ]
    }
    return [41.826, -71.4125]
  }, [graph])

  const checkpointSet = useMemo(() => new Set(checkpoints || []), [checkpoints])

  const edgeLines = useMemo(() => {
    if (!graph?.nodes || !graph?.edges) return []
    const byId = Object.fromEntries(graph.nodes.map((n) => [n.id, n]))
    return graph.edges
      .map((e) => {
        const a = byId[e.u]
        const b = byId[e.v]
        if (!a || !b) return null
        return [
          [a.lat, a.lng],
          [b.lat, b.lng],
        ]
      })
      .filter(Boolean)
  }, [graph])

  return (
    <MapContainer
      center={center}
      zoom={graph?.meta?.zoom || 15}
      className="h-full w-full"
      zoomControl={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <FitBounds bounds={graph?.bounds} />

      {!observerMode &&
        edgeLines.map((latlngs, i) => (
          <Polyline
            key={`e-${i}`}
            positions={latlngs}
            pathOptions={{ color: '#3a4552', weight: 2, opacity: 0.55 }}
          />
        ))}

      {graph?.nodes
        ?.filter((n) => n.checkpoint || checkpointSet.has(n.id))
        .map((n) => (
          <CircleMarker
            key={`cp-${n.id}`}
            center={[n.lat, n.lng]}
            radius={observerMode ? 7 : 5}
            pathOptions={{
              color: CHECKPOINT,
              fillColor: CHECKPOINT,
              fillOpacity: 0.35,
              weight: 1.5,
            }}
          >
            <Tooltip direction="top">Camera {n.id}</Tooltip>
          </CircleMarker>
        ))}

      {(trajectories || []).map((tr) => {
        const color = tr.role === 'cargo' ? CARGO : DECOY
        const coords = (tr.waypoints || []).map((w) => [w.lat, w.lng])
        const pos = positionAlong(tr.waypoints, playTime)
        const near = nearestWaypoint(tr.waypoints, playTime)
        const atCheckpoint =
          near && (checkpointSet.has(near.node) || graph?.nodes?.find((n) => n.id === near.node)?.checkpoint)

        if (observerMode) {
          // Only show vehicle if currently at (or last seen at) a checkpoint
          if (!atCheckpoint || !pos) return null
          return (
            <CircleMarker
              key={`obs-${tr.vehicle_id}`}
              center={pos}
              radius={9}
              pathOptions={{
                color: DECOY,
                fillColor: DECOY,
                fillOpacity: 0.9,
                weight: 2,
              }}
            >
              <Tooltip>Vehicle (identity hidden)</Tooltip>
            </CircleMarker>
          )
        }

        return (
          <Fragment key={tr.vehicle_id}>
            {coords.length > 1 && (
              <Polyline
                positions={coords}
                pathOptions={{
                  color,
                  weight: tr.role === 'cargo' ? 4 : 2.5,
                  opacity: tr.role === 'cargo' ? 0.9 : 0.55,
                  dashArray: tr.role === 'cargo' ? null : '6 8',
                }}
              />
            )}
            {pos && (
              <CircleMarker
                center={pos}
                radius={tr.role === 'cargo' ? 10 : 7}
                pathOptions={{
                  color,
                  fillColor: color,
                  fillOpacity: 0.95,
                  weight: 2,
                }}
              >
                <Tooltip>
                  {tr.role === 'cargo' ? 'Cargo' : 'Decoy'} · {tr.vehicle_id}
                </Tooltip>
              </CircleMarker>
            )}
          </Fragment>
        )
      })}
    </MapContainer>
  )
}
