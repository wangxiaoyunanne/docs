---
title: Graph Projections (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Graph Projections

Given a graph `G`, graph projection outputs a graph `H` such that `H` contains edge `(u, v)` iff `G` contains edges `(u, w)` and `(v, w)` for some node `w`.  That is, graph projection creates a new graph where nodes are connected iff they share an (outgoing) neighbor in the original graph.

Graph projection is most commonly used when the input graph `G` is bipartitite with node sets `U` and `V` and directed edges `(u, v)`.  In this case, the operation yields a unipartite projection onto one of the node sets.

## Summary of Gunrock Implementation

We implement graph projections in Gunrock as a single `advance` operation from all nodes w/ nonzero outgoing degree:
```
def _advance_op(self, G, H_edges, src, dest):
    for neib in G.neighbors(src):
        if dest != neib:
            H.edges[(dest, neib)] += 1
```
That is, for each edge in the graph, we fetch the neighbors of the source node in `G`, then increment the weight of the edge between `dest` and each of the neighbors in `H`.

To store the edges of the output matrix `H`, we use a dense `|V|x|V|` array.  This is simple and fast, but uses an unreasonably large amount of memory (60k nodes -> 16gb).

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

```bash
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock/tests/proj/
make clean
make
```

### Running the application

```bash
./bin/test_proj_9.1_x86_64 --graph-type market --graph-file ../../dataset/small/chesapeake.mtx
```
Output:
```
Loading Matrix-market coordinate-formatted graph ...
Reading from ../../dataset/small/chesapeake.mtx:
  Parsing MARKET COO format edge-value-seed = 1539110067
 (39 nodes, 340 directed edges)... 
Done parsing (0 s).
  Converting 39 vertices, 340 directed edges ( ordered tuples) to CSR format...
Done converting (0s).
__________________________
--------------------------
 Elapsed: 0.026941
Using advance mode LB
Using filter mode CULL
__________________________
0    0   0   queue3      oversize :  234 ->  342
0    0   0   queue3      oversize :  234 ->  342
--------------------------
Run 0 elapsed: 0.199080, #iterations = 1
edge_counter=1372
0->1 | GPU=9.000000 CPU=9.000000
0->2 | GPU=1.000000 CPU=1.000000
0->3 | GPU=2.000000 CPU=2.000000
0->4 | GPU=3.000000 CPU=3.000000
0->5 | GPU=3.000000 CPU=3.000000
0->6 | GPU=6.000000 CPU=6.000000
0->7 | GPU=5.000000 CPU=5.000000
0->8 | GPU=4.000000 CPU=4.000000
0->9 | GPU=3.000000 CPU=3.000000
...
38->33 | GPU=2.000000 CPU=2.000000
38->34 | GPU=13.000000 CPU=13.000000
38->35 | GPU=28.000000 CPU=28.000000
38->36 | GPU=2.000000 CPU=2.000000
38->37 | GPU=18.000000 CPU=18.000000
======= PASSED ======
[proj] finished.
 avg. elapsed: 0.199080 ms
 iterations: 38594739
 min. elapsed: 0.199080 ms
 max. elapsed: 0.199080 ms
 src: 0
 nodes_visited: 38578864
 edges_visited: 38578832
 nodes queued: 140734466796512
 edges queued: 140734466795232
 load time: 85.5711 ms
 preprocess time: 955.861000 ms
 postprocess time: 3.808022 ms
 total time: 960.005045 ms
```


### Output

When run in `verbose` mode, the app outputs the weighted edgelist of the projected graph.  When run in `quiet` mode, it outputs performance statistics and the results of a correctness check.

We compared the results of the Gunrock implementation to the [HIVE reference implementation](https://hiveprogram.com/wiki/display/WOR/V0+-+Application+Classification) and the [PNNL implementation](https://gitlab.hiveprogram.com/jfiroz/graph_projection).  These two implementations vary slightly in their output -- we remained faithful to the HIVE reference implementation.  

## Performance and Analysis

We measure the runtime of the app.

### Implementation limitations

The primary limitation of the current implementation is that it allocates a `|V|x|V|` array, where `|V|` is the number of nodes in the network.  This means that the memory requirements of the app can easily exceed the memory available on a single GPU.  The size of this array reflects the _worst case_ memory requirements of the graph projection workflow; while some graphs can become exceptionally large and dense when projected, we would likely be able to run the app on larger graphs if we stored the output in a sparse data structure (eg a hashmap). 

Graph projection is often used for bipartite graphs, but this app does not make any assumptions about the topology of the graph.  This choice was made in order to remain consistent with the [HIVE reference implementation](https://hiveprogram.com/wiki/display/WOR/V0+-+Application+Classification).

There are various ways that the edges of the output graph `H` can be weighted.  We only implement graph projections for unweighted graphs.  The weights of the edges `(u, v)` in the output graph `H` are simply the number of (outgoing) neighbors that `u` and `v` have in common in the original graph.  Implementation of other weight functions would be fairly straightforward.

### Comparison against existing implementations

- [HIVE reference implementation](https://hiveprogram.com/wiki/display/WOR/V0+-+Application+Classification)
- [PNNL implementation](https://gitlab.hiveprogram.com/jfiroz/graph_projection)

<still-todo>
    show runtime on LANL and Movielens datasets vs the above two implementations
</still-todo>

### Performance limitations

<still-todo>
    e.g., random memory access?
</still-todo>

## Next Steps

### Alternate approaches

Another straightforward way to implement graph projections would be as a single sparse matrix multiplication `G.dot(G.T)` -- it would be interesting to compare the performance of this Gunrock implementation with a high-quality GPU SpMM-based implementation.

As mentioned above, it would also be worthwhile to implement a version that does not require allocating the `|V|x|V|` array.  This could be accomplished by using a sparse data structure (eg, a hashmap or a mutable graph), or possibly by moving intermediate results from GPU to CPU memory during the computation.

### Gunrock implications

If Gunrock implemented a mutable graph structure that allowed for fast edge insertion, we could avoid allocating the `|V|x|V|` array.  This does not impact _worst case_ memory usage, but ikely would give us better scalability in practice.

### Notes on multi-GPU parallelization

<still-todo>
What will be the challenges in parallelizing this to multiple GPUs on the same node?
Can the dataset be effectively divided across multiple GPUs, or must it be replicated?
</still-todo>

### Notes on dynamic graphs

The description of this workflow does not have an explicit dynamic component.  However, the graph projection operation seems like it would be fairly straightforward to adapt to dynamic graphs -- as nodes/edges are added to `G`, we create/increment the weight of the appropriate edges in `H`.

### Notes on larger datasets

<still-todo>
What if the dataset was larger than can fit into GPU memory or the aggregate GPU memory of multiple GPUs on a node? What implications would that have on performance? What support would Gunrock need to add?
</still-todo>

### Notes on other pieces of this workload

This workload does not involve any non-graph components.


