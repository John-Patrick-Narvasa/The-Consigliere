```
[START] ──► [retrieve_context]
	                 │
                     ▼
            [classify_intent_node] (Saves state["intent"])
                     │
                     ▼ (Conditional Edge reads state["intent"])
       ┌─────────────────────┐
       │   route_by_intent   │ ◄── Conditional routing edge (LLM Decision)
       └─┬────────┬────────┬─┘
         │        │        │
 (advice)│        │(proc)  │(system)
         ▼        ▼        ▼
   ┌─────────┐┌─────────┐┌─────────┐
   │ advice  ││procedure││ system  │ ◄── Formats custom layouts & strict citations
   │  node   ││  node   ││  node   │
   └────┬────┘└────┬────┘└────┬────┘
        │          │          │
        └──────────┼──────────┘
                   ▼
                 [END]
```
