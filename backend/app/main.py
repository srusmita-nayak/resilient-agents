import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import init_db
from app.db.repository import Repository
from app.experiments.orchestrator import ExperimentOrchestrator
from app.api.routes import create_api_router
from app.api.websocket import WebSocketManager

# Global singleton instances
repository = Repository()
orchestrator = ExperimentOrchestrator(repository)
ws_manager = WebSocketManager(repository)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 1. Initialize SQLite tables with WAL mode
    init_db()
    
    # 2. Reconcile interrupted runs from previous server runs
    interrupted_count = repository.reconcile_startup_interrupted_runs()
    if interrupted_count > 0:
        print(f"[STARTUP] Reconciled {interrupted_count} previously running runs as 'interrupted'.")

    # 3. Hook orchestrator events to WebSocket manager via event loop
    loop = asyncio.get_running_loop()
    def _on_orchestrator_event(event_dict):
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast_event(event_dict), loop)

    orchestrator.subscribe_events(_on_orchestrator_event)
    yield
    print("[SHUTDOWN] Resilient Agents server stopped.")

app = FastAPI(
    title="Resilient Agents Research Platform API",
    description="Fault-Tolerant Multi-Agent Coordination Research Platform",
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS configuration
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API
api_router = create_api_router(repository, orchestrator)
app.include_router(api_router)

# Mount WebSocket endpoint
@app.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.handle_client_message(websocket, data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=False)
