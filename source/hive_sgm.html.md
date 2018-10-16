---
title: Seeded Graph Matching (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Seeded Graph Matching (SGM)

From (Fishkind et al](https://arxiv.org/pdf/1209.0367.pdf):
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

```
git clone https://github.com/owensgroup/csgm
cd csgm

# build
export GRAPHBLAS_PATH=$HOME/path/to/GraphBLAS/ (eg /home/bjohnson/projects/davis/GraphBLAS/)
make clean
make

# make data
python data/make-random.py
wc -l data/{A,B}.mtx


```

### Running the application

<code>
include a transcript
</code>

Note: This run / these runs need to be on DARPA's DGX-1.

### Output

What is output when you run? Output file? JSON? Anything else? How do you extract relevant statistics from the output?

How do you make sure your output is correct/meaningful? (What are you comparing against?)

## Performance and Analysis

How do you measure performance? What are the relevant metrics? Runtime? Throughput? Some sort of accuracy/quality metric?

### Implementation limitations

e.g.:

- Size of dataset that fits into GPU memory (what is the specific limitation?)
- Restrictions on the type/nature of the dataset

### Comparison against existing implementations

- Reference implementation (python? Matlab?)
- OpenMP reference

Comparison is both performance and accuracy/quality.



### Performance limitations

e.g., random memory access?

## Next Steps

### Alternate approaches

If you had an infinite amount of time, is there another way (algorithm/approach) we should consider to implement this?

### Gunrock implications

What did we learn about Gunrock? What is hard to use, or slow? What potential Gunrock features would have been helpful in implementing this workflow?

### Notes on multi-GPU parallelization

What will be the challenges in parallelizing this to multiple GPUs on the same node?

Can the dataset be effectively divided across multiple GPUs, or must it be replicated?

### Notes on dynamic graphs

(Only if appropriate)

Does this workload have a dynamic-graph component? If so, what are the implications of that? How would your implementation change? What support would Gunrock need to add?

### Notes on larger datasets

What if the dataset was larger than can fit into GPU memory or the aggregate GPU memory of multiple GPUs on a node? What implications would that have on performance? What support would Gunrock need to add?

### Notes on other pieces of this workload

Briefly: What are the important other (non-graph) pieces of this workload? Any thoughts on how we might implement them / what existing approaches/libraries might implement them?
