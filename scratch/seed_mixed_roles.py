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
    # 1. Fetch RBAC Roles
    std_role = db.query(Role).filter(Role.name == "standard_user").first()
    admin_role = db.query(Role).filter(Role.name == "platform_admin").first()
    org_owner_role = db.query(Role).filter(Role.name == "org_owner").first()
    org_member_role = db.query(Role).filter(Role.name == "org_member").first()
    pm_role = db.query(Role).filter(Role.name == "project_manager").first()
    member_role = db.query(Role).filter(Role.name == "project_member").first()
    reviewer_role = db.query(Role).filter(Role.name == "reviewer").first()

    now = utc_now()
    pw_hash = hash_password("Handover123!Secure")

    # 2. Get or Create Users
    def get_or_create_user(email, full_name):
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                id=uuid.uuid4(),
                email=email,
                full_name=full_name,
                password_hash=pw_hash,
                status="active",
                is_email_verified=True,
                email_verified_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(u)
            db.flush()
            db.add_all([
                UserRole(id=uuid.uuid4(), user_id=u.id, role_id=admin_role.id),
                UserRole(id=uuid.uuid4(), user_id=u.id, role_id=std_role.id),
            ])
            db.flush()
        else:
            u.password_hash = pw_hash
            u.status = "active"
            u.is_email_verified = True
            db.flush()
        return u

    user1 = get_or_create_user("engineer_live@handover.internal", "Test Engineer")
    user2 = get_or_create_user("shubham392007@gmail.com", "Shubham")
    user3 = get_or_create_user("alex.chen@handover.internal", "Alex Chen")

    # 3. Get or Create Organisations
    def get_or_create_org(name, slug):
        o = db.query(Organisation).filter(Organisation.slug == slug).first()
        if not o:
            o = Organisation(
                id=uuid.uuid4(),
                name=name,
                slug=slug,
                created_by_id=user1.id,
                created_at=now,
                updated_at=now,
            )
            db.add(o)
            db.flush()
        return o

    org1 = get_or_create_org("The Handover", "the-handover")
    org2 = get_or_create_org("The Sapiens", "the-sapiens")
    org3 = get_or_create_org("Empty Sandbox Org", "empty-sandbox-org")

    # Ensure Organisation Memberships
    def ensure_org_member(org, user, role):
        m = db.query(OrganisationMembership).filter(
            OrganisationMembership.organisation_id == org.id,
            OrganisationMembership.user_id == user.id,
        ).first()
        if not m:
            m = OrganisationMembership(
                id=uuid.uuid4(),
                organisation_id=org.id,
                user_id=user.id,
                role_id=role.id,
                status="active",
                created_at=now,
                updated_at=now,
            )
            db.add(m)
            db.flush()
        else:
            m.status = "active"
            m.role_id = role.id
            db.flush()

    ensure_org_member(org1, user1, org_owner_role)
    ensure_org_member(org1, user2, org_member_role)
    ensure_org_member(org1, user3, org_member_role)

    ensure_org_member(org2, user1, org_owner_role)
    ensure_org_member(org2, user2, org_owner_role)

    ensure_org_member(org3, user1, org_owner_role)
    ensure_org_member(org3, user2, org_member_role)

    # 4. Clean up any existing projects in org3 (must remain 0 projects)
    org3_projects = db.query(Project).filter(Project.organisation_id == org3.id).all()
    for p in org3_projects:
        db.delete(p)
    db.flush()

    # 5. Clean up old projects in org1 to establish clean 5-project test matrix
    org1_projects = db.query(Project).filter(Project.organisation_id == org1.id).all()
    for p in org1_projects:
        db.delete(p)
    db.flush()

    # 6. Create the 5 Mixed-Role Projects in Org 1 ("The Handover")
    
    # Project A: Core Platform Engine -> user1 is Manager
    proj_a = Project(
        id=uuid.uuid4(),
        organisation_id=org1.id,
        name="Core Platform Engine",
        slug="core-platform-engine",
        description="Core platform runtime orchestration, backend APIs, and session management.",
        created_by_id=user1.id,
        owner_id=user1.id,
        created_at=now,
        updated_at=now,
    )
    db.add(proj_a)
    db.flush()
    db.add_all([
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_a.id,
            user_id=user1.id,
            role_id=pm_role.id,
            responsibility_description="Project lead and engineering manager.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_a.id,
            user_id=user2.id,
            role_id=member_role.id,
            responsibility_description="Backend services engineer.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_a.id,
            user_id=user3.id,
            role_id=member_role.id,
            responsibility_description="Infrastructure engineer.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
    ])

    # Project B: Legacy Auth Migration -> user1 is Departing Owner (Outgoing)
    proj_b = Project(
        id=uuid.uuid4(),
        organisation_id=org1.id,
        name="Legacy Auth Migration",
        slug="legacy-auth-migration",
        description="Migration of legacy JWT sessions to Argon2id and HttpOnly RefreshSession rotation.",
        created_by_id=user2.id,
        owner_id=user2.id,
        created_at=now,
        updated_at=now,
    )
    db.add(proj_b)
    db.flush()
    db.add_all([
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_b.id,
            user_id=user1.id,
            role_id=member_role.id,
            responsibility_description="Departing authentication architect.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_b.id,
            user_id=user2.id,
            role_id=pm_role.id,
            responsibility_description="Project manager and successor lead.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectTransition(
            id=uuid.uuid4(),
            project_id=proj_b.id,
            departing_user_id=user1.id,
            successor_user_id=user2.id,
            handover_scope="Full auth service migration, token rotation secrets, and security validation procedures.",
            workflow_stage="evidence_extraction",
            context_notes="All legacy session tables must be audited before final handover sign-off.",
            created_at=now,
            updated_at=now,
        ),
    ])

    # Project C: Knowledge Extraction Pipeline -> user1 is Successor (Incoming)
    proj_c = Project(
        id=uuid.uuid4(),
        organisation_id=org1.id,
        name="Knowledge Extraction Pipeline",
        slug="knowledge-extraction-pipeline",
        description="Document ingestion, OCR pipeline, and nomic-embed-text embedding integration.",
        created_by_id=user2.id,
        owner_id=user2.id,
        created_at=now,
        updated_at=now,
    )
    db.add(proj_c)
    db.flush()
    db.add_all([
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_c.id,
            user_id=user1.id,
            role_id=member_role.id,
            responsibility_description="Incoming lead for extraction pipeline.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_c.id,
            user_id=user2.id,
            role_id=pm_role.id,
            responsibility_description="Departing lead and project administrator.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectTransition(
            id=uuid.uuid4(),
            project_id=proj_c.id,
            departing_user_id=user2.id,
            successor_user_id=user1.id,
            handover_scope="Ollama runtime coordination, VRAM scheduler, and chunk indexing pipelines.",
            workflow_stage="review",
            context_notes="Verification of single-inference scheduler is required.",
            created_at=now,
            updated_at=now,
        ),
    ])

    # Project D: Compliance & Verification Engine -> user1 is Reviewer
    proj_d = Project(
        id=uuid.uuid4(),
        organisation_id=org1.id,
        name="Compliance & Verification Engine",
        slug="compliance-verification-engine",
        description="Human verification workflows, conflict resolution, and handover governance sign-offs.",
        created_by_id=user2.id,
        owner_id=user2.id,
        created_at=now,
        updated_at=now,
    )
    db.add(proj_d)
    db.flush()
    db.add_all([
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_d.id,
            user_id=user1.id,
            role_id=reviewer_role.id,
            responsibility_description="Designated human reviewer and quality auditor.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_d.id,
            user_id=user2.id,
            role_id=pm_role.id,
            responsibility_description="Project manager.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_d.id,
            user_id=user3.id,
            role_id=member_role.id,
            responsibility_description="Compliance data analyst.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
    ])

    # Project E: Frontend System Reference -> user1 is Member (Collaborator)
    proj_e = Project(
        id=uuid.uuid4(),
        organisation_id=org1.id,
        name="Frontend System Reference",
        slug="frontend-system-reference",
        description="Figma Make design system implementation, navigation shell, and accessibility standards.",
        created_by_id=user2.id,
        owner_id=user2.id,
        created_at=now,
        updated_at=now,
    )
    db.add(proj_e)
    db.flush()
    db.add_all([
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_e.id,
            user_id=user1.id,
            role_id=member_role.id,
            responsibility_description="Frontend developer and collaborator.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_e.id,
            user_id=user2.id,
            role_id=pm_role.id,
            responsibility_description="Project manager.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_e.id,
            user_id=user3.id,
            role_id=member_role.id,
            responsibility_description="UI/UX engineer.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
    ])

    # 7. Create Project in Org 2 ("The Sapiens")
    org2_projects = db.query(Project).filter(Project.organisation_id == org2.id).all()
    for p in org2_projects:
        db.delete(p)
    db.flush()

    proj_sapiens = Project(
        id=uuid.uuid4(),
        organisation_id=org2.id,
        name="Sapiens Knowledge Base",
        slug="sapiens-knowledge-base",
        description="Multi-tenant tenant isolation verification project.",
        created_by_id=user1.id,
        owner_id=user1.id,
        created_at=now,
        updated_at=now,
    )
    db.add(proj_sapiens)
    db.flush()
    db.add_all([
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_sapiens.id,
            user_id=user1.id,
            role_id=pm_role.id,
            responsibility_description="Tenant owner and project lead.",
            status="active",
            created_at=now,
            updated_at=now,
        ),
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=proj_sapiens.id,
            user_id=user2.id,
            role_id=member_role.id,
            status="active",
            created_at=now,
            updated_at=now,
        ),
    ])

    db.commit()
    print("SUCCESS: 5-Project Mixed-Role Test Matrix + Multi-tenant isolation seeded successfully!")
    print(f"Org 1 ('The Handover') projects:")
    print(f"  - Proj A: Core Platform Engine -> role for user1: Manager (owner={proj_a.owner_id == user1.id})")
    print(f"  - Proj B: Legacy Auth Migration -> role for user1: Outgoing (departing)")
    print(f"  - Proj C: Knowledge Extraction Pipeline -> role for user1: Incoming (successor)")
    print(f"  - Proj D: Compliance & Verification Engine -> role for user1: Reviewer")
    print(f"  - Proj E: Frontend System Reference -> role for user1: Member (Collaborator)")
    print(f"Org 2 ('The Sapiens') projects: 1 (Sapiens Knowledge Base)")
    print(f"Org 3 ('Empty Sandbox Org') projects: 0 (Empty workspace)")

except Exception as e:
    db.rollback()
    import traceback
    traceback.print_exc()
finally:
    db.close()
