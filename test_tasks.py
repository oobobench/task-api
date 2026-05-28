def _create(client, headers, title, description=None, status_="todo"):
    payload = {"title": title, "status": status_}
    if description is not None:
        payload["description"] = description
    r = client.post("/tasks", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_list_returns_pagination_envelope(client, auth_headers):
    r = client.get("/tasks", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body == {"items": [], "total": 0, "page": 1, "per_page": 20, "pages": 0}


def test_pagination_splits_results_across_pages(client, auth_headers):
    for i in range(25):
        _create(client, auth_headers, f"task {i}")

    r1 = client.get("/tasks?page=1&per_page=10", headers=auth_headers)
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["total"] == 25
    assert b1["page"] == 1
    assert b1["per_page"] == 10
    assert b1["pages"] == 3
    assert len(b1["items"]) == 10

    r2 = client.get("/tasks?page=2&per_page=10", headers=auth_headers)
    b2 = r2.json()
    assert len(b2["items"]) == 10
    assert b2["page"] == 2

    r3 = client.get("/tasks?page=3&per_page=10", headers=auth_headers)
    b3 = r3.json()
    assert len(b3["items"]) == 5
    assert b3["page"] == 3

    seen = {t["id"] for t in b1["items"] + b2["items"] + b3["items"]}
    assert len(seen) == 25


def test_pagination_empty_page_beyond_range(client, auth_headers):
    for i in range(3):
        _create(client, auth_headers, f"task {i}")
    r = client.get("/tasks?page=5&per_page=10", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 3
    assert body["pages"] == 1


def test_status_filter(client, auth_headers):
    _create(client, auth_headers, "a", status_="todo")
    _create(client, auth_headers, "b", status_="in_progress")
    _create(client, auth_headers, "c", status_="done")

    r = client.get("/tasks?status=done", headers=auth_headers)
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "c"


def test_search_matches_title_and_description(client, auth_headers):
    _create(client, auth_headers, "Buy groceries", description="milk and eggs")
    _create(client, auth_headers, "Write report", description="quarterly summary")
    _create(client, auth_headers, "Call plumber", description="leaky pipe in kitchen")

    r = client.get("/tasks?search=groceries", headers=auth_headers)
    titles = [t["title"] for t in r.json()["items"]]
    assert titles == ["Buy groceries"]

    r = client.get("/tasks?search=quarterly", headers=auth_headers)
    titles = [t["title"] for t in r.json()["items"]]
    assert titles == ["Write report"]

    r = client.get("/tasks?search=KITCHEN", headers=auth_headers)
    titles = [t["title"] for t in r.json()["items"]]
    assert titles == ["Call plumber"]


def test_search_combined_with_status(client, auth_headers):
    _create(client, auth_headers, "alpha review", status_="todo")
    _create(client, auth_headers, "alpha ship", status_="done")
    _create(client, auth_headers, "beta review", status_="todo")

    r = client.get("/tasks?search=alpha&status=todo", headers=auth_headers)
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "alpha review"


def test_sort_by_created_at(client, auth_headers):
    a = _create(client, auth_headers, "first")
    b = _create(client, auth_headers, "second")
    c = _create(client, auth_headers, "third")

    r_desc = client.get("/tasks?sort=desc", headers=auth_headers)
    ids_desc = [t["id"] for t in r_desc.json()["items"]]
    assert ids_desc == [c["id"], b["id"], a["id"]]

    r_asc = client.get("/tasks?sort=asc", headers=auth_headers)
    ids_asc = [t["id"] for t in r_asc.json()["items"]]
    assert ids_asc == [a["id"], b["id"], c["id"]]


def test_invalid_pagination_params_rejected(client, auth_headers):
    assert client.get("/tasks?page=0", headers=auth_headers).status_code == 422
    assert client.get("/tasks?per_page=0", headers=auth_headers).status_code == 422
    assert client.get("/tasks?per_page=101", headers=auth_headers).status_code == 422


def test_list_requires_auth(client):
    r = client.get("/tasks")
    assert r.status_code == 401


def test_list_isolated_per_user(client):
    client.post("/auth/register", json={"email": "a@x.com", "password": "password1"})
    a_token = client.post("/auth/login", json={"email": "a@x.com", "password": "password1"}).json()["access_token"]
    client.post("/auth/register", json={"email": "b@x.com", "password": "password1"})
    b_token = client.post("/auth/login", json={"email": "b@x.com", "password": "password1"}).json()["access_token"]

    a_headers = {"Authorization": f"Bearer {a_token}"}
    b_headers = {"Authorization": f"Bearer {b_token}"}

    _create(client, a_headers, "a-only")
    _create(client, b_headers, "b-only-1")
    _create(client, b_headers, "b-only-2")

    a_body = client.get("/tasks", headers=a_headers).json()
    assert a_body["total"] == 1
    assert a_body["items"][0]["title"] == "a-only"

    b_body = client.get("/tasks", headers=b_headers).json()
    assert b_body["total"] == 2
