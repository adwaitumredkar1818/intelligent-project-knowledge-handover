import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)
login_res = client.post("/api/v1/auth/login", json={"email": "engineer_live@handover.internal", "password": "Handover123!Secure"})
print("Login status:", login_res.status_code)
token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

me_res = client.get("/api/v1/auth/me", headers=headers)
print("Auth Me:", me_res.json().get("email"), me_res.json().get("full_name"))

orgs_data = client.get("/api/v1/organisations", headers=headers).json()
orgs = orgs_data.get("items", orgs_data) if isinstance(orgs_data, dict) else orgs_data
print("Accessible Orgs:", [(o["name"], o["slug"]) for o in orgs])

for org in orgs:
    projs_data = client.get(f"/api/v1/organisations/{org['id']}/projects", headers=headers).json()
    projs = projs_data.get("items", projs_data) if isinstance(projs_data, dict) else projs_data
    print(f"\nOrg: {org['name']} ({len(projs)} projects):")
    for p in projs:
        print(f"  - Project: {p['name']} ({p['slug']}), my_project_role={p.get('my_project_role')}")
        mems_data = client.get(f"/api/v1/projects/{p['id']}/members", headers=headers).json()
        mems = mems_data.get("items", mems_data) if isinstance(mems_data, dict) else mems_data
        print(f"    Members: {mems}")
        trans_res = client.get(f"/api/v1/projects/{p['id']}/transition", headers=headers)
        if trans_res.status_code == 200 and trans_res.json():
            t = trans_res.json()
            dep = t.get("departing_user") or {}
            suc = t.get("successor_user") or {}
            print(f"    Transition: stage={t.get('workflow_stage')}, departing={dep.get('email')}, successor={suc.get('email')}")
        else:
            print(f"    Transition: None ({trans_res.status_code})")
