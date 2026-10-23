# Where the Dortmund rules come from

Checked on 16 October 2026. The rules live in `src/data_rules/rules/dortmund.json`.

| Bin in the database | What the rule says | Source |
|---|---|---|
| Brown bin (Biotonne), `compostable` | Food leftovers (cooked meat and fish too), fruit and vegetable scraps, coffee grounds and filters, tea bags, eggshells, dairy that is not liquid, lawn clippings, leaves, flowers, small branches, untreated sawdust. Not allowed: plastic of any kind, also bags sold as "compostable", metal, hygiene items, textiles, paper and cardboard, glass, treated wood, ash, cat litter, animal waste. | EDG "Bio 1x1" brochure, edition 08/2025, edg.de |
| Yellow bin (Wertstofftonne), `recyclable` | Yoghurt pots, plastic bottles, tubes, household foil, tin cans, drink cartons, metal bowls, watering cans, plastic toys. Not allowed: electrical devices, CDs/DVDs, paper and cardboard, tea bags, garden waste, plasters, animal litter, wallpaper scraps, banana peel. | DOWERT (Dortmunder Wertstoff GmbH), dowert.de |
| Blue paper bin and paper depot containers, `recyclable` | Paper, cardboard and card packaging go in the paper bin, the depot containers or the recycling yards. Polystyrene and foils do not belong in the paper depot containers. | EDG press releases 2020 and 2023, edg.de |
| Glass depot containers, `recyclable` | Bottles and jars, sorted by white, green and brown. Other colours go with green glass. Only container glass, no ceramics or heat-resistant glassware. | Umweltbundesamt (national rule). I found no Dortmund-specific EDG page for glass. |
| Grey bin (graue Tonne), `landfill` | Crockery, wallpaper scraps, renovation leftovers go in the grey bin. | EDG press release 2023, edg.de |

## Things that are my reading, not a quote

- Diapers, hygiene items, plasters and cat litter are listed under `landfill` because the EDG and DOWERT pages
  say they do NOT belong in the brown or yellow bin. Nothing I found says "grey bin" next to them word for word.
- The `recyclable` rule names three destinations (yellow, blue, glass) because the system only gives
  three categories. The user sees which one applies from the reason text.

## Before you hand in

Open edg.de, search "Abfall-ABC" and test five or six real items (for example: pizza box, yoghurt pot,
coffee capsule, light bulb). If the site disagrees with a sentence in the JSON file, change the JSON only.
