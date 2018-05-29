from collections import namedtuple, defaultdict
import sys


class Graph:
    # Good old python object to represent weighted graphs
    # Distance field can accept any object, we put a timetable here
    def __init__(self):
        self.nodes = set()
        self.edges = defaultdict(list)
        self.distances = {}

    def add_node(self, value):
        self.nodes.add(value)

    def add_edge(self, from_node, to_node, distance):
        self.edges[from_node].append(to_node)
        self.edges[to_node].append(from_node)
        self.distances[(from_node, to_node)] = distance


def load_test_case(f):
    test_case_configuration = f.readline().split()
    test_case = Puzzle(*[int(num) for num in test_case_configuration])

    graph = Graph()
    questions = list()
    # Each element contains two integers D and S that comprise a question:
    # what is the fewest number of hours it will take to get from city 1 to city D,
    # if Peter departs city 1 at S o'clock?

    # print test_case

    for x in range(1, test_case.number_of_roads + 1):
        roads = f.readline().split()
        # print 'adding roads' + str(roads)
        graph.add_node(roads[0])  # citites (nodes) held as strings
        graph.add_node(roads[1])
        timetable = f.readline().split()
        # print 'adding timetable' + str(timetable)
        graph.add_edge(roads[0], roads[1], [int(num) for num in timetable])
    for q in range(1, test_case.number_of_questions + 1):
        new_questions = f.readline().split()
        # print 'adding questions' + str(new_questions)
        questions.append(new_questions)

    # pdb.set_trace()
    return graph, questions


def normalize_clock(initial, added):
    # Never leave the house without a watch
    # normalizes 24+n hours to military hours (0-24)
    if added == 0:
        # This is zero point
        return int(initial)
    elif added + initial <= 23:
        # 1 day didn't pass, just add elements
        # thanks to that we know at which hour we check the timetable
        # and which train to hop in soon
        return int(added + initial)
    # Journey takes more than 1 day, get the remainder of 24 day/night cycle
    clock_pointer = ((initial + added) // 23)
    return initial + added - clock_pointer


def sp_search(graph, initial, i_point):
    visited = {initial: 0}
    path = {}

    nodes = set(graph.nodes)
    # Ensures copy. There may be many questions to just one dataset,
    # therefore we don't want to modify graph object neither it's arguments in the fly

    while nodes:
        min_node = None
        for node in nodes:
            if node in visited:
                if min_node is None:
                    min_node = node
                elif visited[node] < visited[min_node]:
                    min_node = node
        if min_node is None:
            break

        nodes.remove(min_node)
        current_weight = visited[min_node]

        for edge in graph.edges[min_node]:
            try:
                weight = current_weight + graph.distances[(min_node, edge)][normalize_clock(i_point, current_weight)]
            except (KeyError, IndexError) as exc:
                # We shouldn't worry about try/catch. They are cpu efficient
                # https://docs.python.org/2/faq/design.html#how-fast-are-exceptions
                # print "No edge between nodes"
                continue
            if edge not in visited or weight < visited[edge]:
                visited[edge] = weight
                path[edge] = min_node

    return visited, path


def method_dijkstra(graph, start, end, when_peter_leaves):
    # print start, end, when_peter_leaves

    visited, paths = sp_search(graph, start, when_peter_leaves)

    try:
        end_point = paths[end]
    except KeyError as kerr:
        # print "Whoops, no path goes to this city. Happens."
        return -1

    return visited[end]


def calculate(graph, questions):
    solutions = list()
    for question in questions:
        solution = method_dijkstra(graph, start='1',
                                   end=question[0],
                                   when_peter_leaves=int(question[1]))
        # print solution
        solutions.append(solution)
    return solutions


def load_file(filename):
    with open(filename) as f:
        test_cases = int(f.readline())
        for i in range(1, test_cases + 1):
            graph, questions = load_test_case(f)
            solutions = calculate(graph, questions)
            print('Case #%i: %s' % (i, ' '.join([str(solution) for solution in solutions])))
    return test_cases


if __name__ == '__main__':
    # print 'Load files...'

    Puzzle = namedtuple('Puzzle', ['number_of_cities', 'number_of_roads', 'number_of_questions'])

    try:
        assert len(sys.argv) == 2
    except AssertionError:
        print('Please provide input filename as solution.py argument')
        sys.exit(-1)

    # start = time.time()
    test_size = load_file(sys.argv[1])
    # print "Validation case, time: %d samples: %s" % ((time.time() - start), test_size)
    # start = time.time()
    # test_size = load_file('Small input.in')
    # print "Small case, time: %d samples: %s" % ((time.time() - start), test_size)
    
    # print 'Done'
