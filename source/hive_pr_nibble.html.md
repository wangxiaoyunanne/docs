---
title: Template for HIVE workflow report

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

<aside class="notice">
  JDO notes, delete these when you copy this to `hive_yourworkflowname`: The goal of this report is to be useful to DARPA and to your colleagues. This is not a research paper. Be very honest. If there are limitations, spell them out. If something is broken or works poorly, say so. Above all else, make sure that the instructions to replicate the results you report are good instructions, and the process to replicate are as simple as possible; we want anyone to be able to replicate these results in a straightforward way.
</aside>

# Local Graph Clustering (LGC)

From [Andersen et al](https://projecteuclid.org/euclid.im/1243430567): > A local graph clustering algorithm finds a cut near a specified starting vertex, with a running time that depends largely on the size of the small side of the cut, rather than the size of the input graph. A common algorithm for local graph clustering is called PageRank-Nibble (PR-Nibble). We implment a coordinate descent variant of this algorithm found in [Fountoulakis et al.](https://arxiv.org/pdf/1602.01886.pdf).

## Summary of Gunrock Implementation

The algorithm in [Fountoulakis et al.](https://arxiv.org/pdf/1602.01886.pdf) maps in a straightforward manner to Gunrock. We present the pseudocode below along with the corresponding Gunrock operations:
```
A: adjacency matrix of graph
D: diagonal degree matrix of graph
Q: D^(-1/2) x (D - (1 - alpha)/2 x (D + A)) x D^(-1/2)
s: teleportation distribution, a distribution over nodes of graph
d_i: degree of node i
p_0: PageRank vector at iteration 0
q_0:  D^(-1/2) x p term that coordinate descent optimizes over
f(q): 1/2<q, Qq> - alpha x <s, D^(-1/2) x q>
grad_f_i(q_0): i'th term of the gradient of f(q_0) using q at iteration 0
rho: constant used to ensure convergence
alpha: teleportation constant in (0, 1)

Initialize: rho > 0
Initialize: q_0 = [0 ... 0]
Initialize: grad_f(q_0) = -alpha x D^(-1/2) x s

// Note: || y ||_inf is the infinity norm
For k = 0, 1, ..., inf
    // Implemented using Gunrock ForAll operator
    Choose an i such that grad_f_i(q_k) < - alpha x rho x d_i^(1/2)
    q_k+1(i) = q_k(i) - grad_f_i(q_k)
    grad_f_i(q_k+1) = (1 - alpha)/2 x grad_f_i(q_k)
    
    // Implemented using Gunrock Advance and Filter operator
    For each j such that j ~ i
        Set grad_f_j(q_k+1) = grad_f_j(q_k) + (1 - alpha)/(2d_i^(1/2) x d_j^(1/2)) x A_ij x grad_f_i(q_k)
    For each j such that j !~ j
        Set grad_f_j(q_k+1) = grad_f_j(q_k)
    
    // Implemented using Gunrock ForEach operator
    if (||D^(-1/2) x grad_f(q_k)||_inf > rho x alpha) break
EndFor
return p_k = D^(1/2) x q_k
```

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

```bash
git clone --recursive https://github.com/gunrock/gunrock.git
cd gunrock

# build Gunrock
cmake .
make -j16

# build App
cd tests/pr_nibble
make -j16

```

### Running the application

```bash
./bin/test_pr_nibble_9.1_x86_64 \
    --graph-type market \
    --graph-file ../../dataset/small/chesapeake.mtx \
    --src 0 \
    --max-iter 1
```

Output:
```
Loading Matrix-market coordinate-formatted graph ...
Reading from ../../dataset/small/chesapeake.mtx:
  Parsing MARKET COO format
 (39 nodes, 340 directed edges)...
Done parsing (0 s).
  Converting 39 vertices, 340 directed edges ( ordered tuples) to CSR format...
Done converting (0s).
__________________________
pr_nibble::CPU_Reference: reached max iterations. breaking at it=1
--------------------------
 Elapsed: 0.018835
Using advance mode LB
Using filter mode CULL
__________________________
pr_nibble::Stop_Condition: reached max iterations. breaking at it=1
--------------------------
Run 0 elapsed: 0.252008, #iterations = 1
0 errors occurred.
[pr_nibble] finished.
 avg. elapsed: 0.252008 ms
 iterations: 140734444779008
 min. elapsed: 0.252008 ms
 max. elapsed: 0.252008 ms
 src: 0
 nodes_visited: 5326555
 edges_visited: 2
 nodes queued: 140734444778192
 edges queued: 38878400
 load time: 82.2091 ms
 preprocess time: 978.001000 ms
 postprocess time: 0.098944 ms
 total time: 978.564978 ms
 ```
 
### Output

We output information about the quality of the match in each iteration. The most important number is X errors occurred, which gives the number of disagreements between our CPU validation and our result. X = 0 indicates that LGC has generated an output that matches exactly with our CPU validation.

This implementation is validated against the [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/local_graph_clustering_socialmedia). 

## Performance and Analysis

Performance is primarily measured in runtime of the clustering portion of the LGC procedure. We do not compare the sweep-cut component, because we do not find it to be the meaningful component in this application.  In particular, the LSAP solver in the first iteration tends to take 10-100x longer than in subsequent iterations.

### Implementation limitations

- **Memory size**: The dataset is assumed to be an undirected graph, with self-loops (i.e. edges from vertex i to vertex i are removed). We were able to run on graphs of up to 6.2GB in size (7M vertices, 194M edges). The memory limitation should be the number of edges 2x|E| and 7x|V|, which needs to be smaller than the GPU memory size (16GB for a single P100 on DGX-1). 

- **Data type**: We have tested only using int32 data type, but there is no reason int64 for graphs with more than 4B edges cannot be used too.

### Comparison against existing implementations

- UCB reference implementation (Python wrapper around C++ library)
- CPU reference implementation (C++)

We find the Gunrock implementation is 3 orders of magnitude faster than either reference CPU implementation implemented in C++. The minimum, geomean, and maximum speedups are 7.25x, 1297x, 32899x.

Comparison can be replicated by doing the following.

```bash
# download datasets
cd dataset/large
make -j16

# run script
sh test_big.sh
```
All runtimes are in milliseconds (ms):

Dataset | UCB C++ | Our C++ | Gunrock
------------ | ------------- | ------------ | ------------- 
ak2010 | 97.99 | 72.08 | 3.04
belgium_osm | 2270 | 1663 | 2.97
cit-Patents | 40574 | 22148 | 16.41
coAuthorsDBLP | 1004 | 1399 | 4.86
delaunay_n13 | 21.52 | 16.33 | 2.86
delaunay_n21 | 5733 | 4084 | 2.98
delaunay_n24 | 49299 | 34655 | 3.28
europe_osm | 97022 | 72973 | 2.95
hollywood-2009 | 43024 | 30430 | 46.30
indochina-2004 | 101877 | 71902 | 11.05
kron_g500-logn21 | 110309 | 89438 | 627.55
roadNet-CA | 3403 | 2475 | 3.03
road_usa | 48232 | 31617 | 3.01
soc-LiveJournal1 | 63151 | 37936 | 19.29
soc-orkut | 111391 | 89752 | 18.05

### Performance limitations

We profiled the primitives while running `kron_g500-logn21`. The profiler adds ~100ms of overhead (728.48ms with profiler vs. 627.55ms without profiler). The breakdown looks like

Gunrock Kernel | Runtime (ms) | Percentage
------------ | ------------- | ------------
Advance (EdgeMap) | 566.76 | 77.8%
Filter (VertexMap) | 10.85 | 1.49%
ForAll (VertexMap) | 2.90 | 0.40%
Other | 147.89 | 20.3%

Note: "Other" includes HtoD and DtoH memcpy, smaller kernels such as scan, reduce, etc.

By profiling the LB Advance kernel, we find that the performance of Advance is bottlenecked by random memory accesses. In the first part of the computation --getting row pointers and column indices--memory accesses can be coalesced and the profilers says we perform 4.9 memory transactions per access, which is close to the ideal of 4. However, once we start processing these neighbors, the memory access becomes random and we perform 31.2 memory transactions per access.

## Next Steps

### Alternate approaches

This can also be implemented in GraphBLAS, which is currently being worked on.

### Gunrock implications

The experience of implementing this application using Gunrock was straightforward. The `ForAll` and `ForEach` operators were very useful for this application.

### Notes on multi-GPU parallelization

Since this problem maps well to Gunrock operations, we expect parallelization to be similar to BFS and SSSP. The dataset can be effectively divided across multiple GPUs. 

### Notes on dynamic graphs

N/A

### Notes on larger datasets

If the data were too big to fit into the aggregate GPU memory of multiple GPUs on a single node, then we would need to look at multiple node solutions. Getting the application to work on multiple nodes would not be challenging, because it is very similar to BFS. However, optimizing it to achieve good scalability may require asynchronous communication, which we have experience with (see [Pan et al.](https://arxiv.org/pdf/1803.03922.pdf)).

### Notes on other pieces of this workload

N/A

### How this work can lead to a paper publication

This work can lead to a paper publication, because the coordinate descent implementation by Ben shows that Gunrock can be used as a coordinate descent solver. There have been more interest in coordinate descent recently, because coordinate descent can be used in ML as an alternative to stochastic gradient descent for SVM training. 

Reference: Prof. Cho-Jul Hsieh from UC Davis is an expert in this field (see [1](http://www.jmlr.org/proceedings/papers/v37/hsieha15-supp.pdf), [2](https://www.semanticscholar.org/paper/HogWild%2B%2B%3A-A-New-Mechanism-for-Decentralized-Zhang-Hsieh/183d421bfb807378bd0463894415f40e0fca64d6), [3](http://www.stat.ucdavis.edu/~chohsieh/passcode_fix.pdf)).
