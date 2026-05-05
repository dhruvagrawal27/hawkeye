// Neo4j init — creates constraints and indexes
// Run via: docker exec neo4j cypher-shell -u neo4j -p <password> < init.cypher

CREATE CONSTRAINT employee_id IF NOT EXISTS
  FOR (e:Employee) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT system_id IF NOT EXISTS
  FOR (s:SystemResource) REQUIRE s.id IS UNIQUE;

CREATE INDEX employee_risk IF NOT EXISTS
  FOR (e:Employee) ON (e.risk_score);
