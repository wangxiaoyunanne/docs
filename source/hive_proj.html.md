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

The `csrgemm` functions in cuSPARSE allocate memory more intelligently, on the order number of edges in output, and thus can scale to substantially larger matrices than our Gunrock implementation.  However, a single call to `csrgemm` is still restricted by GPU memory (16GB on the DGX-1) -- this limit can easily be hit by moderately sized graphs.

Thus, we implement a chunked matrix multiply.  Specifically, to compute `X.dot(Y)` w/ `X.shape = (n, m)` and `Y.shape = (m, k)`, we split `X` into `c` matrices `(X_1, ..., X_c)`, w/ `X_i.shape = (n / c, m)`.  Then we compute `X_i.dot(Y)` for each `X_i`, moving the output of each multiplication from GPU to CPU memory as we go.  This implementation addresses the case where we can fit both `X` and `Y` in GPU memory, but cannot fit `X.dot(Y)` which is often orders of magnitude more dense.

The chunked matrix multiply clearly incurs a performance penalty, but allows us to run graph projections of much larger graphs on the GPU.

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

Currently, for the chunked matrix multiply, CPU memory allocation and GPU to CPU memory copies for `X_i.dot(Y)` block the computation of `X_[i+1].dot(Y)`.  This could be addressed using CUDA streams, but would require some redesign of the GraphBLAS APIs.

Certain weighting functions are easily implemented by applying a transformation to the values of the sparse matrices, but others cannot.  For instance, one of the weighting functions in the reference implementation is:
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

#### Existing implementations

##### PNNL

We compare our results against [PNNL's OpenMP reference implementation](https://gitlab.hiveprogram.com/jfiroz/graph_projection).  We make a minor modification to their code to handle unweighted graphs, to match the Gunrock and GraphBLAS implementations.  (Eg, the weight of the edge in the output graph is the number of shared neighbors in the original graph).

There is a `simple` flag in PNNLs code, but examining the code reveals that it just changes the order of operations.  Thus, all experiments are conducted with `simple=1`, which is faster than `simple=0` due to better data access patterns.

##### Scipy

A very simple baseline is sparse matrix-matrix multiplication as implemented in the popular `scipy` python package.  This is a single-threaded C++ implementation with a Python wrapper.

#### Experiments

MovieLens is a bipartite graph w/ `|U|=138493`, `|V|=26744` and `|E|=20000264`. We report results on the full graph, as well as several random subgraphs.

For PNNL's OpenMP implementation, we report results using 1,2,4,8,16,32 or 64 threads.

In all cases, we project onto the nodeset `|V|`, producing a `|V|x|V|` graph.

PNNL results are in the format `threads num_nodes num_edges elapsed_seconds nnz_out`.  Note that small differences in the number of nonzero entries in the output is due to small book-keeping differences (specifically, keeping or dropping self-loops).

```
# --
# |U|=6743 |V|=13950 |E|=1M

scipy:
  {"nnz": 63104132, "elapsed": 2.4912478923797607}

PNNL:
  1 20693 1000000 61.4852 63090182
  2 20693 1000000 62.2842 63090182
  4 20693 1000000 60.1542 63090182
  8 20693 1000000 37.5853 63090182
  16 20693 1000000 22.0257 63090182
  32 20693 1000000 13.1482 63090182
  64 20693 1000000 9.055 63090182

Gunrock: 0.0600s

GraphBLAS: 0.366s

# --
# |U|=34395 |V|=20402 |E|=5M

scipy:
  {"nnz": 157071858, "elapsed": 10.105232000350952}

PNNL:
  1 54797 5000000 357.511 157051456
  2 54797 5000000 309.723 157051456
  4 54797 5000000 218.519 157051456
  8 54797 5000000 113.987 157051456
  16 54797 5000000 57.4606 157051456
  32 54797 5000000 38.1186 157051456
  64 54797 5000000 29.0056 157051456

Gunrock: 0.3349s

GraphBLAS: 1.221s

# --
# |U|=138493 |V|=26744 |E|=20M

scipy:
  {"nnz": 286857534, "elapsed": 39.18109321594238}

PNNL:
  1 165237 20000263 ------- 286830790
  2 165237 20000263 1109.32 286830790
  4 165237 20000263 727.224 286830790
  8 165237 20000263 358.708 286830790
  16 165237 20000263 188.701 286830790
  32 165237 20000263 102.964 286830790
  64 165237 20000263 163.731 286830790

Gunrock: out-of-memory error

GraphBLAS: 5.012s
```

Next we test on a [scale 18 RMAT graph](https://graphchallenge.s3.amazonaws.com/synthetic/graph500-scale18-ef16/graph500-scale18-ef16_adj.tsv.gz).  This is _not_ a bipartite graph, but the graph projection algorithm can still be applied.

This graph was chosen because it was used in benchmarks in [PNNL's gitlab repo](https://gitlab.hiveprogram.com/jfiroz/graph_projection).  However, their command line parameters appear to be incorrect, so our results here are substantially different.

```
# |V|=174147 |E|=7600696

scipy:
  {"nnz": 2973926895, "elapsed": 150.869460105896}

PNNL
  64 174147 7600696 602.69 2973752748
  32 174147 7600696 369.278 2973752748
  16 174147 7600696 419.468 2973752748
  8 174147 7600696 677.582 2973752748
  4 174147 7600696 812.453 2973752748

Gunrock: out-of-memory error

GraphBLAS: 26.478s
```

Note that the PNNL multi-threaded implementation is consistently 2-3x slower than the single-threaded scipy implementation. 

_When the dataset can fit into memory_, Gunrock is \~ 4x faster than GraphBLAS.  Since the two implementations use slightly different algorithms, it's hard to tell where the Gunrock speedup comes from.  Our hunch is that Gunrock's superior load balancing gives better performance than GraphBLAS, but this is an interesting topic for further research.


### Performance information

#### Gunrock
  - Results of profiling indicate that the Gunrock implementation is bound by memory latency.
  - The device memory bandwidth is 297GB/s -- within the expected range for Gunrock graph analytics.
  - 92% of the runtime is spent in the advance operater.

#### GraphBLAS
 - 99% of time is spent in cuSPARSE's `csrgemm` routines


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

The GraphBLAS chunked matrix multiply is trivially extended to multiple GPUs.  

### Notes on dynamic graphs

This workflow does not have an explicit dynamic component.  However, the graph projection operation seems like it would be fairly straightforward to adapt to dynamic graphs -- as nodes/edges are added to `G`, we create/increment the weight of the appropriate edges in `H`.

### Notes on larger datasets

<TODO>
What if the dataset was larger than can fit into GPU memory or the aggregate GPU memory of multiple GPUs on a node? What implications would that have on performance? What support would Gunrock need to add?
</TODO>

### Notes on other pieces of this workload

This workload does not involve any non-graph components.

