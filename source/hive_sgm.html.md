---
title: Seeded Graph Matching (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

!! Results don't replicate the reference implementation _exactly_, because the LAP solvers are not the same and do eg tiebreaking differently.

!! Have verified manually that these are mathematically the same, but you could run the experiments multiple times to verify they give the same results.  It's _possible_ there's some very subtle thing hiding in the LAP solver that _statistically_ makes one of the approaches better (eg, it's better to break ties by going with tthe node w/ larger/smaller degree).

# Seeded Graph Matching (SGM)

From [Fishkind et al](https://arxiv.org/pdf/1209.0367.pdf):
    > Given two graphs, the graph matching problem is to align the two vertex sets so as to minimize the number of adjacency disagreements between the two graphs. The seeded graph matching problem is the graph matching problem when we are first given a partial alignment that we are tasked with completing.

That is, given two graphs `A` and `B`, we seek to find the permutation matrix that maximizes the number of adjacency agreements between `A` and `PBP'`.  The algorithm they propose first relaxes the hard 0-1 constraints on `P` to the set of doubly stochastic matrices (each row and column sums to 1) and uses the Frank-Wolfe algorithm to optimize the objective function.  Finally, the relaxes solution is projected back onto the set of permutation matrices to yield a feasible solution.

## Summary of Gunrock Implementation

The SGM algorithm consists of:
 - matrix multiplications
 - solving a linear assignment problem at each iteration
 - computing the trace of matrix products (eg `trace(A.dot(B))`)

The formulation of SGM in the [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/seeded_graph_matching_brain_connectome/blob/master/sgm.py) does not take advantage of the sparsity of the problem.  This is due to two algorithmic design choices:
 - To penalize adjacency disagreements, they convert the 0s in the inputs matrices `A` and `B` to -1s
 - They initialize the solution matrix `P` to the barycenter of the polytope of doubly-stochastic matrices, which has all entries != 0.

In order to take advantage of sparsity and make SGM more suitable for HIVE analysis, we make two small modifications to the algorithm:
 - Rework the equations so we can express the objective function as a function of the sparse adjacency matrices plus some simple functions of node degree
 - Initialize `P` to a vertex of the polytope

A nice property of the Frank-Wolfe algorithm is that the number of nonzero entries in the intermediate solutions grows slowly -- after the `n`'th step, the solution is the convex combination of (at most) `n` vertices of the polytope (eg, permutation matrices).  Thus, starting from a sparse initialization point means that all of the Frank-Wolfe steps are fairly sparse.

The reference implementation uses the Jonker-Volgenant algorithm to solve the linear assignment portion.  However, the JV algorithm (and the similar Hungarian algorithm) do not admit straightforward parallel implementations.  Thus, we replace the JV algorithm with [Bertsekas' auction algorithm](http://web.mit.edu/dimitrib/www/Auction_Encycl.pdf), which is much more straightforward to parallelize.

Because SGM consists of linear algebra plus an LSAP solver, we implement it in outside of the Gunrock framework, using [a GPU GraphBLAS implementation](https://arxiv.org/abs/1804.03327) from John Owen's lab, as well as [CUDA CUB](https://nvlabs.github.io/cub/).

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

```bash
git clone --recursive https://github.com/owensgroup/csgm.git
cd csgm

# build
make clean
make

# make data (A = random sparse matrix, B = permuted version of A, except first `num-seeds` vertices)
python data/make-random.py --num-seeds 100
wc -l data/{A,B}.mtx

```

### Running the application
Command:
```bash
./csgm --A data/A.mtx --B data/B.mtx --num-seeds 100 --sgm-debug 1
```

Output:
```
===== iter=0 ================================
counter=547
run_num=0 | h_numAssign=4096 | milliseconds=469.121
APPB_trace = 196
APTB_trace = 8108
ATPB_trace = 8108
ATTB_trace = 118296
ps_grad_P  = 393620
ps_grad_T  = 16125600
ps_gradt_P = 409288
ps_gradt_T = 15915048
alpha      = -33.8060455
falpha     = 258535264
f1         = -15521428
num_diff   = 16383596
------------
timer=522.680054
===== iter=1 ================================
counter=1
run_num=0 | h_numAssign=4096 | milliseconds=3.92006397
APPB_trace = 118296
APTB_trace = 195792
ATPB_trace = 195792
ATTB_trace = 333838
ps_grad_P  = 15915048
ps_grad_T  = 16225032
ps_gradt_P = 16225032
ps_gradt_T = 16777216
alpha      = 2.27986789
falpha     = -1258906.62
f1         = -862168
num_diff   = 862168
------------
timer=39.3967361
===== iter=2 ================================
counter=1
run_num=0 | h_numAssign=4096 | milliseconds=3.91375995
APPB_trace = 333838
APTB_trace = 333838
ATPB_trace = 333838
ATTB_trace = 333838
ps_grad_P  = 16777216
ps_grad_T  = 16777216
ps_gradt_P = 16777216
ps_gradt_T = 16777216
alpha      = 0
falpha     = -1
f1         = 0
num_diff   = 0
------------
timer=35.5387535 | num_diff=0
```

__Note:__ Here, the final `num_diff` indicates that the algorithm has found a perfect match between the input graphs.

### Output

When run with `--sgm-debug 1`, we output information about the quality of the match in each iteration.  The most important number is `num_diff`, which gives the number of disagreements between `A` and `PBP'`.  `num_diff=0` indicates that SGM has found a perfect matching between `A` and `B` (no adjacency disagreements).

This implementation is validated against the [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/seeded_graph_matching_brain_connectome/blob/master/sgm.py).  Additionally, since the original reference implementation code was posted, Ben Johnson has worked with John's Hopkins to produce other (more performant) implementations of SGM, found [here](https://github.com/bkj/sgm/tree/v2).

We can also do a simple test to verify that SGM is working, by permuting a matrix and trying to match it with itself.  (This is what we did in the simple example above.)

## Performance and Analysis

Performance is primarily measured in runtime of the entire SGM procedure.  Per-iteration runtime is not meaningful, because difference iterations present dramatically more difficult LSAP instances than others.  In particular, the LSAP solver in the first iteration tends to take 10-100x longer than in subsequent iterations.

Bertsekas' auction algorithm allows us make the trade off between runtime and accuracy.  Used in a certain way, it produces the exact same answer as the JV or Hungarian algorithms.  However, with a different parameter setting, the auction algorithm may run substantically faster (>10x), at the cost of a lower quality assignment.  Since SGM is already an approximate algorithm, _we do not currently know the sensitivity of the SGM algorithm to this kind of approximation._  Running experiments to explore these tradeoffs would be an interesting direction for future research.

### Implementation limitations

Currently, our implementation of SGM only supports undirected graphs -- extension to directed graphs is mathematically straightforward, but require a bit of code refactoring.  We've only tested on unweighted graphs, but the code _should_ work on weighted graphs as well.

At the moment, the primary scaling bottleneck is that we're allocating a `|V|x|V|` array as part of the auction algorithm.  This could be replaced w/ 2 `|E|` arrays without much trouble.

SGM is only appropriate for pairs of graphs w/ some kind of correspondence between the nodes.  This could be an explicit correspondance (users on Twitter and users on Instagram, people in a cell phone network and people on an email network), or an implcit correspondence (two people play similar roles at similar companies).

### Comparison against existing implementations

<TODO>
- Reference implementation (python? Matlab?)
- OpenMP reference

Comparison is both performance and accuracy/quality.
</TODO>


### Performance limitations

- 84% of time is spent in the auction algorithm. Of this 84%:
  - 77% of time is spent in bidding
  - 23% of time is spent in assignment
- 16% of time is spent in sparse-sparse matrix-multiply, which is a memory latency bound problem

## Next Steps

### Alternate approaches

It would be worthwhile to look into parallel versions of the Hungarian or JV algorithms, as even a single-threaded CPU version of those algorithms is somewhat competitive with Berteseka's auction algorithm implemented on the GPU.  It's unclear whether it would be better to implement parallel JV/Hungarian as multi-threaded CPU programs or GPU programs.  If the former, SGM would be a good example of an application that makes good use of both the CPU (for LSAP) and GPU (for SpMM) at different steps.

### Gunrock implications

N/A

### Notes on multi-GPU parallelization

#### GraphBLAS

Multiple GPU support for GraphBLAS is on the roadmap. This will involve dividing the dataset across multiple GPUs, which can be challenging, because the primitives required (`mxm`, `mxv` and `vxm`) have optimal layouts that vary depending on data and each other. There will need to be a tri-lemma between inter-GPU communication, layout transformation and compute time for optimal vs. sub-optimal layout.

Although extending matrix-multiplication to multiple GPUs can be straightforward, doing so in a backend-agnostic fashion that abstracts away the placement (i.e. which part of matrix A goes on which GPU) from the user may be quite challenging. This can be done in two ways:
1. Manually analyze the algorithm and specify the layout in a way that is application-specific to SGM (easier, but not as generalizable)
2. Write a sophisticated runtime that will automatically build a directed acyclic graph (DAG), analyze the optimal layouts, communication volume and required layout transformations, and schedule them to different GPUs (difficult and may require additional research, but generalizable)

#### Auction algorithm

The auction algorithm can be parallelized across GPUs in several ways:
1. Move data onto single GPU and run existing auction algorithm (simple, but not scalable).
2. Bulk-synchronous algorithm: Run auction kernel, communicate, then run next iteration of auction kernel (medium difficulty, scalable).
3. Asynchronous algorithm: Run auction kernel and communicate to other GPUs from within kernel (difficult, most scalable).

### Notes on dynamic graphs

N/A

### Notes on larger datasets

If the dataset were too big to fit into the aggregate GPU memory of multiple GPUs on a node, then two directions can be taken in order to be able to tackle these larger datasets:
1. Out-of-memory: Compute using part of the dataset at a time on the GPU, and save your completed result to CPU memory. When all completed results on the CPU is ready to perform the next step, copy back to GPU (slower than distributed, but cheaper and easier to implement).
2. Distributed memory: If GPU memory of a single node is not enough, use multiple nodes. This method can be made to scale for infinitely large datasets provided the implementation is good enough (faster than out-of-memory, but more expensive and difficult).

### Notes on other pieces of this workload

N/A
