import requests

def test_api_root():
    try:
        res = requests.get("http://localhost:8000/")
        assert res.status_code == 200
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == "__main__":
    test_api_root()
