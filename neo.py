from neo4j import GraphDatabase

# Correct format for the driver initialization
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

cypher_query = '''
MATCH (n:Greeting) RETURN n.name as name, n.msg_reply as reply;
'''
Entity_corpus = []
with driver.session() as session:
    results = session.run(cypher_query)
    for record in results:
        Entity_corpus.append(record['name'])
print(Entity_corpus)
