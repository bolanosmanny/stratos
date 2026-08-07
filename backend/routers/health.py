import logging

from fastapi import APIRouter, HTTPException
from supabase import Client


logger = logging.getLogger("stratos.api.health")


def create_health_router(supabase: Client) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def read_health():
        try:
            (
                supabase.table("document_chunks")
                .select("id")
                .limit(1)
                .execute()
            )

            return {
                "status": "healthy",
                "dependencies": {
                    "supabase": "connected",
                },
            }
        except Exception:
            logger.exception("health_check_failed dependency=supabase")

            raise HTTPException(
                status_code=503,
                detail="Supabase dependency is unavailable.",
            )

    return router