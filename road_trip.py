#!/usr/bin/env python3
"""Solver for the "road trip" puzzle: shortest paths through a timetable.

The puzzle
----------
Peter lives in city 1 of a country with ``N`` cities joined by ``M``
bidirectional roads. How long a road takes depends on *when you set off along
it*: every road carries 24 numbers, ``Cost[0]`` through ``Cost[23]``, and a
journey begun at ``t`` o'clock arrives ``Cost[t]`` hours later. Trips start and
end on the hour, and one can be started the instant another finishes. Given a
departure hour ``S`` and a destination ``D``, how few hours can the trip from
city 1 take? See ``README.md`` for the statement in full.

How it is answered
------------------
The costs obey ``Cost[t] <= Cost[t+1] + 1`` (wrapping at midnight), which is
the *FIFO* condition: setting off an hour later never gets you there any
earlier. That single guarantee is what makes the puzzle tractable -- waiting
around is never worth it, a prefix of a fastest route is itself a fastest
route, and plain Dijkstra is correct as long as the label being relaxed is the
*arrival time* rather than a sum of fixed weights.

Answers depend on the departure hour and nothing else, so a test case needs at
most 24 shortest-path trees no matter how many questions are asked of it;
:func:`solve_case` computes each one once, on demand, and looks the rest up.
:func:`travel_times_by_relaxation` recomputes the same table by repeated
relaxation instead, and ``--check`` runs the two against each other.

Usage
-----
    python road_trip.py data/sample.in         # solve a file
    python road_trip.py < data/sample.in       # or read standard input
    python road_trip.py data/small-input.in --check
    python road_trip.py data/large-input.in -v

Requires Python 3.10 or newer. It has no third-party dependencies.
"""

import argparse
import heapq
import sys
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from itertools import islice
from time import perf_counter

#: Hours in a day -- the length of every road's cost table, and the modulus
#: that turns "hours since Peter left home" back into a wall-clock hour.
HOURS_IN_DAY = 24

#: Peter always sets off from city 1.
START_CITY = 1

#: What the puzzle wants printed when a destination cannot be reached at all.
UNREACHABLE = -1

#: Stand-in for "no route found yet". Larger than any real answer: a route
#: visits at most 500 cities and no single road costs more than 50 hours.
UNREACHED = sys.maxsize


class MalformedInput(ValueError):
    """The input did not have the shape the puzzle statement describes."""


@dataclass(frozen=True, slots=True)
class Road:
    """One end of one road, as seen from the city at the other end.

    Roads are bidirectional, so each one is stored twice -- once in the
    adjacency list of either endpoint.

    Attributes:
        to_city: Where this road leads.
        cost: 24 durations in hours, indexed by the hour of departure, so
            ``cost[t]`` is what the crossing takes if you leave at ``t``
            o'clock. Traffic is equally bad in both directions, so both copies
            of a road share the same table.
    """

    to_city: int
    cost: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Question:
    """One of Peter's questions: how fast can he get somewhere, leaving when?

    Attributes:
        destination: The city he wants to reach.
        departure_hour: The hour he leaves city 1, from ``0`` to ``23``.
    """

    destination: int
    departure_hour: int


@dataclass(frozen=True, slots=True)
class Leg:
    """One road taken on a fastest route.

    Attributes:
        from_city: Where this leg starts.
        to_city: Where it ends.
        departs_at: The wall-clock hour it sets off at, from ``0`` to ``23``.
            This is the hour whose entry of the road's cost table was used.
        hours: How long the leg takes.
    """

    from_city: int
    to_city: int
    departs_at: int
    hours: int


