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
APB_num_entries=659238
counter=17
run_num=0 | h_numAssign=4096 | milliseconds=21.3737
APPB_trace = 196
APTB_trace = 7760
ATPB_trace = 7760
ATTB_trace = 109460
ps_grad_P  = 393620
ps_grad_T  = 16124208
ps_gradt_P = 407896
ps_gradt_T = 15879704
alpha      = -29.4213314
falpha     = 224003776
f1         = -15486084
num_diff   = 448756
------------
f1 < 0
iter_timer=74.0615005
===== iter=1 ================================
APB_num_entries=13466405
counter=1
run_num=0 | h_numAssign=4096 | milliseconds=5.72806406
APPB_trace = 109460
APTB_trace = 189910
ATPB_trace = 189910
ATTB_trace = 333838
ps_grad_P  = 15879704
ps_grad_T  = 16201504
ps_gradt_P = 16201504
ps_gradt_T = 16777216
alpha      = 2.26736832
falpha     = -1305351
f1         = -897512
num_diff   = 0
------------
f1 < 0
iter_timer=50.2999039
===== iter=2 ================================
APB_num_entries=13464050
counter=1
run_num=0 | h_numAssign=4096 | milliseconds=5.71267223
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
iter_timer=45.222271
total_timer=170.153473 | num_diff=0
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

At the moment, the primary scaling bottleneck is that we allocate a `|V|x|V|` array as part of the auction algorithm.  This could be replaced w/ 2 `|E|` arrays without much trouble.

Currently, the auction algorithm does not take advantage of all of available parallelism.  Each thread gets a row of the cost matrix, and then does a serial reduction across the entries of the row.  As the auction algorithm runs, the number of "active" rows rapidly decreases.  This means that the majority of auction iterations have a small number of active rows, and thus use a small number of GPU threads.  We could better utilize the GPU by doing the reductions in parallel across rows.  We have a preliminary implementation of this using the CUB library, but it has not been tested on various edge cases. Preliminary experiments suggest the CUB implementation of the auction algorithm may be substantially faster than the current implementation (roughly 2-5x)

SGM is only appropriate for pairs of graphs w/ some kind of correspondence between the nodes.  This could be an explicit correspondance (users on Twitter and users on Instagram, people in a cell phone network and people on an email network), or an implcit correspondence (two people play similar roles at similar companies).

### Comparison against existing implementations

#### Python SGM code

The [original SGM implementation](https://github.com/youngser/VN/) is a single-threaded R program.  Preliminary tests on small graphs show that this implementation is not very performant.  As part of other work, we've written a [modular SGM package](https://github.com/bkj/sgm) that allows the programmer to plug in different backends for the LSAP solver and the linear algebra operations.  This package includes modes that transform the SGM problem to take advantage of sparsity to improve runtime.  In particular, we benchmark our CUDA SGM implementation against the `scipy.sparse.jv` mode, which uses `scipy` for linear algebra and the [gatagat/lap](https://github.com/gatagat/lap) implementation of the JV algorithm for the LSAP solver.

#### Experiments

##### Connectome

The connectome graphs are generated from brain MRIs.  Nodes represent a voxel in the image and edges indicate some kind of flow between parts of the brain. Each of the graphs represents one hemishpere of the brain -- therefor, we expect there to be an actual correspondence between nodes. By binning at different spatial resolutions, the researchers graphs at a variety of sizes.  Note that these graphs are already partially aligned -- the distance between the input graphs is far smaller than would be expected by chance.

The size of the graphs are as follows:

| name    | num_nodes | num_edges |
| ------- | --------- | --------- |
| DS00833 | 00833   |   12497   | 
| DS01216 | 01216   |   19692   | 
| DS01876 | 01876   |   34780   | 
| DS03231 | 03231   |   64662   | 
| DS06481 | 06481   |  150012   | 
| DS16784 | 16784   |  445821   | 
| DS72784 | 72784   | 2418304   | 

Python runtimes:

| name    | orig_dist | final_dist | time_ms | 
| -------- | --------- | ---------- | -------- |
| DS00833 | 11650.0 | 11486.0 | 122.65658378601074 |
| DS01216 | 20004.0 | 19264.0 | 278.73969078063965 |
| DS01876 | 38228.0 | 36740.0 | 2275.141954421997 |
| DS03231 | 78058.0 | 73282.0 | 8900.371313095093 |
| DS06481 | 201084.0 | 183908.0 | 97658.3788394928 |
| DS16784 | 677754.0 | 593590.0 | 920436.3875389099 |

CSGM runtimes: 

| eps | name      | orig_dist | final_dist | time_ms    | speedup  |
| --- | --------- | --------- | ---------- | ---------- | ----- |
| 1.0 |  DS00833  | 11650  | 11538   | 181.481 | 0.6    | 
| 1.0 |  DS01216  | 20004  | 19360   | 324.908 | 0.8    | 
| 1.0 |  DS01876  | 38228  | 36936   | 807.148 | 2.8    | 
| 1.0 |  DS03231  | 78058  | 73746   | 3078.78 | 2.9    | 
| 1.0 |  DS06481  | 201084 | 184832  | 9056.55 | 10.7   | 
| 1.0 |  DS16784  | 677754 | 596370  | 42220.5 | 21.8   | 
| 1.0 |  DS72784  |  x     |   x     | OOM     |  x     | 
| 0.5 |  DS00833  | 11650  | 11466   | 378.056 | 0.3 *  |
| 0.5 |  DS01216  | 20004  | 19288   | 965.915 | 0.3    | 
| 0.5 |  DS01876  | 38228  | 36764   | 1258.65 | 1.8    | 
| 0.5 |  DS03231  | 78058  | 73346   | 6257.87 | 1.4    | 
| 0.5 |  DS06481  | 201084  | 183796 | 25931.2 | 3.7 *  |
| 0.5 |  DS16784  | 677754  | 592822 | 120799  | 7.6 *  |
| 0.5 |  DS72784  |   x     |   x    | OOM     |   x    | 

We run CSGM w/ two values of `eps`, which controls the precision of the auction algorithm (lower values = more precise but slower).  For small graphs (`|U| < ~2000`) the Python implementation is faster.  However, as the size of the graph grows, CSGM becomes significantly faster -- up to 20x faster in the low accuracy setting and up to 7.6x faster in the higher accuracy setting.  Also, though in general the auction algorithm does not compute exact solutions to the LSAP, in several cases CSGM's accuracy outperforms the Python implementation, which uses an exact LSAP solver.

### Performance limitations

- Results from profiling indicate that these kernels are memory latency bound.
- 50% of time is spent in sparse-sparse matrix-multiply (SpMM)
- 39% of time is spent in the auction algorithm. Of this 39%:
  - 65% of time is spent in `run_bidding`
  - 26% of time is spent in `cudaMemset`
  - 9% of time is spent in `run_assignment`

## Next Steps

### Alternate approaches

It would be worthwhile to look into parallel versions of the Hungarian or JV algorithms, as even a single-threaded CPU version of those algorithms is somewhat competitive with Bertseka's auction algorithm implemented on the GPU.  It's unclear whether it would be better to implement parallel JV/Hungarian as multi-threaded CPU programs or GPU programs.  If the former, SGM would be a good example of an application that makes good use of both the CPU (for LSAP) and GPU (for SpMM) at different steps.

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
