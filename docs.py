import json
with open('Orion-tecnologics-docs/Security-IT.json') as f:
    data = json.load(f)
print(data['documents'][3]['title'], data['documents'][3]['content'], sep='\n')