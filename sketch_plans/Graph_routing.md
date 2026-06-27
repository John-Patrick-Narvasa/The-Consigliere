

```
			   [START]
                  │
                  ▼
       ┌─────────────────────┐
       │  retrieve_context   │ ◄── Hits Pinecone using query embedding
       └──────────┬──────────┘
                  │
                  ▼
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
