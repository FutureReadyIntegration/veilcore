import veil.orchestrator as orch

print(len(orch.list()), "organs")
for organ in orch.list():
    print("-", organ)
