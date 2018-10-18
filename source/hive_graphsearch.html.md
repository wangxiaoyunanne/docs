---
title: Graph Search (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# `GraphSearch`

The `GraphSearch` workflow walks the graph searching for nodes that score highly on some indicator of interest.

The use case given by the HIVE government partner was sampling a graph: given some seen nodes, and some model that can score a node, find lots of "interesting" nodes as quickyy as possible.  Their `GraphSearch` algorithm attempts to solve this problem by implementing several different strategies for walking the graph.
 - `uniform`: given a node `u`, randomly move to one of `u`'s neighbors (ignoring scores)
 - `greedy`: given a node `u`, walk to neighbor with maximum score
 - `stochastic_greedy`: given a node `u`, choose neighbor to walk to with probability proportional to score

## Summary of Gunrock Implementation

The scoring model is an arbitrary function of graph structure and/or node metadata.  For example, if we were running `GraphSearch` on the Twitter friends/followers graph, the scoring model might be the output of a text classifier on each users' messages.  Thus, we do not implement the scoring model in our Gunrock implementation -- we read scores from an input file and access them as necessary.

`GraphSearch` is a generalization of a typical random walk algorithm, where there can be more variety in the transition function between nodes.  The `GraphSearch` `uniform` case is exactly a uniform random walk, so we can use the pre-existing Gunrock application.  Given a node, we compute the node to walk to as:
```python
r = random.uniform(0, 1)
neighbors = graph.get_neighbors(node)
next_node = neighbors[floor(r * len(neighbors))]
```

Both the `GraphSearch` `greedy` and `stochastic_greedy` consist of small modifications to this transition function.  For `greedy`, we find the neighbor with maximum score:
```python
neighbors = graph.get_neighbors(node)
next_node = neighbors[0]
next_node_score = scores[next_node]
for neighbor in neighbors:
    neighbor_score = scores[neighbor]
    if neighbor_score > next_node_score:
        next_node = neighbor
        next_node_score = neighbor_score
```

For `stochastic_greedy`, we sample neighbors proportional to their score:
```python
sum_neighbor_scores = 0
for neighbor in graph.neighbors(node):
   sum_neighbor_scores += scores[neighbor]

r *= sum_neighbor_scores

tmp = 0
for neighbor in graph.neighbors(node):
   tmp += scores[neighbor]
   if r < tmp:
       next_node = neighbor
       break
```

In `Gunrock`, we create a frontier containing all of the nodes we want to walk from (currently, hardcoded to all the nodes in the graph).  Then we map the transition function over the frontier using `Gunrock`'s `ForEach` operator, replacing the current nodes in the frontier w/ the chosen neighbor, and recording the random walk in an output array.

Because this is such a straightforward modification, we implement `GraphSearch` inside of the existing `RandomWalk` Gunrock application.  This just requires adding a couple of extra flags and one extra array of size `|V|` to store the node values.

## How To Run This Application on DARPA's DGX-1

### Prereqs/input
```
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock/tests/rw/
cp ../../gunrock/util/gitsha1.c.in ../../gunrock/util/gitsha1.c
make clean
make
```

### Running the application
Application specific parameters:
```
    --walk-mode
        0 = uniform
        1 = greedy
        2 = stochastic_greedy
    --node-value-path
        If --walk-mode != 0, this is the path to node scores
    --walk-length
        Length of each walk
    --walks-per-node
        Number of walks to do per seed node
    --seed
        Seed for random number generator
```

Example:
```bash
# generate random features
python random-values.py 39 > chesapeake.values

# uniform random
./bin/test_rw_9.1_x86_64 --graph-type market --graph-file ../../dataset/small/chesapeake.mtx --walk-mode 0 --seed 123

# greedy
./bin/test_rw_9.1_x86_64 --graph-type market --graph-file ../../dataset/small/chesapeake.mtx --node-value-path chesapeake.values --walk-mode 1

# stochastic greedy
./bin/test_rw_9.1_x86_64 --graph-type market --graph-file ../../dataset/small/chesapeake.mtx --node-value-path chesapeake.values --walk-mode 2 --seed 123
```

Output:
```
# ------------------------------------------------------------------------
# uniform random

Loading Matrix-market coordinate-formatted graph ...
Reading from ../../dataset/small/chesapeake.mtx:
  Parsing MARKET COO format
 (39 nodes, 340 directed edges)... 
Done parsing (0 s).
  Converting 39 vertices, 340 directed edges ( ordered tuples) to CSR format...
Done converting (0s).
__________________________
--------------------------
 Elapsed: 0.001907
Using advance mode LB
Using filter mode CULL
num_nodes=39
__________________________
0    0   0   queue3      oversize :  234 ->  682
0    0   0   queue3      oversize :  234 ->  682
0    1   0   queue3      oversize :  682 ->  1085
0    1   0   queue3      oversize :  682 ->  1085
0    5   0   queue3      oversize :  1085 ->     1166
0    5   0   queue3      oversize :  1085 ->     1166
--------------------------
Run 0 elapsed: 4.551888, #iterations = 10
[[0, 38, 8, 35, 11, 25, 13, 27, 37, 7, ],
[1, 34, 1, 38, 30, 38, 29, 37, 7, 37, ],
[2, 17, 2, 38, 4, 38, 10, 18, 14, 28, ],
[3, 16, 3, 35, 14, 27, 38, 32, 37, 11, ],
...
[36, 33, 0, 22, 38, 27, 37, 18, 38, 8, ],
[37, 21, 31, 17, 25, 17, 18, 32, 37, 26, ],
[38, 7, 8, 34, 6, 5, 6, 5, 38, 19, ]]
-------- NO VALIDATION -----[rw] finished.
 avg. elapsed: 4.551888 ms
 iterations: 10
 min. elapsed: 4.551888 ms
 max. elapsed: 4.551888 ms
 load time: 60.925 ms
 preprocess time: 964.890000 ms
 postprocess time: 0.715017 ms
 total time: 970.350027 ms

# ------------------------------------------------------------------------
# greedy
# !! In this case, the output is formatted as `GPU_result:CPU_result`, for correctness checking

Loading Matrix-market coordinate-formatted graph ...
Reading from ../../dataset/small/chesapeake.mtx:
  Parsing MARKET COO format
 (39 nodes, 340 directed edges)... 
Done parsing (0 s).
  Converting 39 vertices, 340 directed edges ( ordered tuples) to CSR format...
Done converting (0s).
__________________________
--------------------------
 Elapsed: 0.085831
Using advance mode LB
Using filter mode CULL
num_nodes=39
__________________________
0    0   0   queue3      oversize :  234 ->  682
0    0   0   queue3      oversize :  234 ->  682
0    1   0   queue3      oversize :  682 ->  770
0    1   0   queue3      oversize :  682 ->  770
--------------------------
Run 0 elapsed: 0.695944, #iterations = 10
[[0:0, 22:22, 32:32, 18:18, 11:11, 18:18, 11:11, 18:18, 11:11, 18:18, ],
[1:1, 22:22, 32:32, 18:18, 11:11, 18:18, 11:11, 18:18, 11:11, 18:18, ],
[2:2, 17:17, 2:2, 17:17, 2:2, 17:17, 2:2, 17:17, 2:2, 17:17, ],
[3:3, 16:16, 2:2, 17:17, 2:2, 17:17, 2:2, 17:17, 2:2, 17:17, ],
...
[36:36, 33:33, 36:36, 33:33, 36:36, 33:33, 36:36, 33:33, 36:36, 33:33, ],
[37:37, 18:18, 11:11, 18:18, 11:11, 18:18, 11:11, 18:18, 11:11, 18:18, ],
[38:38, 2:2, 17:17, 2:2, 17:17, 2:2, 17:17, 2:2, 17:17, 2:2, ]]
0 errors occurred.
[rw] finished.
 avg. elapsed: 0.695944 ms
 iterations: 10
 min. elapsed: 0.695944 ms
 max. elapsed: 0.695944 ms
 load time: 44.2419 ms
 preprocess time: 974.721000 ms
 postprocess time: 0.731945 ms
 total time: 976.338863 ms


# stochastic greedy
# !! TODO
```


### Output

When run in `verbose` mode, the app outputs the walks.  When run in `quiet` mode, it outputs performance statistics.  If running `greedy` `GraphSearch`, the app also outputs the results of a correctness check.

Because of the stochasticity of the app, we do not have correctness checks for `uniform` or `stochastic_greedy`.  However, we have validated the underlying algorithms in outside experiments.

## Performance and Analysis

Performance is measured by the runtime of the app, given
 - an input graph
 - set of seed nodes (hardcoded to all nodes in Graph)
 - number of walks per seed
 - number of steps per walk
 - a transition function (eg `uniform|greedy|stochastic_greedy`)

### Implementation limitations

The output of the random walk is a dense array of size `(# seeds) * (steps per walk) * (walks per seed)`.  For a large graph _or_ long walks _or_ multiple walks per seed, this array may exceed the size of GPU memory. 

This app can only be used for graphs that have scores associated w/ each node.  In order to run benchmarks, if scores are not available we often assign uniformly random scores to nodes.

### Comparison against existing implementations

We measure runtime on the [HIVE graphsearch Twitter dataset](https://hiveprogram.com/data/_v0/graph_search/).
 - Nodes: 9291392
 - Edges: 21741663

#### HIVE Python reference implementation

We run the HIVE Python reference implementation w/ the following settings:
 - undirected graph
 - 100 random seeds
 - 10000 steps per walk

With the `greedy` transition function, the run took `139.31s`.
With the `uniform` transition function, the run took `310.25s`.

!! Could flesh this out more, but it's so slow it's not very interesting

#### PNNL OpenMP implementation

We run the PNNL OpenMP implementation on the Twitter graph w/ the following settings:
 - 1,2,4,8,16,32 or 64 threads
 - `greedy` or `uniform` transition function
 - directed or undirected graph


| threads | transition | num_nodes | num_edges | num_seeds | seconds  | steps | steps_per_second | neighbors | neighbors_per_second | 
|---------|------------|-----------|-----------|-----------|----------|-------|------------------|-----------|----------------------|
|dir|1|greedy|7199978|21741663|7199978|3.02876|16325873|5.39027e+06|298668024|9.86105e+07
|dir|2|greedy|7199978|21741663|7199978|2.83467|16325873|5.75936e+06|298668024|1.05363e+08
|dir|4|greedy|7199978|21741663|7199978|1.64405|16325873|9.9303e+06|298668024|1.81666e+08
|dir|8|greedy|7199978|21741663|7199978|0.870028|16325873|1.87648e+07|298668024|3.43286e+08
|dir|16|greedy|7199978|21741663|7199978|0.605769|16325873|2.69507e+07|298668024|4.93039e+08
|dir|32|greedy|7199978|21741663|7199978|0.43742|16325873|3.73231e+07|298668024|6.82794e+08
|dir|64|greedy|7199978|21741663|7199978|0.236701|16325873|6.89725e+07|298668024|1.26179e+09

```

We omit the `greedy` undirected case because the algorithm gets stuck jumping between a local maximum and it's highest scoring neighbor.

All experiments conducted on the HIVE DGX-1.

### Performance limitations

<TODO>
e.g., random memory access?
</TODO>

## Next Steps

### Alternate approaches

The size of the output array may become a significant bottleneck for large graphs.  However, since all of the transition functions do not depend on anything besides the current node, we could reasonably move the results of the walk from GPU to CPU memory every N iterations.  Properly executed, this should eliminate the largest bottleneck without unduely impacting performance.

### Gunrock implications

For the `greedy` and `stochastic_greedy` transition function, we have to sequentially iterate over all of a node's neighbors.  Simple wrappers for computing eg. the maximum of node scores across all of a nodes neighbors could be helpful, both for ease of programming and performance.

### Notes on multi-GPU parallelization

<TODO>
What will be the challenges in parallelizing this to multiple GPUs on the same node?
Can the dataset be effectively divided across multiple GPUs, or must it be replicated?
</TODO>

### Notes on dynamic graphs

This workflow does not have an explicit dynamic component. However, because steps only depend on the current node, the underlying graph could be changing as the walks are happening without causing too much trouble.

### Notes on larger datasets

<TODO>
What if the dataset was larger than can fit into GPU memory or the aggregate GPU memory of multiple GPUs on a node? What implications would that have on performance? What support would Gunrock need to add?
</TODO>

### Notes on other pieces of this workload

In real use cases, the scoring function would be computed lazily -- that is, we wouldn't have a precomputed array with scores for each of the nodes.  Thus, it would be critical for us to be able to call the scoring function from within Gunrock a) quickly and b) without excessive programmer overhead.


