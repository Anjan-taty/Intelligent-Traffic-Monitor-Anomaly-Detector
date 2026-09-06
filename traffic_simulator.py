import time
import random
import argparse
import threading
from typing import Dict, Any, List
import httpx

TARGET_URL = "http://localhost:8000"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

SCRAPER_AGENTS = [
    "python-requests/2.31.0",
    "Scrapy/2.11.0 (+https://scrapy.org)",
    "Go-http-client/1.1",
    "curl/8.4.0"
]

def simulate_human_session(base_url: str = TARGET_URL, num_requests: int = 15) -> Dict[str, Any]:
    """
    Simulates a genuine human user browsing the website.
    Characteristics: Varied think-time delays, low error rate, cohesive browsing path.
    """
    client = httpx.Client(base_url=base_url, timeout=5.0)
    fake_ip = f"192.168.1.{random.randint(10, 80)}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "X-Forwarded-For": fake_ip
    }

    endpoints = [
        ("GET", "/api/products"),
        ("GET", f"/api/products/{random.randint(1, 5)}"),
        ("GET", "/api/search?q=laptop"),
        ("GET", f"/api/products/{random.randint(6, 10)}"),
        ("GET", "/api/cart"),
        ("POST", "/api/cart")
    ]

    success, blocked, errors = 0, 0, 0
    start_time = time.time()

    for _ in range(num_requests):
        method, path = random.choice(endpoints)
        try:
            if method == "GET":
                resp = client.get(path, headers=headers)
            else:
                resp = client.post(path, json={"item_id": random.randint(1, 20), "qty": 1}, headers=headers)

            if resp.status_code == 200:
                success += 1
            elif resp.status_code == 429:
                blocked += 1
            else:
                errors += 1
        except Exception:
            errors += 1

        # Human think time jitter (0.4s to 1.5s)
        time.sleep(random.uniform(0.4, 1.2))

    client.close()
    duration = time.time() - start_time
    return {
        "scenario": "human",
        "ip": fake_ip,
        "total": num_requests,
        "success": success,
        "blocked": blocked,
        "errors": errors,
        "duration": round(duration, 2)
    }

def simulate_scraper_bot(base_url: str = TARGET_URL, num_requests: int = 40) -> Dict[str, Any]:
    """
    Simulates an aggressive web scraper crawling through product IDs.
    Characteristics: High frequency, low timing jitter, high endpoint entropy.
    """
    client = httpx.Client(base_url=base_url, timeout=5.0)
    fake_ip = f"10.0.5.{random.randint(100, 200)}"
    headers = {
        "User-Agent": random.choice(SCRAPER_AGENTS),
        "X-Forwarded-For": fake_ip
    }

    success, blocked, errors = 0, 0, 0
    start_time = time.time()

    for item_id in range(1, num_requests + 1):
        path = f"/api/products/{item_id}"
        try:
            resp = client.get(path, headers=headers)
            if resp.status_code == 200:
                success += 1
            elif resp.status_code == 429:
                blocked += 1
            else:
                errors += 1
        except Exception:
            errors += 1

        # Very low robotic cadence (0.02s fixed delay)
        time.sleep(0.02)

    client.close()
    duration = time.time() - start_time
    return {
        "scenario": "scraper",
        "ip": fake_ip,
        "total": num_requests,
        "success": success,
        "blocked": blocked,
        "errors": errors,
        "duration": round(duration, 2)
    }

