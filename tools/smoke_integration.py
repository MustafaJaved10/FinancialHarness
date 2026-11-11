"""Verify the running frontend, queue, data connectors, and sandbox."""
import json
import os
import time
import urllib.request

BASE = os.getenv("APP_URL", "http://127.0.0.1:8080")


def request(path, body=None):
    payload = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as result:
        return result.read()


def job(question):
    ticket = json.loads(request("/api/jobs", {"question": question}))
    assert ticket["status"] == "queued"
    path = "/api/jobs/" + ticket["job_id"]
    for _ in range(180):
        status = json.loads(request(path))
        if status["status"] == "failed":
            raise AssertionError(status)
        if status["status"] == "completed":
            assert status["progress"] == 100 and json.loads(request(path))["result"] == status["result"]
            return status["result"]
        time.sleep(1)
    raise TimeoutError(question)


def main():
    assert json.loads(request("/api/health")) == {"status": "ok"}
    assert b'<div id="root">' in request("/")
    technical = job("Show IBM price and volume")
    assert technical["tool"] == "technical" and len(technical["chart"]["candles"]) >= 21
    assert "saved copy" in technical["sources"][0]
    fundamental = job("Show IBM earnings and valuation")
    assert fundamental["tool"] == "fundamental" and any(
        row[:2] == ["Revenue", 17103000000] for row in fundamental["table"]["rows"]
    )
    assert len(job("Compare IBM and MSFT")["table"]["rows"]) == 2
    assert len(job("Project IBM over 3 years")["table"]["rows"]) == 3
    assert job("What if $1,000 drops 10%?")["table"]["rows"] == [[1000, -10, 900]]
    assert job("Should I buy TSLA?")["tool"] == "none"
    print("PASS: frontend, IBM price and financials, comparison, projection, what-if, refusal, and saved results")


if __name__ == "__main__":
    main()
