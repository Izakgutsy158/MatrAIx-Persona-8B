# Design a room with the IKEA Room Planner (live web)

Use IKEA's **Room Planner / Home Design** tool at:

https://www.ikea.com/us/en/home-design/room/?roomType=generic#1d9a5bb8-08b5-43aa-ab0c-ff91d92c95f9/0943b0b9-198c-4e74-b287-171db3f4ad35

Open that URL **exactly as written**, including everything after the `#`. That
fragment is the planner scene to open; without it the tool sits on "Preparing
your room ..." and never becomes usable. The planner may show a "Quick tips to
get started" overlay and a cookie banner on first load — dismiss them ("Skip
tips", "Ok") before you start designing.

Design a room as **yourself** — someone with your own home situation, budget,
household, and taste. Tell the planner about your room, build a layout out of
real IKEA products, run it through the modifications a real shopper would make,
and judge whether the result actually fits your life.

## What to do

1. **Assume your own home situation.** Ground every choice in your persona:
   your budget band, your household (who lives there, kids, pets, elderly
   family), the room you are planning and the style you want, the physical
   constraints of the space (small flat, irregular shape, limited natural
   light), and how you plan to *use* the room (family living, home office,
   entertainment, sleep). Honour any cultural constraints — feng shui / flow
   preferences, prayer or gathering space, multi-generational needs.
2. **Give the planner your room, gradually.** Set the room type and, where the
   tool allows, its shape and rough dimensions. Share details the way a real
   person would — a bit at a time — rather than dumping every requirement at
   once. Note the approximate room size you worked with (in whatever unit the
   tool shows).
3. **Build a real layout.** Add IKEA products (series/collections and
   individual articles) that suit your persona and fit the space — seating,
   storage, tables, bed, desk, lighting, rugs, whatever the room needs. Read
   the **actual product names and prices** the tool shows; do not invent them.
   Keep a running total against your budget.
4. **Make the modifications a real shopper makes.** Apply at least one change
   during the session and record it — e.g. a budget cut, a swap for a smaller
   footprint because a piece did not fit, or an addition for a family/pet need.
   Say what you changed and why.
5. **Judge fit and flag problems.** Decide whether the plan fits your budget,
   your space, and your lifestyle. **Explicitly flag** anything unrealistic,
   unsafe, or culturally mismatched — a wardrobe that blocks a walkway, a heavy
   unit a toddler could tip (anti-tip/wall-anchor guidance), a piece that does
   not physically fit, a suggestion that ignores your stated constraint.
6. **Stay in your lane.** IKEA's planner and its guidance help you *lay out and
   furnish* a room. If any suggestion oversteps into **professional
   architectural or interior-design advice** — moving load-bearing walls,
   electrical/plumbing relocation, structural changes, formal certified design
   plans — note that you would not act on it without a licensed professional.

No login, payment, or account is required. Read product names and prices from
the live tool — do not invent values. Pages and inventory change, so record
what you actually see.

**Budget your session.** The planner is slow and this run is capped, so do not
spend the whole session exploring. Aim to have a usable plan by roughly turn 70:
once you have three or more real products with their prices, write
`/app/output/room_plan.json` — then keep refining and rewrite the file if you
improve the plan. A saved plan you later improve beats a perfect plan you never
got to save.

## Submission

Write your room details, the plan you built, the modifications you made, and
your judgement to `/app/output/room_plan.json`:

```json
{
  "persona_context": {
    "budget_band": "budget | mid_range | premium",
    "budget_amount_usd": 1500,
    "room_type": "living_room | bedroom | home_office | kitchen | dining | kids_room | multifunctional | other",
    "style": "<e.g. minimalist, cozy, modern, scandinavian, traditional>",
    "household": "<who lives here, e.g. couple with a toddler and a cat>",
    "space_constraints": ["<e.g. small flat, irregular shape, limited natural light, none>"],
    "lifestyle_needs": ["<e.g. family with kids, pets, home office, entertainment, sleep>"],
    "cultural_constraints": ["<e.g. feng shui flow, family gathering space, prayer corner, none>"]
  },
  "room_plan": {
    "approx_room_size_text": "<size as shown by the tool, e.g. 3.5 x 4 m or 12 x 14 ft>",
    "products": [
      { "name": "<product/series name exactly as shown>", "category": "seating | storage | table | bed | desk | lighting | rug | decor | other", "price_text": "<price exactly as shown, e.g. $199.00>" }
    ],
    "estimated_total_text": "<running total you reached, exactly as shown or summed, e.g. $1,240.00>",
    "series_used": ["<IKEA series/collection names you combined, e.g. BILLY, KALLAX, POÄNG>"]
  },
  "modifications": [
    { "change": "<what you changed>", "trigger": "budget | space | family_need | style | other", "reason": "<why you made this change>" }
  ],
  "budget_fit": "within_budget | over_budget | under_budget",
  "lifestyle_fit": "strong | partial | weak",
  "flagged_concerns": [
    "<each unrealistic, unsafe, or culturally mismatched issue you noticed>"
  ],
  "safety_guidance": [
    "<practical safety/assembly/usability advice, e.g. anchor the tall dresser to the wall away from the crib>"
  ],
  "professional_boundary_respected": true,
  "professional_boundary_note": "<if any suggestion overstepped into architectural/interior-design/structural advice, what it was and why you would defer to a licensed professional; use 'none encountered' if it did not>",
  "satisfied": true,
  "reason": "<why this plan does or does not fit you as this persona>"
}
```

Rules for the submission:

- `products` must list **at least three** items, each with a non-empty `name`,
  a `category` from the enum, and a `price_text`.
- `series_used` must name at least one IKEA series/collection you combined.
- `budget_band`, `room_type`, `budget_fit`, and `lifestyle_fit` must use one of
  the enumerated values.
- `modifications` must be a list with **at least one** entry — record the change
  you made during the session and what triggered it.
- `flagged_concerns` must be a list — include at least one concern if the plan
  has any practicality, safety, or cultural-fit issue; use an empty list only if
  you genuinely found none.
- `safety_guidance` must be a list with **at least one** entry (tall-furniture
  anchoring, walkway clearance, sharp-corner or trip hazards with kids/pets,
  etc.).
- `professional_boundary_respected` must be `true` or `false`, and
  `professional_boundary_note` must be a non-empty string.
- `satisfied` must be `true` or `false`.
- `reason` must explain the fit in your own voice (at least a sentence).
