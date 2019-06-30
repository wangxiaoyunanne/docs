# Overview

## What is _Gunrock_?
Gunrock is a stable, powerful, and forward-looking substrate for GPU-based graph-centric research and development. Like many graph frameworks, it leverages a bulk-synchronous programming model and targets iterative convergent graph computations. We believe that today Gunrock offers both the [best performance on GPU graph analytics](#results-and-analysis) as well as the [widest range of primitives](#gunrock-39-s-application-cases).

## Who may use _Gunrock_?

+ **External Interface Users:** Users interested in leveraging the external C, C++ and/or Python interfaces to call [high-performance applications and primitives](#gunrock-39-s-application-cases) (such as breadth-first search, connected components, PageRank, single-source shortest path, etc.) within Gunrock to perform graph analytics.

+ **Application Developers:** Uses interested in developing applications, primitives, and/or low-level operators for Gunrock.

+ **Graph Analytics Library Developers:** Gunrock can potentially serve as a back end for higher-level abstractions (e.g., DSLs for graph analytics, such as [GraphIt](https://graphit-lang.org/) or a front end for lower-level abstractions (e.g., Gunrock's frontier model could potentially target a [GraphBLAS](http://graphblas.org/) back end).

## Why use _Gunrock_?
-   **Gunrock has the best performance of any programmable GPU+graph library.** Gunrock primitives are an order of magnitude faster than (CPU-based) Boost, outperform any other programmable GPU-based system, and are comparable in performance to hardwired GPU graph primitive implementations. When compared to [Ligra](https://github.com/jshun/ligra), a best-of-breed CPU system, Gunrock currently matches or exceeds Ligra's 2-CPU performance with only one GPU.

    Gunrock's abstraction separates its programming model from the low-level implementation details required to make a GPU implementation run fast. Most importantly, Gunrock features powerful load-balancing capabilities that effectively address the inherent irregularity in graphs, which is a problem we must address in all graph analytics. We have spent significant effort developing and optimizing these features---when we beat hardwired analytics, the reason is load balancing---and because they are beneath the level of the programming model, improving them makes all graph analytics run faster without needing to expose them to programmers.

-   **Gunrock's data-centric programming model is targeted at GPUs and offers advantages over other programming models.** Gunrock is written in a higher-level abstraction than hardwired implementations, leveraging reuse of its fundamental operations across different graph primitives. Gunrock has a bulk-synchronous programming model that operates on a frontier of vertices or edges; unlike other GPU-based graph analytic programming models, Gunrock focuses not on sequencing *computation* but instead on sequencing *[operations](#operators) on frontier data structures*. This model has two main operations: *compute*, which performs a computation on every element in the current frontier, and *traversal*, which generates a new frontier from the current frontier. Traversal operations include *advance* (the new frontier is based on the neighbors of the current frontier) and *filter* (the new frontier is a programmable subset of the current frontier). Gunrock also currently offers segmented-intersection and neighbor-reduce operators.

    This programming model is a better fit to high-performance GPU implementations than traditional programming models adapted from CPUs. Specifically, traditional models like gather-apply-scatter (GAS) map to a suboptimal set of GPU kernels that do a poor job of capturing producer-consumer locality. With Gunrock, we can easily integrate compute steps within the same kernels as traversal steps. As well, Gunrock's frontier-centric programming model is a better match for key optimizations such as push-pull direction-optimal search or priority queues, which have been a challenge to integrate into other GPU frameworks.

-   **Gunrock supports more primitives than any other programmable GPU+graph library.** We currently support a wide variety of graph primitives, including traversal-based (breadth-first search, single-source shortest path); node-ranking (HITS, SALSA, PageRank); and global (connected component, minimum spanning tree). Many more algorithms are supported with others under active development; see [Gunrock Applications](https://gunrock.github.io/docs/#gunrock-39-s-application-cases).

-   **Gunrock's programming model scales to multiple GPUs with high performance while still using the same code as a single-GPU primitive.** Other frameworks require rewriting their primitives when moving from one to many GPUs. Gunrock's multi-GPU programming model uses single-node Gunrock code at its core so that single-GPU and multi-GPU operations can share the same codebase, and Gunrock's single- and multi-GPU performance is best-in-class.

## What does Gunrock not do?

-   Gunrock does not currently scale to multiple nodes ("scale-out"). Gunrock also does not scale to datasets that cannot fit into GPU memory ("scale-up"), for instance, datasets primarily stored in a larger CPU memory that may or may not require CPU-GPU coprocessing. Both of these problems are interesting to solve.

-   Gunrock is written in a bulk-synchronous programming model and does not currently have asynchronous capabilities.

-   Gunrock currently supports only static graph datasets; supporting dynamic graphs is an active area of current work.

-   For any given application, Gunrock's default parameters run the simplest possible Gunrock configurations and should not be used for performance comparisons. We have done no tuning of Gunrock's default parameters for performance.

-   Gunrock does no preprocessing on its datasets. Other projects have demonstrated that preprocessing datasets can deliver performance improvements. We believe this would also extend to Gunrock, but philosophically, we expect that the primary use case for Gunrock will be in pipelines of multiple stages where each stage receives an input from a previous stage, performs a computation on it, and outputs a result to the next stage. In this scenario, the previous stage's output is dynamically generated at runtime and thus not available for preprocessing. We hope that any graph libraries that do preprocessing report results with both preprocessed and unmodified input datasets.