@dataclass(frozen=True, slots=True)
class TestCase:
    """A road network and the questions asked about it.

    Attributes:
        cities: How many cities exist. Some may have no roads at all, which is
            why this is stored rather than inferred from ``adjacency``.
        adjacency: Roads leaving each city, indexed by city number. Index 0 is
            an unused placeholder so that cities can keep their 1-based names.
        questions: The questions, in the order they must be answered.
    """

    cities: int
    adjacency: tuple[tuple[Road, ...], ...]
    questions: tuple[Question, ...]

    @property
    def road_count(self) -> int:
        """How many roads the network has, counting each one once."""
        return sum(len(roads) for roads in self.adjacency) // 2


# --------------------------------------------------------------------------
# Reading the input
# --------------------------------------------------------------------------


def tokenize(lines: Iterable[str]) -> Iterator[str]:
    """Flatten input into a stream of whitespace-separated words.

    The statement lays the numbers out one group per line, but nothing depends
    on that, and a stream is both faster to read and tolerant of a file whose
    long cost rows have been wrapped.

    Args:
        lines: Any iterable of text, typically an open file.
    """
    for line in lines:
        yield from line.split()


def _take_ints(tokens: Iterator[str], count: int, what: str) -> list[int]:
    """Pull exactly ``count`` integers off the stream, or explain what is wrong.

    Args:
        tokens: The stream to read from.
        count: How many integers are expected.
        what: What they are, for the error message.

    Raises:
        MalformedInput: If the stream runs dry or holds something that is not
            an integer.
    """
    words = list(islice(tokens, count))
    if len(words) != count:
        raise MalformedInput(
            f"expected {count} integer(s) for {what}, but the input ended after {len(words)}"
        )
    try:
        return [int(word) for word in words]
    except ValueError as error:
        raise MalformedInput(f"expected integers for {what}, got {words!r}") from error


def read_case(tokens: Iterator[str]) -> TestCase:
    """Read one test case: its size, its roads, and its questions.

    Args:
        tokens: The stream to read from, positioned at the case's first number.

    Raises:
        MalformedInput: If the case is truncated, or names a city that does not
            exist, or gives a departure hour outside ``0..23``.
    """
    cities, roads, questions = _take_ints(tokens, 3, "the N, M and K of a test case")
    if cities < 1 or roads < 0 or questions < 0:
        raise MalformedInput(f"nonsensical test case size: N={cities} M={roads} K={questions}")

    def check_city(city: int, role: str) -> int:
        if not 1 <= city <= cities:
            raise MalformedInput(f"{role} {city} is outside the 1..{cities} cities of this case")
        return city

    # Build the adjacency lists in mutable form, then freeze them, so that a
    # TestCase cannot be edited from under the solvers.
    adjacency: list[list[Road]] = [[] for _ in range(cities + 1)]
    for _ in range(roads):
        left, right = _take_ints(tokens, 2, "the two endpoints of a road")
        check_city(left, "road endpoint")
        check_city(right, "road endpoint")
        cost = tuple(_take_ints(tokens, HOURS_IN_DAY, f"the cost table of road {left}-{right}"))
        # Both directions share one table: the statement is explicit that
        # traffic is equally bad whichever way you drive.
        adjacency[left].append(Road(right, cost))
        adjacency[right].append(Road(left, cost))

    asked = []
    for _ in range(questions):
        destination, hour = _take_ints(tokens, 2, "the D and S of a question")
        check_city(destination, "question destination")
        if not 0 <= hour < HOURS_IN_DAY:
            raise MalformedInput(f"departure hour {hour} is not an hour of the day (0..23)")
        asked.append(Question(destination, hour))

    return TestCase(cities, tuple(tuple(roads_here) for roads_here in adjacency), tuple(asked))


def read_cases(tokens: Iterator[str]) -> Iterator[TestCase]:
    """Read a whole input file: a count, then that many test cases.

    Yields cases one at a time rather than returning a list, so a large file is
    answered as it is read instead of after it has all been parsed.

    Args:
        tokens: The stream to read from, positioned at the very beginning.

    Raises:
        MalformedInput: If the file is empty or a case is truncated.
    """
    (count,) = _take_ints(tokens, 1, "the number of test cases")
    if count < 0:
        raise MalformedInput(f"the number of test cases must not be negative, got {count}")
    for _ in range(count):
        yield read_case(tokens)


