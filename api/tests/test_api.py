import requests

def test_check_users(base_url_api):
    response = requests.get(f"{base_url_api}/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Leanne Graham"
    # assert data["email"] == ""
    assert "email" in data
    print(f"user is: {data['name']}, email: {data['email']}")

def test_create_object(base_url_api):
    payload = {
        "title": "My QA Post",
        "body": "Learning API testing is fun!",
        "userId": 1
    }
    response = requests.post(f"{base_url_api}/posts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My QA Post"
    assert data["body"] == "Learning API testing is fun!"
    assert data["userId"] == 1
    print(f"Created object ID: {data['id']}")

