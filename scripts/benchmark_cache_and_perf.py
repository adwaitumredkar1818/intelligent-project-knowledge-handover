"""Comprehensive Performance & Caching Benchmarking Script.

Measures latency and throughput differences for:
1. Cache Service Latency (Set, Get, Invalidate)
2. Dashboard Overview Aggregation (Cold Uncached DB Query vs Warm Redis Cache)
3. Embedding Pipeline Caching (Cold Ollama call vs Cached Vector Chunk Retrieval)
4. Memory RSS Footprint (Backend process memory before and during operations)
"""

from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from datetime import UTC, datetime

import psutil
from app.core.cache import CacheKeys, CachePolicies, CacheService, RedisConnectionManager
from app.core.config import get_settings
from app.core.rbac_catalog import deterministic_rbac_id
from app.core.security import hash_password
from app.db.session import create_db_engine, create_session_factory
from app.models.enums import OrganisationStatus, ProjectStatus, ProjectVisibility, RoleName, UserStatus
from app.models.organisation import Organisation, OrganisationMembership
from app.models.project import Project, ProjectMembership
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.organisation import OrganisationRepository
from app.repositories.project import ProjectRepository
from app.repositories.rbac import RbacRepository
from app.repositories.user import UserRepository
from app.services.audit import AuditService
from app.services.embedding import OllamaEmbeddingService
from app.services.project import ProjectContext, ProjectService
from app.services.rbac import RbacService