# --------------------------------------------------------------------------
# Solving
# --------------------------------------------------------------------------


def travel_times(case: TestCase, departure_hour: int, start: int = START_CITY) -> list[int]:
    """Fastest journey from ``start`` to every city, leaving at ``departure_hour``.

    Dijkstra's algorithm, with two adjustments for a network whose roads change
    speed through the day. The label kept for a city is the number of hours
    since Peter left home, and the cost of a road is read out of its table at
    the hour he would actually be setting off along it -- ``departure_hour``
    plus the hours elapsed so far, wrapped at midnight.

    That is only sound because the puzzle guarantees ``Cost[t] <= Cost[t+1]+1``
    (see :func:`fifo_violations`): leaving later never means arriving earlier,
    so the first time the queue settles a city it has settled it for good, and
    hanging about in the hope of catching a faster road is never worthwhile.

    Args:
        case: The network to search.
        departure_hour: The hour Peter leaves ``start``, from ``0`` to ``23``.
        start: Where he leaves from.

    Returns:
        A list indexed by city number: hours needed to reach it, or
        :data:`UNREACHED` where no route exists. Index 0 is a placeholder, and
        ``result[start]`` is ``0``.
    """
    best = [UNREACHED] * (case.cities + 1)
    best[start] = 0
    queue: list[tuple[int, int]] = [(0, start)]

    while queue:
        elapsed, city = heapq.heappop(queue)
        if elapsed > best[city]:
            continue  # a faster route to this city was already settled
        clock = (departure_hour + elapsed) % HOURS_IN_DAY
        for road in case.adjacency[city]:
            arrival = elapsed + road.cost[clock]
            if arrival < best[road.to_city]:
                best[road.to_city] = arrival
                heapq.heappush(queue, (arrival, road.to_city))

    return best


def fastest_route(
    case: TestCase, destination: int, departure_hour: int, start: int = START_CITY
) -> tuple[Leg, ...] | None:
    """Recover the roads of a fastest journey, not merely its length.

    The same search as :func:`travel_times`, keeping a note of which road
    settled each city so the itinerary can be walked back afterwards. Where
    several routes tie, the one found first comes back; which that is is
    unspecified but deterministic.

    Args:
        case: The network to search.
        destination: The city to reach.
        departure_hour: The hour Peter leaves ``start``, from ``0`` to ``23``.
        start: Where he leaves from.

    Returns:
        The legs in travelling order, empty if he is already there, or ``None``
        if the destination cannot be reached at all.
    """
    best = [UNREACHED] * (case.cities + 1)
    best[start] = 0
    came_from: dict[int, Leg] = {}
    queue: list[tuple[int, int]] = [(0, start)]

    while queue:
        elapsed, city = heapq.heappop(queue)
        if elapsed > best[city]:
            continue
        if city == destination:
            break  # settled: nothing still queued can improve on it
        clock = (departure_hour + elapsed) % HOURS_IN_DAY
        for road in case.adjacency[city]:
            arrival = elapsed + road.cost[clock]
            if arrival < best[road.to_city]:
                best[road.to_city] = arrival
                came_from[road.to_city] = Leg(city, road.to_city, clock, road.cost[clock])
                heapq.heappush(queue, (arrival, road.to_city))

    if best[destination] == UNREACHED:
        return None

    legs = []
    city = destination
    while city != start:
        leg = came_from[city]
        legs.append(leg)
        city = leg.from_city
    legs.reverse()
    return tuple(legs)


