# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A solver for a time-dependent shortest-path puzzle (full statement in
`README.md`): cities joined by bidirectional roads, each road carrying **24
hourly costs** rather than one weight, and questions of the form "leaving city 1
at hour `S`, how few hours to reach city `D`?".

The whole program is `road_trip.py`. `read_cases()`/`read_case()` parse a
whitespace token stream into `TestCase` objects, `travel_times()` is Dijkstra on
arrival times, `travel_times_by_relaxation()` is an independent Bellman-Ford,
`solve_case()` answers a case's questions from at most 24 cached trees,
`fastest_route()` recovers an itinerary, `fifo_violations()` audits the input,
and `main()` wires up argparse. There is no package structure, no test suite and
no build step.

`tools/make_banner.py` imports the solver, solves case 29 of
`data/small-input.in` and draws `docs/banner-{dark,light}.svg` from the real
answers. It is **local-only and gitignored** — the generated banners are
committed, the generator is not — so it may be missing from a fresh clone. Do not
add it back to git.

## Running

```
python road_trip.py data/sample.in                    # the statement's worked example
python road_trip.py data/small-input.in --check       # both solvers, cross-checked
python road_trip.py data/large-input.in -v            # ~0.12 s
python road_trip.py data/sample.in --itinerary        # the roads taken, not just the total
python tools/make_banner.py                           # regenerate both banners (local-only)
```

Python 3.10+, no third-party dependencies. The system `python3` on this machine
is 3.9 and fails at import on `dataclass(slots=True)`; use
`~/miniconda3/envs/py_313/bin/python` (or `py_310`) to actually run it.

## Conventions worth preserving

- The puzzle's answers go to **stdout**, one `Case #x: ...` line each; timings,
  warnings and itineraries go to **stderr**, so the graded output stays
  diffable against `data/sample.out`.
- Exit codes carry the verdict: `0` answered, `1` a `--check` run caught the two
  methods disagreeing, `2` bad arguments or malformed input.
- **The label Dijkstra settles is hours elapsed, and the road's cost is read at
  `(departure_hour + elapsed) % 24`.** This is the whole algorithm. Do not
  reintroduce a "distance" that is a sum of fixed weights, and do not compute the
  clock from anything but the arrival time at the city being expanded.
- That is only correct because of the statement's `Cost[t] <= Cost[t+1] + 1`
  guarantee (FIFO). It is what makes waiting pointless and restores optimal
  substructure. `fifo_violations()` exists to check it; if an input ever breaks
  it, neither solver is right and the time-expanded construction in `README.md`
  is the fallback.
- **Answers depend only on the departure hour**, of which there are 24 however
  many questions are asked. `solve_case` caches one tree per hour. Do not go back
  to a search per question — that is what made the 2018 version quadratic.
- Roads are bidirectional and **both endpoints share one cost table object**.
  Storing the table under a single ordered key is precisely the 2018 bug that
  made half the network invisible; parallel roads between the same pair are legal
  and the adjacency lists must keep all of them.
- `cities` is read from the input rather than inferred from the roads: a city may
  have no roads at all, and must still answer `-1` rather than vanish.
- Parsing goes through `tokenize()`, which ignores line structure. Do not switch
  back to `readline().split()` — line-oriented parsing was slower and would break
  on a wrapped cost row.
- The banner must stay derived from real solver output. `LAYOUT_SEED` and
  `LAYOUT_STEPS` are fixed on purpose: re-rendering must produce byte-identical
  SVGs, on 3.10 and 3.13 alike.
- The mathematics, the alternative approaches and the literature live in
  `README.md` — if the algorithm changes, that is what has to stay true.

## Checking correctness

`travel_times()` and `travel_times_by_relaxation()` are independent
implementations and must agree; that is the cheapest regression test there is,
and `--check` is how it is run. Above it sits the sample from the original
statement, which is the only externally authoritative ground truth in the repo:

```
python road_trip.py data/sample.in | diff - data/sample.out
python road_trip.py data/small-input.in --check >/dev/null   # 100 cases
python road_trip.py data/large-input.in --check >/dev/null   # 5 cases
```

Known answers: `data/sample.in` → `1 2` / `1 -1` / `17 26 13`. The two datasets
hold 4 592 and 22 598 questions; 145 of the small set's answers are `-1` and none
of the large set's are. A stronger check, worth re-running after any change to
the search, is that an itinerary from `fastest_route()` is a real walk whose leg
costs match the cost tables at the hours the legs depart, and whose hours sum to
what `travel_times()` reported — this holds for all 27 045 answerable questions
in `data/`.

## Branches

Work happens on `refactor/2026-revisit`; `master` is the default/PR target.