def simulate_ddos_flood(base_url: str = TARGET_URL, num_requests: int = 80, concurrency: int = 8) -> Dict[str, Any]:
    """
    Simulates a volumetric Layer-7 DDoS flood attack using multiple concurrent worker threads.
    Characteristics: Extreme RPS, rapid rate-limit triggers.
    """
    fake_ip = f"45.33.32.{random.randint(10, 99)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; EvilBot/2.0)",
        "X-Forwarded-For": fake_ip
    }

    results = {"success": 0, "blocked": 0, "errors": 0}
    lock = threading.Lock()
    start_time = time.time()

    def worker(count: int):
        client = httpx.Client(base_url=base_url, timeout=3.0)
        for _ in range(count):
            try:
                resp = client.get("/api/products", headers=headers)
                with lock:
                    if resp.status_code == 200:
                        results["success"] += 1
                    elif resp.status_code == 429:
                        results["blocked"] += 1
                    else:
                        results["errors"] += 1
            except Exception:
                with lock:
                    results["errors"] += 1
        client.close()

    per_thread = num_requests // concurrency
    threads = []
    for _ in range(concurrency):
        t = threading.Thread(target=worker, args=(per_thread,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    duration = time.time() - start_time
    return {
        "scenario": "ddos",
        "ip": fake_ip,
        "total": num_requests,
        "success": results["success"],
        "blocked": results["blocked"],
        "errors": results["errors"],
        "duration": round(duration, 2)
    }

def simulate_credential_bruteforce(base_url: str = TARGET_URL, num_requests: int = 25) -> Dict[str, Any]:
    """
    Simulates a credential stuffing / brute force login attack.
    Characteristics: Rapid consecutive POSTs to /api/login yielding 401 Unauthorized errors.
    """
    client = httpx.Client(base_url=base_url, timeout=5.0)
    fake_ip = f"198.51.100.{random.randint(2, 90)}"
    headers = {
        "User-Agent": "Hydra/9.5 (Network Logon Brute Force)",
        "X-Forwarded-For": fake_ip
    }

    success, blocked, errors = 0, 0, 0
    start_time = time.time()

    passwords = ["admin123", "password", "123456", "toor", "root", "qwerty", "welcome"]
    for i in range(num_requests):
        try:
            resp = client.post(
                "/api/login",
                json={"username": "admin", "password": random.choice(passwords) + str(i)},
                headers=headers
            )
            if resp.status_code == 200:
                success += 1
            elif resp.status_code == 429:
                blocked += 1
            elif resp.status_code in [401, 403]:
                errors += 1
            else:
                errors += 1
        except Exception:
            errors += 1

        time.sleep(0.04)

    client.close()
    duration = time.time() - start_time
    return {
        "scenario": "bruteforce",
        "ip": fake_ip,
        "total": num_requests,
        "success": success,
        "blocked": blocked,
        "errors": errors,
        "duration": round(duration, 2)
    }

def run_simulation(scenario: str, count: int = 30, concurrency: int = 5, base_url: str = TARGET_URL) -> Dict[str, Any]:
    """Unified dispatch function for both API and CLI invocation."""
    scenario = scenario.lower()
    if scenario == "human":
        return simulate_human_session(base_url=base_url, num_requests=count)
    elif scenario == "scraper":
        return simulate_scraper_bot(base_url=base_url, num_requests=count)
    elif scenario == "ddos":
        return simulate_ddos_flood(base_url=base_url, num_requests=count, concurrency=concurrency)
    elif scenario == "bruteforce":
        return simulate_credential_bruteforce(base_url=base_url, num_requests=count)
    else:
        raise ValueError(f"Unknown scenario: {scenario}. Choose from: human, scraper, ddos, bruteforce.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cyber Defense Traffic Attack Simulator")
    parser.add_argument("--scenario", type=str, default="scraper", choices=["human", "scraper", "ddos", "bruteforce"], help="Traffic pattern scenario")
    parser.add_argument("--count", type=int, default=30, help="Number of requests to generate")
    parser.add_argument("--concurrency", type=int, default=5, help="Thread concurrency for DDoS")
    parser.add_argument("--url", type=str, default=TARGET_URL, help="Target Gateway URL")
    args = parser.parse_args()

    print(f"[*] Dispatching '{args.scenario}' simulation to {args.url} (Count: {args.count})...")
    res = run_simulation(args.scenario, count=args.count, concurrency=args.concurrency, base_url=args.url)
    print("\n[+] Simulation Complete:")
    for k, v in res.items():
        print(f"    {k:12}: {v}")
