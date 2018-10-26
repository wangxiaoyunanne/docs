---
title: Scaling analysis for Hive applications

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

The purpose of this document is to understand how the Hive applications would
scale out on multiple GPUs, with the focus on tarting the DGX-1 platform.
Before diving into per application analysis, a brief summary of the potential
hardware platforms, the communication methods and models, and graph
partitioning schemes will be given.

# Hardware platforms

There are at least three kinds of potential multi-GPU platforms the Hive apps
can run on. They have different GPU-communication properties, and that may
affect the choice of communication models and / or graph partitioning schemes,
thus may have different scaling results.

## DGX-1

## DGX-2

## GPU clusters

# Communication methods / models

## Explicit data movement

### Peers to host GPU

### Host GPU to peers

### All reduce

### Mix all reduce with peers to host GPU or host GPU to peers

# Graph partitioning scheme

## 1D partitioning

## 2D partitioning

## High / low degree partitioning

# Scaling of the Hive applications

As the target platform DGX-1 has 8 GPUs. Although that's more than people
normally used for single scaling studies, the simple 1D graph partitioning
scheme should still work. The marginal performance benific by using more GPUs
may be insignificant at this scale, and a small number of applications might even see
performance degration with some datasets. However, the 1D partitioning makes
the scaling analysis simple and easily understandable. If other partitioning
scheme could work better for a specific application, it would be noted.

## How scalings are considered

The bandwidth of NVLink is much faster than PCIe 3.0: 20 x 3 and 25 x 6 GBps
bidirectional for each Tesla P100 and V100 GPUs respectively in an DGX-1. But
compared to the several TFLOPs computing power and several hundred GBps device
bandwidth, the inter-GPU bandwidth is still considerably less. For any
application to have a good scalability, the communication time should be able
to: 1) hidden by overlapping with computation, or 2) kept as a small portion as
the computation. The computation to communication ratio is a good indicator to
predict the scalability: higher ratio means better scalability. Specific to the
DGX-1 system with P100 GPUs, a ratio larger than about 10 to 1 is expected for
an app to have okay-ish scalability. With GPUs newer than P100, the computation
power and memory bandwidth improve faster than the inter connects, the compute
to communicate ratio needs to be higher to start seeing positive scaling.

## Louvain

The main part and most time consuming of the Louvain algorithm is the
modularity optimization iterations. The aggregated edge weights between
vertices and their respective adjacent communities, as well as the out-going
edge weights of each community, are needed for the modularity optimization. The
vertex-community weights can be computed locally, if the community assignments
of all neighbors of local vertices are available; to achieve this, a vertex
needs to broadcast its new community when the assignment changes. The
per-community out-going edge weights can be computed by `AllReduce` across all
GPUs. The modularity optimization with inter-GPU communication can be done as:

```
Do
    Local modularity optimization;
    Broadcast updated community assignments of local vertices;
    local_weights_community2any <- sums(local edges from an community);
    weights_community2any <- AllReduce(local_weights_community2any, sum);
While iterations stop condition not met
```

The local computation cost is in the order of O(|E| + |V|)/p, but with a large
constant hidden by the O() notation. From experiments, the constant factor is
about 10, considering the cost of sort or the random memory access penalty of
hash table. The community assignment broadcast has a cost of |V| x 4 bytes, and
the 'AllReduce' costs 2|V| x 8 bytes. These communication costs are the upper
bound, assuming there are |V| communities, and all vertices update their
community assignments. In practice, the communication cost can be much lower,
depending on the dataset.

The graph contraction can be done as below on multiple GPUs
```
temp_graph <- Contract the local sub-graph based on community assignments;
Send edges <v, u, w> in temp_graph to host_GPU(v);
Merge received edges and form the new local sub-graph;
```

In the worst cases, assuming the number of edges in the contracted graph is
|E'|, the communication cost could be |E'| x 8 bytes, with the computation cost
at about 5|E|/p + |E'|. For most datasets, the size reduction of graph from the
contraction step is significant, so the memory needed to receive edges from the
peer GPUs is manageable; however, if |E'| is large, it can be significant and
may run out of GPU memory.

*Summary of Louvain multi-GPU scaling*

Because the modularity optimization runs multiple iterations before each graph
contraction phase, the computation and communication of modularity optimization
is dominant.

| Parts                   | Computation cost | Communication cost    | Computation to communication ratio | Scalability | Memory usage |
|-------------------------|------------------|-----------|-----------------|------|--------------------------|
| Modularity optimization | 10(E + V) /p     | 20V bytes | E/p : 2V        | Okay | 88E/p + 12V bytes        |
| Graph contraction       | 5E / p + E'      | 8E' bytes | 5E/p + E' : 8E' | Hard | 16E' bytes               |
| Louvain                 | 10(E + V) / p    | 20V bytes | E/p : 2V        | Okay | 88E/p + 12V + 16E' bytes |

Louvain could be hard to implement on multiple GPUs, but the scalability should
okay.

## Graph SAGE

## Summary of the V0 apps

| Application | Computation to communication ratio | Scalability | Implementation difficulty |
|-------------|----------------|------|------|
| Louvain     | E/p : 2V       | Okay | Hard |
