import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import init_db
from app.db.repository import Repository
from app.experiments.orchestrator import ExperimentOrchestrator
from app.api.routes import create_api_router
from app.api.websocket import WebSocketManager

# Global singleton instances for default application
repository = Repository()
orchestrator = ExperimentOrchestrator(repository)
ws_manager = WebSocketManager(repository)


def create_app(
    db_path: Optional[Any] = None,
    repo: Optional[Repository] = None,
    orch: Optional[ExperimentOrchestrator] = None,
    ws: Optional[WebSocketManager] = None,
) -> FastAPI:
    """Application factory allowing isolated database and orchestrator for tests or custom deployments."""
    active_repo = repo or (Repository(db_path) if db_path else repository)
    active_orch = orch or (ExperimentOrchestrator(active_repo) if db_path else orchestrator)
    active_ws = ws or (WebSocketManager(active_repo) if db_path else ws_manager)

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None, None]:
        init_db(active_repo.db_path)
        interrupted_count = active_repo.reconcile_startup_interrupted_runs()
        if interrupted_count > 0:
            print(f"[STARTUP] Reconciled {interrupted_count} previously running runs as 'interrupted'.")

        try:
            loop = asyncio.get_running_loop()

            def _on_orchestrator_event(event_dict):
                coro = active_ws.broadcast_event(event_dict)
                try:
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(coro, loop)
                    else:
                        coro.close()
                except Exception:
                    coro.close()

            active_orch.subscribe_events(_on_orchestrator_event)
        except RuntimeError:
            pass
        yield
        active_orch.wait_idle(timeout=2.0)
        print("[SHUTDOWN] Resilient Agents server stopped.")

    app_instance = FastAPI(
        title="Resilient Agents Research Platform API",
        description="Fault-Tolerant Multi-Agent Coordination Research Platform",
        version=settings.VERSION,
        lifespan=lifespan,
    )
    app_instance.state.orchestrator = active_orch


    origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = create_api_router(active_repo, active_orch)
    app_instance.include_router(api_router)

    @app_instance.websocket("/ws/events")
    async def websocket_events_endpoint(websocket: WebSocket):
        await active_ws.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                await active_ws.handle_client_message(websocket, data)
        except WebSocketDisconnect:
            await active_ws.disconnect(websocket)
        except Exception:
            await active_ws.disconnect(websocket)

    return app_instance


# Default global application instance (used by uvicorn)
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=False)

