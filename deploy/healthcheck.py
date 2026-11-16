from urllib.request import Request, urlopen

with urlopen(Request("http://127.0.0.1:8001/health/ready", headers={"Host": "clockin.arnatech.id"}), timeout=5) as response:
    assert response.status == 200
