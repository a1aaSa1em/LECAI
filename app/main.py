from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .reconciliation_agent import ReconciliationAgent
from .sources import get_source_a_assets, get_source_b_assets
from .store import canonical_store


agent = ReconciliationAgent(
    store=canonical_store,
    source_a_loader=get_source_a_assets,
    source_b_loader=get_source_b_assets,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await agent.start()
    try:
        yield
    finally:
        await agent.stop()


app = FastAPI(title="Asset Reconciliation Agent", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/source-a/assets")
def source_a_assets():
    return get_source_a_assets()


@app.get("/source-b/assets")
def source_b_assets():
    return get_source_b_assets()


@app.post("/agent/poll-once")
def poll_once():
    return agent.poll_once()


@app.post("/agent/start")
async def start_agent():
    return await agent.start()


@app.post("/agent/stop")
async def stop_agent():
    return await agent.stop()


@app.get("/agent/status")
def agent_status():
    return agent.status()


@app.get("/assets")
def list_assets():
    return canonical_store.list_assets()


@app.get("/assets/{asset_id}")
def get_asset(asset_id: str):
    asset = canonical_store.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@app.get("/decisions")
def list_decisions():
    return canonical_store.list_decisions()
