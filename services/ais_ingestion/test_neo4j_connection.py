"""Diagnostic script - tests Neo4j connection step by step."""
import sys
import os

# Load kg .env for credentials
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kg"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "kg", ".env"))

print("1. Loading credentials...")
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "")
print(f"   URI: {uri}")
print(f"   User: {user}")
print(f"   Password: {'(set)' if password else '(empty - PROBLEM!)'}")

if not password:
    print("\n   ERROR: NEO4J_PASSWORD is empty. Set it in services/kg/.env")
    sys.exit(1)

print("\n2. Connecting to Neo4j...")
try:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("   OK - Connected successfully!")
except Exception as e:
    print(f"   FAILED: {type(e).__name__}: {e}")
    sys.exit(1)

print("\n3. Checking databases...")
try:
    with driver.session() as session:
        result = session.run("SHOW DATABASES")
        dbs = [r["name"] for r in result]
        print(f"   Databases: {dbs}")
        if not dbs:
            print("   WARNING: No databases found. Create one in Neo4j Desktop (Create database)")
except Exception as e:
    print(f"   FAILED: {type(e).__name__}: {e}")
    driver.close()
    sys.exit(1)

print("\n4. Counting vessels in default DB...")
try:
    with driver.session(database="neo4j") as session:
        result = session.run("MATCH (v:Vessel) RETURN count(v) as n")
        n = result.single()["n"]
        print(f"   Vessels: {n}")
except Exception as e:
    print(f"   (expected if schema not set up): {type(e).__name__}: {e}")

driver.close()
print("\nDone.")
