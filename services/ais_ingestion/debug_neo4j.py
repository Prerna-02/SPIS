"""Quick Neo4j connection debug with timeout."""
import os
import sys

print("Step 1: Loading environment...")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kg"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "kg", ".env"))

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "")

print(f"   URI: {uri}")
print(f"   User: {user}")
print(f"   Password: {password[:3]}*** (length={len(password)})")

print("\nStep 2: Importing neo4j driver...")
from neo4j import GraphDatabase

print("\nStep 3: Creating driver (5 second timeout)...")
try:
    driver = GraphDatabase.driver(
        uri, 
        auth=(user, password),
        connection_timeout=5,  # 5 second timeout
        max_connection_lifetime=10
    )
    print("   Driver created.")
except Exception as e:
    print(f"   FAILED: {e}")
    sys.exit(1)

print("\nStep 4: Verifying connectivity...")
try:
    driver.verify_connectivity()
    print("   SUCCESS! Connected to Neo4j.")
except Exception as e:
    print(f"   FAILED: {type(e).__name__}: {e}")
    driver.close()
    sys.exit(1)

print("\nStep 5: Running test query...")
try:
    with driver.session() as session:
        result = session.run("RETURN 1 as n")
        print(f"   Query result: {result.single()['n']}")
except Exception as e:
    print(f"   FAILED: {e}")

driver.close()
print("\nDone! Neo4j connection works.")