def benchmark_suite() -> dict:
    settings = get_settings()
    results = {}
    proc = psutil.Process(os.getpid())
    results["baseline_rss_mb"] = round(proc.memory_info().rss / (1024 * 1024), 2)

    # 1. Cache Service Microbenchmarks
    redis_mgr = RedisConnectionManager(settings)
    redis_mgr.initialize()
    cache_svc = CacheService(settings, redis_mgr=redis_mgr)

    set_times = []
    get_times = []
    sample_payload = {"project_id": str(uuid.uuid4()), "metrics": list(range(100)), "status": "active"}

    for _ in range(100):
        k = f"bench:k:{uuid.uuid4()}"
        t0 = time.perf_counter()
        cache_svc.set(k, sample_payload, ttl=60)
        set_times.append((time.perf_counter() - t0) * 1000.0)

        t1 = time.perf_counter()
        cache_svc.get(k)
        get_times.append((time.perf_counter() - t1) * 1000.0)

    results["cache_microbenchmarks"] = {
        "set_mean_latency_ms": round(statistics.mean(set_times), 3),
        "set_p95_latency_ms": round(sorted(set_times)[int(len(set_times) * 0.95)], 3),
        "get_mean_latency_ms": round(statistics.mean(get_times), 3),
        "get_p95_latency_ms": round(sorted(get_times)[int(len(get_times) * 0.95)], 3),
        "operations_tested": 100,
    }

    # 2. Project Overview Dashboard Benchmark (Uncached DB vs Cached Redis)
    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    session = session_factory()

    tag = uuid.uuid4().hex[:6]
    test_user = User(
        email=f"bench_{tag}@handover.local",
        password_hash=hash_password("Password123!"),
        full_name="Benchmarking User",
        status=UserStatus.ACTIVE.value,
    )
    session.add(test_user)
    session.flush()

    test_org = Organisation(
        name=f"Bench Org {tag}",
        slug=f"bench-org-{tag}",
        status=OrganisationStatus.ACTIVE.value,
        created_by_id=test_user.id,
    )
    session.add(test_org)
    session.flush()

    test_proj = Project(
        organisation_id=test_org.id,
        name=f"Bench Project {tag}",
        slug=f"bench-proj-{tag}",
        status=ProjectStatus.ACTIVE.value,
        visibility=ProjectVisibility.PRIVATE.value,
        created_by_id=test_user.id,
        owner_id=test_user.id,
    )
    session.add(test_proj)
    session.flush()

    session.add_all([
        OrganisationMembership(
            organisation_id=test_org.id,
            user_id=test_user.id,
            role_id=deterministic_rbac_id("role", RoleName.ORG_OWNER.value),
            status="active",
            joined_at=datetime.now(UTC),
        ),
        ProjectMembership(
            project_id=test_proj.id,
            user_id=test_user.id,
            role_id=deterministic_rbac_id("role", RoleName.PROJECT_MANAGER.value),
            status="active",
        ),
    ])
    session.commit()

    rbac_service = RbacService(
        db_session=session,
        rbac_repository=RbacRepository(session),
        user_repository=UserRepository(session),
    )
    proj_service = ProjectService(
        db_session=session,
        org_repository=OrganisationRepository(session),
        project_repository=ProjectRepository(session),
        rbac_repository=RbacRepository(session),
        rbac_service=rbac_service,
        audit_service=AuditService(audit_repository=AuditLogRepository(session)),
    )
    principal = rbac_service.resolve_principal(user=test_user, session_family_id=uuid.uuid4())
    ctx = rbac_service.resolve_project_context(
        project_id=test_proj.id,
        principal=principal,
    )

    # Invalidate cache first to measure cold query
    cache_key = CacheKeys.dashboard_overview(test_proj.id, test_user.id)
    cache_svc.delete(cache_key)

    cold_latencies = []
    for _ in range(5):
        cache_svc.delete(cache_key)
        t0 = time.perf_counter()
        proj_service.get_project_overview(ctx)
        cold_latencies.append((time.perf_counter() - t0) * 1000.0)

    # Measure warm cached query
    warm_latencies = []
    for _ in range(20):
        t0 = time.perf_counter()
        proj_service.get_project_overview(ctx)
        warm_latencies.append((time.perf_counter() - t0) * 1000.0)

    cold_mean = statistics.mean(cold_latencies)
    warm_mean = statistics.mean(warm_latencies)
    results["dashboard_aggregation"] = {
        "cold_db_mean_ms": round(cold_mean, 2),
        "warm_cached_mean_ms": round(warm_mean, 2),
        "speedup_factor": round(cold_mean / warm_mean, 1) if warm_mean > 0 else 1.0,
        "latency_reduction_percent": round((1.0 - (warm_mean / cold_mean)) * 100, 1) if cold_mean > 0 else 0.0,
    }

    # 3. Embedding Pipeline Chunk-Level Deduplication & Cache
    emb_svc = OllamaEmbeddingService(
        base_url=settings.ollama.base_url,
        model=settings.ollama.embedding_model,
        cache_service=cache_svc,
    )
    sample_text = (
        "PostgreSQL 16 serves as the canonical source of truth for all structured entities, "
        "evidence records, and audit logs within The Handover platform."
    )

    # Cold embedding request (hits Ollama)
    t0 = time.perf_counter()
    vecs_cold = emb_svc.embed_documents([sample_text])
    cold_emb_time = (time.perf_counter() - t0) * 1000.0

    # Warm embedding request (hits Redis chunk embedding cache)
    t1 = time.perf_counter()
    vecs_warm = emb_svc.embed_documents([sample_text])
    warm_emb_time = (time.perf_counter() - t1) * 1000.0

    results["embedding_pipeline_cache"] = {
        "cold_inference_ms": round(cold_emb_time, 2),
        "cached_retrieval_ms": round(warm_emb_time, 2),
        "speedup_factor": round(cold_emb_time / warm_emb_time, 1) if warm_emb_time > 0 else 1.0,
        "vector_dimensions": len(vecs_warm[0]),
        "vectors_match": vecs_cold == vecs_warm,
    }

    results["final_rss_mb"] = round(proc.memory_info().rss / (1024 * 1024), 2)
    results["memory_delta_mb"] = round(results["final_rss_mb"] - results["baseline_rss_mb"], 2)

    return results


if __name__ == "__main__":
    benchmark_results = benchmark_suite()
    print("--- BENCHMARK RESULTS ---")
    print(json.dumps(benchmark_results, indent=2))
