road-trip
=======

#### Description

Write a Python program that will solve the problem described

#### Puzzle

There are N cities in Peter's state (numbered starting from 1, which is Peter's city), and M bidirectional roads 
directly connect them. (A pair of cities may even be directly connected by more than one road.) Because of changes 
in traffic patterns, it may take different amounts of time to use a road at different times of day, depending on 
when the journey starts. (However, the direction traveled on the road does not matter -- traffic is always equally 
bad in both directions!) All trips on a road start (and end) exactly on the hour, and a trip on one road can be 
started instantaneously after finishing a trip on another road.

Peter loves to travel and is deciding where to go for his summer holiday trip. He wonders how quickly he can get 
from his city to various other destination cities, depending on what time he leaves his city. (His route to his 
destination may include other intermediate cities on the way.) Can you answer all of his questions?

In the following, 

`<= means 'less than or equal to'`

`>= means 'greater than or equal to'`

##### Input

The first line of the input gives the number of test cases, T. 

T test cases follow.

The first line of each test case contains three integers: the number N of cities, the number M of roads, and the
 number K of Peter's questions.

2M lines -- M pairs of two lines -- follow. In each pair, the first line contains two different integers x and y 
that describe one bidirectional road between the x-th city and the y-th city. The second line 
contains 24 integers Cost[t] (0 <= t <= 23) that indicate the time cost, in hours, to use the road when 
departing at t o'clock on that road. It is guaranteed that Cost[t] <= to Cost[t+1]+1 (0 <= t <= 22) 
and Cost[23] <= Cost[0]+1.

Then, an additional K lines follow. Each contains two integers D and S that comprise a question: what is the fewest
 number of hours it will take to get from city 1 to city D, if Peter departs city 1 at S o'clock?

##### Output

For each test case, output one line containing "Case #x: ", where x is the case number (starting from 1),
 followed by K distinct space-separated integers that are the answers to the questions, in order. 
 If Peter cannot reach the destination city for a question, no matter which roads he takes, 
 then output -1 for that question.

##### Limits

```
x >= 1, y <= N.
1 <= all Cost values <= 50.
1 <= D <= N.
0 <= S <= 23.
```

Take careful note of the Limits section. This section will describe two different sets of limits: limits for the 
Small input and the Large input. 

##### Small dataset

```
1 <= T <= 100.
2 <= N <= 20.
1 <= M <= 100.
1 <= K <= 100.
```

##### Large dataset

```
1 = T = 5.
2 = N = 500.
1 = M = 2000.
1 = K = 5000.
```

##### SAMPLE INPUT

```
3
3 3 2
1 2
1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
1 3
3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 
2 3
1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
2 1
3 3
3 1 2
1 2
1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
2 2
3 4
3 3 3
1 2
7 23 23 25 26 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8
1 3
10 11 15 26 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11
2 3
7 29 28 27 26 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8
2 14
3 3
3 21
```

##### SAMPLE OUTPUT

```
Case #1: 1 2
Case #2: 1 -1
Case #3: 17 26 13
```

##### EVALUATION
The Python program will be run on a standard Ubuntu machine and Python version 2.7. 
It will be evaluated on code quality and execution time. 