def format_route(legs: Sequence[Leg], departure_hour: int, start: int = START_CITY) -> str:
    """Render an itinerary as one readable line.

    Args:
        legs: The route, as returned by :func:`fastest_route`.
        departure_hour: The hour the journey begins.
        start: Where it begins.
    """
    if not legs:
        return f"already in city {start} at {departure_hour:02d}:00 -- 0 hours"
    hops = f"{start}" + "".join(f" --{leg.hours}h--> {leg.to_city}" for leg in legs)
    total = sum(leg.hours for leg in legs)
    arrival = (departure_hour + total) % HOURS_IN_DAY
    return (
        f"{hops}   (leave {departure_hour:02d}:00, arrive {arrival:02d}:00, "
        f"{total} hour{'s' if total != 1 else ''})"
    )


def travel_times_by_relaxation(
    case: TestCase, departure_hour: int, start: int = START_CITY
) -> list[int]:
    """The same table as :func:`travel_times`, computed a different way.

    Bellman-Ford rather than Dijkstra: sweep every road repeatedly, shortening
    whatever can be shortened, and stop when a whole sweep changes nothing. No
    priority queue and no assumption about the order cities settle in, which is
    exactly what makes it useful -- it is an independent second opinion, and
    ``--check`` holds the two to it. It is also markedly slower, so it is not
    the default.

    Args:
        case: The network to search.
        departure_hour: The hour Peter leaves ``start``, from ``0`` to ``23``.
        start: Where he leaves from.

    Returns:
        The same shape of list as :func:`travel_times`.

    Raises:
        RuntimeError: If the sweeps have not settled after one per city. A
            fastest route never revisits a city, so ``cities`` sweeps is more
            than enough; failing to settle means the FIFO guarantee was broken.
    """
    best = [UNREACHED] * (case.cities + 1)
    best[start] = 0

    for _ in range(case.cities):
        changed = False
        for city in range(1, case.cities + 1):
            elapsed = best[city]
            if elapsed == UNREACHED:
                continue
            clock = (departure_hour + elapsed) % HOURS_IN_DAY
            for road in case.adjacency[city]:
                arrival = elapsed + road.cost[clock]
                if arrival < best[road.to_city]:
                    best[road.to_city] = arrival
                    changed = True
        if not changed:
            return best

    raise RuntimeError(
        f"relaxation had not settled after {case.cities} sweeps; "
        "the cost tables probably violate the Cost[t] <= Cost[t+1]+1 guarantee"
    )


#: The two ways of computing a travel-time table, by the name ``--method`` uses.
METHODS = {
    "dijkstra": travel_times,
    "relaxation": travel_times_by_relaxation,
}


def solve_case(case: TestCase, method: str = "dijkstra") -> list[int]:
    """Answer every question in a test case.

    An answer depends only on which hour Peter sets off, so the shortest-path
    tree for a given hour is computed once and then read by every question that
    shares it. There are 24 hours in a day and there may be thousands of
    questions, which is where the time goes if this is done naively.

    Args:
        case: The network and its questions.
        method: Which entry of :data:`METHODS` to compute the tables with.

    Returns:
        One answer per question, in the order asked: hours needed, or
        :data:`UNREACHABLE` (``-1``) where there is no route.
    """
    compute = METHODS[method]
    by_hour: dict[int, list[int]] = {}
    answers = []
    for question in case.questions:
        table = by_hour.get(question.departure_hour)
        if table is None:
            table = by_hour[question.departure_hour] = compute(case, question.departure_hour)
        hours = table[question.destination]
        answers.append(UNREACHABLE if hours == UNREACHED else hours)
    return answers


def fifo_violations(case: TestCase) -> list[tuple[int, int, int]]:
    """Find cost tables that break the guarantee the solvers rely on.

    The statement promises ``Cost[t] <= Cost[t+1] + 1`` for every hour, midnight
    included, which says that delaying departure by an hour never advances
    arrival by more than that hour. Both solvers assume it. This is not checked
    on the hot path -- ``--check`` calls it -- but an input that broke it would
    make waiting at a city worthwhile, and then neither answer here would be
    right.

    Args:
        case: The network to inspect.

    Returns:
        One ``(from_city, to_city, hour)`` triple per offending entry, where
        ``hour`` is the ``t`` whose cost is too large.
    """
    offenders = []
    for city in range(1, case.cities + 1):
        for road in case.adjacency[city]:
            if road.to_city < city:
                continue  # each road is stored twice; inspect one copy
            for hour in range(HOURS_IN_DAY):
                later = road.cost[(hour + 1) % HOURS_IN_DAY]
                if road.cost[hour] > later + 1:
                    offenders.append((city, road.to_city, hour))
    return offenders


