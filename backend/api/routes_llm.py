# -*- coding: utf-8 -*-
"""
api/routes_llm.py — служебные эндпоинты LLM (ТИТАН-5).
  GET /api/llm/status — какие провайдеры доступны
"""

from fastapi import APIRouter
from core import llm_router

router = APIRouter()


@router.get("/api/llm/status")
async def llm_status():
    """Статус всех LLM-провайдеров."""
    return await llm_router.check_status()
