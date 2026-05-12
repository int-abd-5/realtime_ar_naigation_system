1. Start backend locally
```powershell
cd C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend
.\run_backend.ps1
```

2. Confirm backend is running
```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/destinations
```

3. Get your PC LAN IP for phone testing
```powershell
ipconfig
```
Use the IPv4 of your active Wi-Fi adapter, for example `192.168.100.25`.

4. Start a navigation session from frontend
- HTTP:
  - `POST http://<PC_IP>:8000/api/v1/session/start`
  - Body:
```json
{
  "destination_id": "D3",
  "start_node_id": "C1"
}
```
- Response:
```json
{
  "session_id": "uuid-value",
  "start_node_id": "C1"
}
```

5. Open websocket stream
- URL:
`ws://<PC_IP>:8000/api/v1/session/<SESSION_ID>/stream`

6. Send frame messages from Android
- Message format:
```json
{
  "type": "frame",
  "timestamp_ms": 1714410000123,
  "jpeg_b64": "<base64-jpeg>",
  "heading_deg": 82.4
}
```
- Optional keepalive:
```json
{
  "type": "ping"
}
```

7. Receive navigation updates
```json
{
  "type": "nav_update",
  "pose": {"x": 0.12, "y": 0.0, "z": 1.33},
  "rotation": {"qx": 0.0, "qy": 0.41, "qz": 0.0, "qw": 0.91},
  "confidence": 0.54,
  "nearest_node": "C7",
  "next_node": "C8",
  "instruction": "TURN_RIGHT",
  "distance_m": 6.42,
  "target_label": "D3"
}
```

8. How to use this in AR UI
- `instruction` drives arrow state: `TURN_LEFT`, `TURN_RIGHT`, `GO_STRAIGHT`, `ARRIVED`.
- `distance_m` shows remaining distance.
- `confidence` can gate warnings like "Relocalizing..." when low.

9. Hosting decision
- For development: no cloud hosting needed. Keep phone and laptop on same Wi-Fi and use `ws://<PC_IP>:8000/...`.
- For production/public use: deploy backend on a server and use HTTPS/WSS (`https://` + `wss://`), TLS certificate, auth token, rate limiting, and logging.

10. Current localization mode
- `NAV_LOCALIZATION_MODE=mock` keeps the full realtime pipeline running while COLMAP fused output is still being prepared.
- Once map localization is ready, replace `app/localization.py` logic with visual localization from your COLMAP map, keeping the same websocket schema.
 - `NAV_LOCALIZATION_MODE=hybrid` now enables visual PnP localization with dead-reckoning fallback.
 - `NAV_LOCALIZATION_MODE=visual` prioritizes visual PnP against COLMAP sparse map.

11. Refresh map files and graph quickly
- Update map assets from new PLY files:
```powershell
python C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\scripts\update_map_assets.py --fused C:\Users\Abdul\Downloads\fused_final.ply --mesh C:\Users\Abdul\Downloads\mesh_final.ply --map-name floor_v2_half_floor_approved
```
- Regenerate `edges.json` from `nodes.json`:
```powershell
python C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\scripts\generate_edges_from_nodes.py --nodes C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\navigation\nodes.json --edges C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\navigation\edges.json
```

12. Build visual map package for PnP localization
```powershell
python C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\scripts\build_visual_map_package.py --model-dir C:\path\to\model_txt --database C:\path\to\database.db --images C:\path\to\images --out-dir C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\visual_map
```
