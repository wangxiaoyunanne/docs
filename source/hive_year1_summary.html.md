---
title: HIVE Year 1 Report&colon; Executive Summary

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Executive Summary

This report is located online at the following URL: <https://gunrock.github.io/docs/hive_year1_summary.html>.

Herein UC Davis produces the following three deliverables that it promised to deliver in Year 1:

1. **7--9 kernels running on a single GPU on DGX-1**. The PM had indicated that the application targets are the graph-specific kernels of larger applications, and that our effort should target these kernels. These kernels run on one GPU of the DGX-1. These kernels are in Gunrock's GitHub repository as standalone kernels. While we committed to delivering 7--9 kernels, we deliver all 11 v0 kernels.
2. **(High-level) performance analysis of these kernels**. In this report we analyze the performance of these kernels.
3. **Separable communication benchmark predicting latency and throughput for a multi-GPU implementation**. This report (and associated code, also in the Gunrock GitHub repository) analyzes the DGX-1's communication capabilities and projects how single-GPU benchmarks will scale on this machine to 8 GPUs.

Specific notes on applications and scaling follow:


**[Application Classification](https://gunrock.github.io/docs/hive_application_classification.html)** Application classification involves a number of dense-matrix operations, which did not make it an obvious candidate for implementation in Gunrock.  However, our GPU implementation using the CUDA CUB library shows substantial speedups (10-50x) over the multi-threaded OpenMP implementations.

However, there are two neighbor reduce operations that may benefit from the kind of load balancing implemented in Gunrock.  Thus, it would be useful to either expose lightweight wrappers of high-performance Gunrock primitives for easy intergration into outside projects _or_ come up with a workflow inside of Gunrock that makes programming applications with lots of non-graph operations straightforward.

**[Geolocation](https://gunrock.github.io/docs/hive_geolocation.html)** Geolocation or geotagging is an interesting parallel problem, because it is among the few that exhibits the dynamic parallism pattern within the compute. The pattern is as follows; there is parallel compute across nodes, each node has some serial work and within the serial work there are sveral parallel math operations. Even without leveraging dynamic parallelism within CUDA (kernel launches within a kernel), Geolocation performs well on the GPU environment because it mainly requires simple math operations, instead of complicated memory movement schemes. 

However, the challenge within the application is load balancing this simple compute, such that each processor has roughly the same amount of work. Currently, in gunrock, we map Geolocation using the `ForAll()` compute operator with optimizations to exit early (performing less work and fewer reads). Even without addressing load balancing issue with a complicated balancing scheme, on the HIVE datasets we achieve a 100x speedup with respect to the CPU reference code, implemented using C++ and OpenMP, and ~533x speedup  with respect to the GTUSC implementation. We improve upon the algorithm by avoiding a global gather and a global synchronize, and using 3x less memory than the GTUSC reference implementation.

**[GraphSAGE](https://gunrock.github.io/docs/hive_graphSage.html)** The vertex embedding part of the GraphSAGE algorithm is implemented in the
Gunrock framework using custom CUDA kernels, utilizing block-level
parallelism, that allow a shorter running time. For the embedding part alone, the GPU
implementation is 7.5X to 15X on P100, and 20X to 30X on V100,
faster than an OpenMP implementation using 32 threads. The GPU hardware, especially
the memory system, has high utilizations from these custom kernels. It is still
unclear how to expose block-level parallelism for more general usage in
other applications in Gunrock.

Connecting the vertex embedding with the neural network training part, and
making the GraphSAGE workflow complete, would be an interesting task for year 2.
Testing on the complete workflow for prediction accuracy and running speed will
be more meaningful.

**[GraphSearch](https://gunrock.github.io/docs/hive_graphsearch.html)** Graph search is a relatively minor modification to Gunrock's random walk application, and was straightforward to implement.  Though random walks are a "worst case scenario" for GPU memory bandwidth, we still achieve 3--5x speedup over a modified version of the OpenMP reference implementation.

The original OpenMP reference implementation actually ran slower with more threads -- we fixed the bugs, but the benchmarking experience highlights the need for performant and hardened CPU baselines.

Until recently, Gunrock did not support parallelism _within_ the lambda functions run by the `advance` operator, so neighbor selection for a given step in the walk is done sequentially.  Methods for exposing more parallelism to the programmer are currently being developed via parallel neighbor reduce functions.

In an end-to-end graph search application, we'd need to implement the scoring function as well as the graph walk component.  For performance, we'd likely want to implement the scoring function on the GPU as well, which makes this a good example of a "Gunrock+X" app, where we'd need to integrate the high-performance graph processing component with arbitrary user code.

**[Community Detection (Louvain)](https://gunrock.github.io/docs/hive_louvain.html)** The Gunrock implementation uses sort and segmented reduce to implement the
Louvain algorithm, different from the commonly used hash table mapping. The GPU
implementation is about ~1.5X faster than the OpenMP implementation, and also
faster than previous GPU works. It is still unknown whether the sort and
segmented reduce formulation map the problem better than hash table on the GPU. The
modularities resulting from the GPU implementation are within small differences
as the serial implementation, and are better when the graph is larger. A custom
hash table can potentially improve the running time. The GPU Louvain
implementation should have moderate scalability across multiple GPUs in an
DGX-1.

**[Local Graph Clustering (LGC)](https://gunrock.github.io/docs/hive_pr_nibble.html)** This variant of local graph clustering (L1 regularized PageRank via FISTA) is a natural fit for Gunrock's frontier-based programming paradigm.  We observe speedups of 2-3 orders of magnitude over the HIVE reference implementation.

The reference implementation of the algorithm was not explicitly written as `advance`/`filter`/`compute` operations, but we were able to quickly determine how to map the operations by using [a lightweight Python implementation of the Gunrock programming API](https://github.com/gunrock/pygunrock/blob/master/apps/pr_nibble.py) as a development environment.  Thus, LGC was a good exercise in implementing a non-trivial end-to-end application in Gunrock from scratch.

**[Graph Projections](https://gunrock.github.io/docs/hive_proj.html)** Because it has a natural representation in terms of sparse matrix operations, graph projections gave us an opportunity to compare ease of implementation and performance between Gunrock and another UC-Davis project, GPU [GraphBLAS](https://github.com/owensgroup/GraphBLAS).  

Overall, we found that Gunrock was more flexible and more performant than GraphBLAS, likely due to better load balancing.  However, in this case, the GraphBLAS application was substantially easier to program than Gunrock, and also allowed us to take advantage of some more sophisticated memory allocation methods available in the GraphBLAS cuSPARSE backend.  These findings suggest that addition of certain commonly used API functions to Gunrock could be a fruitful direction for further work.

**[Seeded Graph Matching (SGM)](https://gunrock.github.io/docs/hive_sgm.html)** SGM is a fruitful workflow to optimize, because the existing implementations were not written with performance in mind.  By making minor modifications to the algorithm that allow use of sparse data structures, we enable scaling to larger datasets than previously possible.

The application involves solving a linear assignment problem (LSAP) as a subproblem.  Solving these problems on the GPU is an active area of research -- though papers have been written describing high-performance parallel LSAP solvers, reference implementations are not available.  We implement a GPU LSAP solver via Bertsekas' auction algorithm, and make it available as a [standalone library](https://github.com/bkj/cbert).

SGM is an approximate algorithm that minimizes graph adjacency disagreements via the Frank-Wolfe algorithm. Certain uses of the auction algorithm can introduce additional approximation in the gradients of the Frank-Wolfe iterations.  An interesting direction for future work would be a rigorous study of the effects of this kind of approximation on a variety of different graph tolopogies.  Understanding of those dynamics could allow further scaling beyond what our current implementations can handle.

**[Vertex Nomination](https://gunrock.github.io/docs/hive_vn.html)** The term "vertex nomination" covers a variety of different node ranking schemes that fuse "content" and "context" information.  The HIVE reference code implements a "multiple-source shortest path" context scoring function, but uses a very suboptimal algorithm.  By using a more efficient algorithm, our serial CPU implementation achieves 1-2 orders of magnitude speedup over the HIVE implementation and our GPU implementation achieves another 1-2 orders of magnitude on top of that.  Implementation was straightforward, involving only a small modification to the existing Gunrock SSSP app.

