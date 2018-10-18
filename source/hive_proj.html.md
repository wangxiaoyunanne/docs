---
title: Graph Projections (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Graph Projections

Given a (directed) graph `G`, graph projection outputs a graph `H` such that `H` contains edge `(u, v)` iff `G` contains edges `(w, u)` and `(w, v)` for some node `w`.  That is, graph projection creates a new graph where nodes are connected iff they are neighbors of the same node in the original graph.  Typically, the edge weights of `H` are computed via some (simple) function of the corresponding edge weights of `G`.

Graph projection is most commonly used when the input graph `G` is bipartitite with node sets `U1` and `U2` and directed edges `(u, v)`.  In this case, the operation yields a unipartite projection onto one of the node sets.

## Summary of Gunrock Implementation

We implement two versions of graph projections.

#### Gunrock

First, we can compute graph projection in Gunrock via a single `advance` operation from all nodes w/ nonzero outgoing degree:
```
def _advance_op(self, G, H_edges, src, dest):
    for neib in G.neighbors(src):
        if dest != neib:
            H_edges[dest * G.num_nodes + neib] += 1
```
That is, for each edge in the graph, we fetch the neighbors of the source node in `G`, then increment the weight of the edge between `dest` and each of the neighbors in `H`. 

Note that we have only considered the unweighted case and a single method for computing the edgeweights of `H`, but the extension to weighted graphs and different weighting functions would be straightforward.

We use a dense `|V|x|V|` array to store the edges of the output matrix `H`.  This is simple and fast, but uses an unrealistically large amount of memory (60k nodes -> 16gb).  Though, in the worst case, `H` may actually have all `|V|x|V|` possible edges, many real world graphs have far fewer.

#### GraphBLAS

Second, we implement graph projection as a single sparse matrix-matrix multiply in [GraphBLAS](https://github.com/owensgroup/GraphBLAS), which wraps and extends cuSPARSE.  Graph projection admits a simple linear algebra formulation:
```
matmul(tranpose(A), A)
```
which can be concisely implemented via cuSPARSE's `csr2csc` and `csrgemm` functions.

The `csrgemm` functions in cuSPARSE allocate memory more intelligently, on the order number of edges in output, and thus can scale to substantially larger matrices than our Gunrock implementation.  This implementation is still restricted by GPU memory (16GB on the DGX-1) -- this limit can easily be hit by moderately sized graphs.  

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

```bash
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock/tests/proj/
cp ../../gunrock/util/gitsha1.c.in ../../gunrock/util/gitsha1.c
make clean
make
# !! May need to change compute capability in `gunrock/tests/BaseMakefile.mk`
```

### Running the application
Application specific parameters: NONE

#### Gunrock

Example:
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

#### GraphBLAS

<TODO>
</TODO>

### Output

#### Gunrock

When run in `verbose` mode, the app outputs the weighted edgelist of the projected graph.  When run in `quiet` mode, it outputs performance statistics and the results of a correctness check.

We compared the results of the Gunrock implementation to the [HIVE reference implementation](https://hiveprogram.com/wiki/display/WOR/V0+-+Application+Classification) and the [PNNL implementation](https://gitlab.hiveprogram.com/jfiroz/graph_projection).  These two implementations vary slightly in their output -- we validated our results against the HIVE reference implementation.  

#### GraphBLAS

## Performance and Analysis

Performance is measured by the runtime of the app, given:
 - an input graph (possibly bipartite)
 - whether to project onto the rows or columns of the graph

### Implementation limitations

### Gunrock

The primary limitation of the current implementation is that it allocates a `|V|x|V|` array, where `|V|` is the number of nodes in the network.  This means that the memory requirements of the app can easily exceed the memory available on a single GPU.  The size of this array reflects the _worst case_ memory requirements of the graph projection workflow; while some graphs can become exceptionally large and dense when projected, we would likely be able to run the app on larger graphs if we stored the output in a sparse data structure (eg a hashmap).  There are methods for mitigating this restriction: cuSPARSE's `csrgemm` methods compute the row pointers in one pass, then allocate memory more efficiently for the column and value arrays, and then actually compute the matrix product.  An interesting future direction would be to integrate this sort of algorithm into Gunrock.

Graph projection is often used for bipartite graphs, but this app does not make any assumptions about the topology of the graph.  This choice was made in order to remain consistent with the [HIVE reference implementation](https://hiveprogram.com/wiki/display/WOR/V0+-+Application+Classification).

There are various ways that the edges of the output graph `H` can be weighted.  We only implement graph projections for unweighted graphs.  The weights of the edges `(u, v)` in the output graph `H` are simply the number of (incoming) neighbors that `u` and `v` have in common in the original graph.  Implementation of other weight functions would be fairly straightforward.

### GraphBLAS

The GraphBLAS implementation uses memory much more efficiently, but still requires that the output array fits in a single GPUs memory.  This could be solved by incrementally computing the projection and moving the results from GPU to CPU memory as necessary. __We could do this now?__

Certain weighting functions are easily implemented by applying some transformation to the values of the sparse matrices, but others cannot.  For instance, one of the weighting functions in the reference implementation is:
```
    weight_out = weight_edge_1 / (weight_edge_1 + weight_edge_2)
```
which may be difficult to implement in the plus/multiply semiring.  However, it's straightforward to support many other weighting functions:
```
    weight_out = 1                             (by setting both matrices entries to 1)
    weight_out = weight_edge_1                 (by setting one matrices  entries to 1)
    weight_out = weight_edge_1 / weight_edge_2 (by setting one matrices  entries to 1 / x)
    ...
```

The planned implementation of additional semirings in GraphBLAS would extend the kinds of weightings we could support. 

### Comparison against existing implementations

- [HIVE reference implementation](https://hiveprogram.com/wiki/display/WOR/V0+-+Application+Classification)

#### PNNL

We compare our results against [PNNL's OpenMP reference implementation](https://gitlab.hiveprogram.com/jfiroz/graph_projection).  We make a minor modification to their code to handle unweighted graphs, to match the Gunrock and GraphBLAS implementations.  (Eg, the weight of the edge in the output graph is the number of shared neighbors in the original graph).

There is a `simple` flag in PNNLs code, but examining the code reveals that it just changes the order of operations.  Thus, all experiments are conducted with `simple=1`, which was the faster of the two due to better cache usage.

First, we report results on a subset of the MovieLens-20M dataset, using
 - 1,2,4,8,16,32 or 64 threads

This dataset has `|U|=6743`, `|V|=13950` and `|E|=1M`.  We project onto the columns to create a `|V|x|V|` matrix.

```

```

Notice that 64 threads only gets us 2.35x speedup.

Next, we report results on the entire MovieLens-20M datset, using
- 1,2,4,8,16,32 or 64 threads

This dataset has `|U|=138493`, `|V|=26744` and `|E|=20000264`.  We project onto the columns to create a `|V|x|V|` matrix.

```

```

Next, we report results on a (scale 18 RMAT graph](https://graphchallenge.s3.amazonaws.com/synthetic/graph500-scale18-ef16/graph500-scale18-ef16_adj.tsv.gz), using 
- 1,2,4,8,16,32 or 64 threads

```
==> results/rmat <==
1 262144 4194304 39.2209 4865426
2 262144 4194304 28.7223 4865426
4 262144 4194304 15.5026 4865426
8 262144 4194304 11.2476 4865426
16 262144 4194304 9.35304 4865426
32 262144 4194304 5.42222 4865426
64 262144 4194304 4.98734 4865426
```

This shows substantially better speedup, with 64 threads giving about 8x speedup. __Appears to be incorrect.  He passes the wrong number of nodes and edges?__

#### MovieLens

MovieLens is a bipartite graph w/ `|U|=138493`, `|V|=26744` and `|E|=20000264`.

Allocating the necessary `|U|x|V|` matrix required by Gunrock would require > 14GB, which is towards the upper limit of available GPU memory.  However, Gunrock does not natively support bipartite graphs, so we'd actually have to allocate a `(|U| + |V|)x(|U| + |V|)`, which is soundly outside the memory constraints.

Projecting MovieLens onto the rows produces an output that is too big for GraphBLAS.

<TODO>
    show runtime on LANL and Movielens datasets vs the above two implementations
    smaller graph where we can compare benchmark, graphblas and gunrock
</TODO>

### Performance limitations

<TODO>
    e.g., random memory access?
</TODO>

## Next Steps

### Alternate approaches

Another straightforward way to implement graph projections would be as a single sparse matrix multiplication `G.T.dot(G)` -- it would be interesting to compare the performance of this Gunrock implementation with a high-quality GPU SpMM-based implementation.

As mentioned above, it would also be worthwhile to implement a version that does not require allocating the `|V|x|V|` array.  This could be accomplished by using a sparse data structure (eg, a hashmap or a mutable graph), or possibly by moving intermediate results from GPU to CPU memory during the computation.

### Gunrock implications

Gunrock support for bipartite graphs would make programming bipartite graph projections easier and more scalable.

If Gunrock implemented a mutable graph structure that allowed for fast edge insertion, we may be able to avoid allocating the `|V|x|V|` array.  This does not impact _worst case_ memory usage, but likely would give us better scalability in practice.

### Notes on multi-GPU parallelization

<TODO>
What will be the challenges in parallelizing this to multiple GPUs on the same node?
Can the dataset be effectively divided across multiple GPUs, or must it be replicated?
</TODO>

### Notes on dynamic graphs

This workflow does not have an explicit dynamic component.  However, the graph projection operation seems like it would be fairly straightforward to adapt to dynamic graphs -- as nodes/edges are added to `G`, we create/increment the weight of the appropriate edges in `H`.

### Notes on larger datasets

<TODO>
What if the dataset was larger than can fit into GPU memory or the aggregate GPU memory of multiple GPUs on a node? What implications would that have on performance? What support would Gunrock need to add?
</TODO>

### Notes on other pieces of this workload

This workload does not involve any non-graph components.


