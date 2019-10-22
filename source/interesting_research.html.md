---
title: Interesting Graph Research Projects with Possible Gunrock Applicability

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2019 The Regents of the University of California.

search: false

noindex: true

full_length: true
---

# Interesting Graph Research Projects with Possible Gunrock Applicability

We may see papers during the course of our work lives that have possible applicability to Gunrock. There's three steps to making use of those:

1. Add these papers here.
2. Summarize what those papers do.
3. Ascertain with the aid of Gunrock-internals experts if these are worth pursuing (as core-Gunrock projects, as projects for new students, and/or as possible external projects). If we know they're good, we can add them to the main docs [here](https://gunrock.github.io/docs/#possible-gunrock-projects).

Your todos: Add new papers! Add your summary below for any of these! And/or add your assessment on how well it'd work in Gunrock!

## The broker queue: A fast, linearizable FIFO queue for fine-granular work distribution on the GPU

B. Kerbl, M. Kenzel, J. H. Mueller, D. Schmalstieg, and M. Steinberger, “The broker queue: A fast, linearizable FIFO queue for fine-granular work distribution on the GPU,” presented at the Proceedings of the International Conference on Supercomputing, 2018, pp. 76–85. [[doi](https://doi.org/10.1145/3205289.3205291)]

### Summary

todo

### Assessment

todo

## XBFS: eXploring Runtime Optimizations for Breadth-First Search on GPUs

A. Gaihre, Z. Wu, F. Yao, and H. Liu, XBFS: eXploring Runtime Optimizations for Breadth-First Search on GPUs. New York, New York, USA: ACM, 2019, pp. 121–131. [[doi](https://doi.org/10.1145/3183713.3183735)]


## GraphCage: Cache Aware Graph Processing on GPUs

X. Chen, “GraphCage: Cache Aware Graph Processing on GPUs,” arXiv.org, vol. cs.DC. 03-Apr-2019. [[arXiv](https://arxiv.org/abs/1904.02241v1)]

## Combining Data Duplication and Graph Reordering to Accelerate Parallel Graph Processing

V. Balaji and B. Lucia, “Combining Data Duplication and Graph Reordering to Accelerate Parallel Graph Processing,” presented at the the 28th International Symposium, New York, New York, USA, 2019, pp. 133–144. [[doi](10.1145/3307681.3326609)]

## Improving Efficiency of Parallel Vertex-Centric Algorithms for Irregular Graphs

M. M. Ozdal, “Improving Efficiency of Parallel Vertex-Centric Algorithms for Irregular Graphs,” IEEE TPDS, 2019. [[doi](https://doi.org/10.1109/TPDS.2019.2906166)]


## Optimal algebraic Breadth-First Search for sparse graphs

P. Burkhardt, “Optimal algebraic Breadth-First Search for sparse graphs.” [[arXiv](https://arxiv.org/abs/1906.03113)]


## Kaskade: Graph Views for Efficient Graph Analytics

J. M. F. da Trindade, K. Karanasos, C. Curino, S. Madden, and J. Shun, “Kaskade: Graph Views for Efficient Graph Analytics,” arXiv.org, vol. cs.DB. 12-Jun-2019. [[arXiv](https://arxiv.org/abs/1906.05162v1)]

## Synchronization-Avoiding Graph Algorithms

J. S. Firoz, M. Zalewski, T. Kanewala, and A. Lumsdaine, “Synchronization-Avoiding Graph Algorithms,” presented at the Proceedings - 25th IEEE International Conference on High Performance Computing, HiPC 2018, 2019, pp. 52–61. [[doi](https://doi.org/10.1109/HiPC.2018.00015)]

## A pattern based algorithmic autotuner for graph processing on GPUs

K. Meng, J. Li, G. Tan, and N. Sun, A pattern based algorithmic autotuner for graph processing on GPUs. PPoPP '19. New York, New York, USA: ACM, 2019, pp. 201–213. [[doi](https://dx.doi.org/10.1145/3293883.3295716)]

## When is Graph Reordering an Optimization?: Studying the Effect of Lightweight Graph Reordering Across Applications and Input Graphs

V. Balaji and B. Lucia, “When is Graph Reordering an Optimization?: Studying the Effect of Lightweight Graph Reordering Across Applications and Input Graphs,” presented at the 2018 IEEE International Symposium on Workload Characterization, IISWC 2018, 2018, pp. 203–214. [[doi](https://dx.doi.org/10.1109/IISWC.2018.8573478)]

## SEP-Graph: Finding shortest execution paths for graph processing under a hybrid framework on GPU

H. Wang, L. Geng, R. Lee, K. Hou, Y. Zhang, and X. Zhang, "SEP-Graph: Finding shortest execution paths for graph processing under a hybrid framework on GPU," Proceedings of the ACM SIGPLAN Symposium on Principles and Practice of Parallel Programming, PPOPP, 2019, pp. 38–52. [[doi](10.1145/3293883.3295733)]

## A compiler for throughput optimization of graph algorithms on GPUs

S. Pai and K. Pingali, "A compiler for throughput optimization of graph algorithms on GPUs," Proceedings of the Conference on Object-Oriented Programming Systems, Languages, and Applications, OOPSLA, 2016, vol. 2, pp. 1–19. [[doi](10.1145/2983990.2984015)]

## SHOVE ASIDE, PUSH: THE CASE FOR PULL-BASED GRAPH PROCESSING

S. R. Grossman, “SHOVE ASIDE, PUSH: THE CASE FOR PULL-BASED GRAPH PROCESSING,” Ph.D. dissertation, Stanford University Department of Electrical Engineering, Nov. 2018. [[url](https://stacks.stanford.edu/file/druid:pr584hs3251/dissertation-augmented.pdf)]

## Tigr: Transforming Irregular Graphs for GPU-Friendly Graph Processing

Amir Hossein Nodehi Sabet, Junqiao Qiu, and Zhijia Zhao. 2018. Tigr: Transforming Irregular Graphs for GPU-Friendly Graph Processing. In Proceedings of the Twenty-Third International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS '18), pp. 622–636. [[doi](https://doi.org/10.1145/3173162.3173180)]

### Summary

Preprocesses scale-free datasets to reduce irregularity by splitting high-degree nodes into sets of lower-degree nodes. This can be done virtually without modifying the underlying graph structure by adding additional virtual data structures atop it.

### Assessment (JDO)

I read this as "requiring preprocessing" but preprocessing times do not appear to be included in the results. This is an incomplete comparison.

## Low-latency graph streaming using compressed purely-functional trees

Laxman Dhulipala, Guy E. Blelloch, and Julian Shun. 2019. Low-latency graph streaming using compressed purely-functional trees. In Proceedings of the 40th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI 2019). ACM, New York, NY, USA, 918-934. [[doi](https://doi.org/10.1145/3314221.3314598)]

### Summary

Muhammad discussed this work in September with the author and thought it had interesting applications to both multi-node Gunrock and to data-structure design.

## Realtime Top-k Personalized PageRank over Large Graphs on GPUs

Shi, J., Yang, R., Jin, T., Xiao, X., Yang, Y. Realtime Top-k Personalized PageRank over Large Graphs on GPUs. Proceedings of the VLDB Endowment, 13(1):15-28, 2019. [[www](http://www.vldb.org/pvldb/vol13/p15-shi.pdf)]

### Summary

Implementation of Personalized PageRank. Can we learn something from this?

## SIMD-X: Programming and Processing of Graph Algorithms on GPUs

Hang Liu and H. Howie Huang. SIMD-X: Programming and Processing
of Graph Algorithms on GPUs. Proceedings of the 2019 USENIX Annual Technical Conference, 2019. [[www](https://www.usenix.org/system/files/atc19-liu-hang.pdf)]
