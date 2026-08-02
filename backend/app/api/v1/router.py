from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.career import public_router as career_public_router
from app.api.v1.career import router as career_router
from app.api.v1.cms import public_router as managed_content_router
from app.api.v1.cms import router as cms_router
from app.api.v1.diagnostic import router as diagnostic_router
from app.api.v1.labs import router as labs_router
from app.api.v1.learning import router as learning_router
from app.api.v1.mentor import router as mentor_router
from app.api.v1.missions import router as missions_router
from app.api.v1.operations import public_router as verification_router
from app.api.v1.operations import router as operations_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.projects import router as projects_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(career_router)
router.include_router(career_public_router)
router.include_router(cms_router)
router.include_router(managed_content_router)
router.include_router(diagnostic_router)
router.include_router(organizations_router)
router.include_router(operations_router)
router.include_router(verification_router)
router.include_router(learning_router)
router.include_router(labs_router)
router.include_router(missions_router)
router.include_router(mentor_router)
router.include_router(projects_router)
