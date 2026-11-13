import sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory
from app.core.security import hash_password, utc_now
from app.models.user import User
from app.models.organisation import Organisation, OrganisationMembership
from app.models.project import Project, ProjectMembership, ProjectTransition
from app.models.rbac import Role, UserRole

settings = get_settings()
engine = create_db_engine(settings)
session_factory = create_session_factory(engine)
db = session_factory()

try:
    # 1. Get Roles
    std_role = db.query(Role).filter(Role.name == "standard_user").first()
    admin_role = db.query(Role).filter(Role.name == "platform_admin").first()
    org_owner_role = db.query(Role).filter(Role.name == "org_owner").first()
    pm_role = db.query(Role).filter(Role.name == "project_manager").first()
    member_role = db.query(Role).filter(Role.name == "project_member").first()

    now = utc_now()
    pw_hash = hash_password("Handover123!Secure")

    # 2. Create Users
    user1 = User(
        id=uuid.uuid4(),
        email="engineer_live@handover.internal",
        full_name="Test Engineer",
        password_hash=pw_hash,
        status="active",
        is_email_verified=True,
        email_verified_at=now,
        created_at=now,
        updated_at=now,
    )
    user2 = User(
        id=uuid.uuid4(),
        email="shubham392007@gmail.com",
        full_name="Shubham",
        password_hash=pw_hash,
        status="active",
        is_email_verified=True,
        email_verified_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add_all([user1, user2])
    db.flush()

    # User Roles
    db.add_all([
        UserRole(id=uuid.uuid4(), user_id=user1.id, role_id=admin_role.id),
        UserRole(id=uuid.uuid4(), user_id=user1.id, role_id=std_role.id),
        UserRole(id=uuid.uuid4(), user_id=user2.id, role_id=admin_role.id),
        UserRole(id=uuid.uuid4(), user_id=user2.id, role_id=std_role.id),
    ])

    # 3. Create Organisations
    org1 = Organisation(
        id=uuid.uuid4(),
        name="The Handover",
        slug="the-handover",
        created_by_id=user1.id,
        created_at=now,
        updated_at=now,
    )
    org2 = Organisation(
        id=uuid.uuid4(),
        name="The Sapiens",
        slug="the-sapiens",
        created_by_id=user1.id,
        created_at=now,
        updated_at=now,
    )
    db.add_all([org1, org2])
    db.flush()

    # Org Memberships
    db.add_all([
        OrganisationMembership(id=uuid.uuid4(), organisation_id=org1.id, user_id=user1.id, role_id=org_owner_role.id, status="active", created_at=now, updated_at=now),
        OrganisationMembership(id=uuid.uuid4(), organisation_id=org1.id, user_id=user2.id, role_id=org_owner_role.id, status="active", created_at=now, updated_at=now),
        OrganisationMembership(id=uuid.uuid4(), organisation_id=org2.id, user_id=user1.id, role_id=org_owner_role.id, status="active", created_at=now, updated_at=now),
        OrganisationMembership(id=uuid.uuid4(), organisation_id=org2.id, user_id=user2.id, role_id=org_owner_role.id, status="active", created_at=now, updated_at=now),
    ])

    # 4. Create Project
    proj1 = Project(
        id=uuid.uuid4(),
        organisation_id=org1.id,
        name="Handover Core Platform",
        slug="handover-core-platform",
        description="Core platform knowledge reconstruction and handover intelligence engine.",
        created_by_id=user1.id,
        owner_id=user1.id,
        created_at=now,
        updated_at=now,
    )
    db.add(proj1)
    db.flush()

    # Project Memberships
    db.add_all([
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj1.id,
            user_id=user1.id,
            role_id=pm_role.id,
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj1.id,
            user_id=user2.id,
            role_id=member_role.id,
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectTransition(
            id=uuid.uuid4(),
            project_id=proj1.id,
            departing_user_id=user2.id,
            successor_user_id=user1.id,
            handover_scope="Full core platform reconstruction, technical architecture and operational procedures.",
            workflow_stage="evidence_extraction",
            created_at=now,
            updated_at=now,
        ),
    ])

    db.commit()
    print("Local database successfully seeded with organisations, projects, and users!")
except Exception as e:
    db.rollback()
    import traceback
    traceback.print_exc()
finally:
    db.close()