def format_answers(case_number: int, answers: Sequence[int]) -> str:
    """Render one case's answers in the form the puzzle asks for."""
    return f"Case #{case_number}: " + " ".join(str(answer) for answer in answers)


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line. ``argv`` defaults to :data:`sys.argv`."""
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", maxsplit=1)[0],
        epilog="Answers go to stdout, one line per test case; timings and "
        "warnings go to stderr, so the answers stay easy to diff.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="file to read the test cases from (default: standard input)",
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=sorted(METHODS),
        default="dijkstra",
        help="how to compute the travel times: a priority-queue search "
        "(default) or repeated relaxation of every road",
    )
    parser.add_argument(
        "-c",
        "--check",
        action="store_true",
        help="solve each case both ways and confirm they agree, and report any "
        "road whose costs break the Cost[t] <= Cost[t+1]+1 guarantee",
    )
    parser.add_argument(
        "-i",
        "--itinerary",
        action="store_true",
        help="print the actual roads taken for every question on stderr",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="report the size and timing of every case on stderr",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the solver as a command line program and return its exit code."""
    args = parse_args(argv)

    if args.input == "-":
        stream, closing = sys.stdin, False
    else:
        try:
            stream, closing = open(args.input, encoding="utf-8"), True
        except OSError as error:
            print(f"error: cannot read {args.input}: {error.strerror}", file=sys.stderr)
            return 2

    started = perf_counter()
    cases = 0
    disagreements = 0
    try:
        for number, case in enumerate(read_cases(tokenize(stream)), start=1):
            cases = number
            case_started = perf_counter()
            answers = solve_case(case, args.method)

            if args.check:
                other = "relaxation" if args.method == "dijkstra" else "dijkstra"
                if solve_case(case, other) != answers:
                    print(
                        f"error: case {number}: dijkstra and relaxation disagree",
                        file=sys.stderr,
                    )
                    disagreements += 1
                for from_city, to_city, hour in fifo_violations(case):
                    print(
                        f"warning: case {number}: road {from_city}-{to_city} has "
                        f"Cost[{hour}] > Cost[{(hour + 1) % HOURS_IN_DAY}] + 1",
                        file=sys.stderr,
                    )

            print(format_answers(number, answers))
            if args.itinerary:
                for index, question in enumerate(case.questions, start=1):
                    legs = fastest_route(case, question.destination, question.departure_hour)
                    described = (
                        f"no route to city {question.destination}"
                        if legs is None
                        else format_route(legs, question.departure_hour)
                    )
                    print(f"case {number}, question {index}: {described}", file=sys.stderr)
            if args.verbose:
                reachable = sum(1 for answer in answers if answer != UNREACHABLE)
                print(
                    f"case {number}: {case.cities} cities, {case.road_count} roads, "
                    f"{len(case.questions)} questions "
                    f"({reachable} reachable) in {perf_counter() - case_started:.2f}s",
                    file=sys.stderr,
                )
    except MalformedInput as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    finally:
        if closing:
            stream.close()

    if args.verbose or args.check:
        checked = " (cross-checked)" if args.check and not disagreements else ""
        print(
            f"{cases} test case(s) solved by {args.method}{checked} "
            f"in {perf_counter() - started:.2f}s",
            file=sys.stderr,
        )
    return 1 if disagreements else 0


if __name__ == "__main__":
    raise SystemExit(main())
