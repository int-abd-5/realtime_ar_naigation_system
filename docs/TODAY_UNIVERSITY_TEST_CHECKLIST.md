1. Confirm latest map assets are loaded
```powershell
python C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\scripts\update_map_assets.py --fused C:\Users\Abdul\Downloads\fused_final.ply --mesh C:\Users\Abdul\Downloads\mesh_final.ply --map-name floor_v2_half_floor_approved
```

2. Regenerate graph edges from current nodes
```powershell
python C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\scripts\generate_edges_from_nodes.py --nodes C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\navigation\nodes.json --edges C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\navigation\edges.json
```

3. Start backend
```powershell
cd C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend
.\run_backend.ps1
```

4. Verify backend status
```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/map
curl http://127.0.0.1:8000/api/v1/destinations
```

5. Frontend settings
- Frontend repo path used for integration: `C:\Users\Abdul\Desktop\_repo_check_nav_frontend`
- Edit host in:
  - `C:\Users\Abdul\Desktop\_repo_check_nav_frontend\app\src\main\java\com\mahad\arnavigation\network\BackendConfig.java`
- Set `HOST` to your laptop IPv4 on university Wi-Fi/hotspot.

6. Build/install frontend APK
- Open frontend project in Android Studio and run on phone.
- Keep laptop + phone on same network.

7. Demo flow
- Start app.
- Destination can be passed as room code or direct node id (`D1`, `D2`, `D3`, `D4`).
- Backend streams navigation instructions (`TURN_LEFT`, `TURN_RIGHT`, `GO_STRAIGHT`, `ARRIVED`) in realtime over WebSocket.

8. Important note
- Current localization is session-wise dead-reckoning initialized from the chosen start node, suitable for today's realtime product demo with the approved half-floor map.
