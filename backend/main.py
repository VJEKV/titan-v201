# -*- coding: utf-8 -*-
"""
main.py — FastAPI точка входа для ТИТАН Аудит ТОРО v.200
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes_upload import router as upload_router
from api.routes_kpi import router as kpi_router
from api.routes_filters import router as filters_router
from api.routes_finance import router as finance_router
from api.routes_timeline import router as timeline_router
from api.routes_work_types import router as work_types_router
from api.routes_planners import router as planners_router
from api.routes_workplaces import router as workplaces_router
from api.routes_risks import router as risks_router
from api.routes_quality import router as quality_router
from api.routes_orders import router as orders_router
from api.routes_equipment import router as equipment_router
from api.routes_export import router as export_router

app = FastAPI(
    title="ТИТАН Аудит ТОРО v.200",
    description="Аналитическая система аудита заказов ТОРО",
    version="2.0.0"
)

# CORS — разрешить Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутов
app.include_router(upload_router)
app.include_router(kpi_router)
app.include_router(filters_router)
app.include_router(finance_router)
app.include_router(timeline_router)
app.include_router(work_types_router)
app.include_router(planners_router)
app.include_router(workplaces_router)
app.include_router(risks_router)
app.include_router(quality_router)
app.include_router(orders_router)
app.include_router(equipment_router)
app.include_router(export_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# Раздача собранного React (production)
dist_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
if os.path.isdir(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")
