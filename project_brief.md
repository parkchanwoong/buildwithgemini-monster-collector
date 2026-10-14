# My agent: monster-collector
One-liner: A conversational agent that helps players collect, battle, and evolve monsters with a catalog of unique creatures.

Tool coverage:
- Memory: Remembers player's caught monsters (collection), active party, trainer level, in-game currency, and exploration history across sessions.
- Tools: Catch wild monsters (`catch_monster`), search local wild areas (`explore_area`), manage party roster, purchase items.
- Catalog/UI: Monster encyclopedia and active party roster rendered as rich A2UI cards (stats, type, abilities) and battle log tables.
- Image gen: Generates unique visual illustrations for newly caught or evolved creatures and battle scenes.
- Sandbox: Computes battle damage calculations with type effectiveness multipliers, critical strike odds, and turn simulation logic.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): code sandbox for battle damage calculations, Cloud Trace
