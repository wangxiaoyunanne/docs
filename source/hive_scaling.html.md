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
scheme should still work. The marginal performance improvement by using more GPUs
may be insignificant at this scale, and a small number of applications might even see
performance decreases with some datasets. However, the 1D partitioning makes
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

## Community Detection (Louvain)

The main and most time consuming part of the Louvain algorithm is the
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
    local_weights_community2any := sums(local edges from an community);
    weights_community2any := AllReduce(local_weights_community2any, sum);
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
temp_graph := Contract the local sub-graph based on community assignments;
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

| Parts                   | Comp. cost | Comm. cost    | Comp. to comm. ratio | Scalability | Memory usage |
|-------------------------|------------------|-----------|-----------------|------|--------------------------|
| Modularity optimization | 10(E + V) /p     | 20V bytes | E/p : 2V        | Okay | 88E/p + 12V bytes        |
| Graph contraction       | 5E / p + E'      | 8E' bytes | 5E/p + E' : 8E' | Hard | 16E' bytes               |
| Louvain                 | 10(E + V) / p    | 20V bytes | E/p : 2V        | Okay | 88E/p + 12V + 16E' bytes |

Louvain could be hard to implement on multiple GPUs, but the scalability should
okay.

## Graph SAGE

The main memory usage and computation of SAGE are related to the features of
vertices. While directly accessing the feature data of neighbors via. peer
access is possible and memory efficient, it will create a huge amount of
inter-GPU traffic that makes SAGE unscalable in terms of running time. Using
UVM to store the feature data is also possible, but that will move the traffic
from inter-GPU to the GPU-CPU connection, which is even less desirable. Although
there is a risk of using up the GPU memory, especially on graphs that have high
connectivity, a more scalable way is to duplicate the feature data of neighboring
vertices. Depending on the graph size and the size of features, not all of the
above data distribution schemes are applicable. The following analysis focuses
on the feature duplication scheme, with other schemes' result in the summary
table.

SAGE can be separated into three parts, depending on whether the computation
and data access is source-centric or child-centric.
```
// Part1: Select the children
For each source in local batch:
    Select num_children_per_source children form source's neighbors;
    Send <source, child> pairs to host_GPU(child);

// Part2: Child-centric computation
For each received <source, child> pair:    
    child_feature = feature[child];
    send child_feature to host_GPU(source);

    feature_sums := {0};
    For i from 1 to num_leafs_per_child:
        Select a leaf from child's neighbors;
        leafs_feature += feature[leaf];
    child_temp = L2_normalize( concatenate(
        feature[child] * Wf1, leafs_feature * Wa1));
    send child_temp to host_GPU(source);

// Part3: Source-centric computation
For each source in local batch:
    children_feature := sum(received child_feature);
    children_temp := sum(received child_temp);
    source_temp := L2_normalize( concatenate(
        feature[source] * Wf1, children_feature * Wa1));

    source_result := L2_normalize( concatenate(
        source_temp * Wf2, children_temp * Wa2));
```

Assume the size of local batch is B, the number of children per source is C,
the number of leafs per child is L, and the feature length per vertex is F.
Dimensions of 2D matrices are noted as (x, y). The
computation and communication costs for each part are:

Part 1, computation  : B x C. <br>
Part 1, communication: B x C x 8 bytes. <br>
Part 2, computation  : B x C x F + B x C x (F + L x F + F x (Wf1.y + Wa1.y)).<br>
Part 2, communication: B x C x (F + Wf1.y + Wa1.y) x 4 bytes.<br>
Part 3, computation  : B x (C x (F + Wf1.y + Wa1.y) + F x (Wf1.y + Wa1.y) + (Wf1.y + Wa1.y) x (Wf2.y + Wa2.y)). <br>
Part 3, communication: 0 byte.

For Part 2's communication, if C is larger than about 2p, using `AllReduce` to
sum up child\_feature and child\_temp for each source will cost less, at B x (F + Wf1.y + Wa1.y) x 2p x 4 bytes.

*Summary of Graph SAGE multi-GPU scaling*

| Parts                 | Comp. cost | Comm. cost    | Comp. to comm. ratio | Scalability | Memory usage |
|-----------------------|------------|---------------|----------------------|-------------|--------------|
| *Feature duplication* | | | | | |
| Children selection    | BC | 8BC bytes | 1 : 8 | Poor | |
| Child-centric comp.   | BCF x (2 + L + Wf1.y + Wa1.y) | 4B x (F + Wf1.y + Wa1.y) x min(C, 2p) bytes | \~ CF : min(C, 2p) x 4 | Good | |
| Source-centric comp.  | B x (CF + (Wf1.y + Wa1.y) x (C + F + Wf2.y + Wa2.y) | 0 bytes | N.A. | N.A. | |
| Graph SAGE            | B x (C + 3CF + 3LCF + (Wf1.y + Wa1.y) x (CF + C + F + Wf2.y + Wa2.y)) | 8BC + 4B x (F + Wf1.y + Wa1.y) x min(C, 2p) bytes | at least \~ CF : min(C, 2p) x 4 | Good | |
| | | | | | |
| *Direct feature access* | | | | | |
| Child-centric comp.   | BCF x (2 + L + Wf1.y + Wa1.y) | 4B x ((F + Wf1.y + Wa1.y) x min(C, 2p) + CLF) bytes | \~ (2 + L + Wf1.y + Wa1.y) : 4L | poor | |
| Graph SAGE            | B x (C + 3CF + 3LCF + (Wf1.y + Wa1.y) x (CF + C + F + Wf2.y + Wa2.y)) | 8BC + 4B x (F + Wf1.y + Wa1.y) x min(C, 2p) + 4BCFL bytes | \~ (2 + L + Wf1.y + Wa1.y) : 4L | poor | |
| | | | | | |
| *Feature in UVM*      | | | | | |
| Child-centric comp.   | BCF x (2 + L + Wf1.y + Wa1.y) | 4B x (F + Wf1.y + Wa1.y) x min(C, 2p) bytes over GPU-GPU + 4BCLF bytes over GPU-CPU | \~ (2 + L + Wf1.y + Wa1.y) : 4L over GPU-CPU | very poor | |
| Graph SAGE            | B x (C + 3CF + 3LCF + (Wf1.y + Wa1.y) x (CF + C + F + Wf2.y + Wa2.y)) | 8BC + 4B x (F + Wf1.y + Wa1.y) x min(C, 2p) bytes over GPU-GPU + 4BCFL bytes over GPU-CPU | \~ (2 + L + Wf1.y + Wa1.y) : 4L over GPU-CPU | very poor | |

When the number of features are at least several tens, the computation workload
will be much more than communication, and SAGE should have good scalability.
Implementation should be easy, as only simple p2p or AllReduce communication
models are used. If memory usage is an issue, falling back to peer-access or
UVM will resulted in very poor scalability; problem segmentation (i.e. only
process portion of the graph at a time) may be necessary to have a scalable
implementation for large graphs, but that will be quite complex.

## Random walks

If the graph can be duplicated on each GPUs, the random walk multi-GPU
implementation is trivial: just do a subset of the walks on each GPU. The
scalability will be perfect, as there is no communication involved at all.

A more interesting multi-GPU implementation would be when the graph is
distributed across the GPUs. In this case, each step of a walk not only needs
to send the <walk#, step#, v> information to host\_GPU(v), but also to the GPU that
stores the result for such walk.
```
For each walk starting from local vertex v:
    Store v for <walk#, step 0>;
    Select a neighbor u of v;
    Store u for <walk#, step 1>;
    Send <walk#, 1, u> to host_GPU(u) for visit;

Repeat until all steps of walks finished:
    For each received <walk#, step#, v> for visit:
        Select a neighbor u of v;
        Send <walk#, step# + 1, u> to host_GPU(u) for visit;
        Send <walk#, step# + 1, u> to host_GPU_walk(walk#) for record;

    For each received <walk#, step#, v> for record:
        Store v for <walk#, step#>;
```

Using W as the number of walks, for each step, we have

| Parts                 | Comp. cost | Comm. cost    | Comp. to comm. ratio | Scalability | Memory usage |
|-----------------------|------------|---------------|----------------------|-------------|--------------|
| Random walk           | W/p        | W/p x 24 bytes| 1 : 24               | very poor   | |

If the selection of neighbor is weighted random, instead of uniformly random,
it will increase the computation workload to Wd /p, where d is the average
degree of vertices in the graph. As a result, the computation to communication
ratio will increase to d : 24; for most graphs, it's still not high enough to
have good scalability.

## Geo Location

In each iteration, Geo updates a vertex's location based on its neighbors. For
multiple GPUs, neighboring vertices's location information need to be
available, either by direct access, UVM, or explicit data movement. The following
shows how explicit data movement can be implemented.
```
Do
    Local geo location updates on local vertices;
    Broadcast local vertices' updates;
While no more update
```

The computation cost is in the order of O(|E|/p), if each iteration all
vertices are looking for possible location updates from neighbors. Because the
spatial median function has a lot of mathematical computation inside,
particularly a haversine() for each edge, the constant factor hidden by O() is
large; for simplicity, 100 is used as the constant factor here. Assuming
broadcasting every vertex's location gives the upper bound of communication,
but in reality, the communication should be much less: 1) not every vertex
updates location every iteration; 2) vertices may not have neighbors on each
GPUs, so instead of broadcast, p2p communication may be used to reduce the
communication cost, especially when the graph connectivity is low.

| Comm. method          | Comp. cost | Comm. cost    | Comp. to comm. ratio | Scalability | Memory usage |
|-----------------------|------------|---------------|----------------------|-------------|--------------|
| Explicit movement     | 100E/p     | 2V x 8 bytes  | 25E/p : 4V           | Okay        | |
| UVM or peer access    | 100E/p     | E/p x 8 bytes | 25 : 1               | Good        | |

## Vertex Nomination

Vertex nomination is very much a single source shortest path (SSSP) problem,
except it starts from a group of vertices, instead of a single source. One
multi-GPU implementation is as following:
```
Set the starting vertex / vertices;
While has new distance updates
    For each local vertex v with distance update:
        For each edge <v, u, w> of vertex v:
            new_distance := distance[v] + w;
            if (distance[u] > new_distance)
                distance[u] = new_distance;

    For each u with distance update:
        Send <u, ditance[u]> to host_GPU(u);
```

Assuming on average, each vertex has its distance updated a times, and the
average degree of vertices is d, the compuation and the communication costs are:

| Parts                 | Comp. cost | Comm. cost    | Comp. to comm. ratio | Scalability | Memory usage |
|-----------------------|------------|---------------|----------------------|-------------|--------------|
| Vertex nomination     | aE/p       | aV/p x min(d, p) x 8 bytes | E : 8V x min(d, p) | Okay | | 

The min(d, p) part in the communication cost comes from update aggretion on
each GPU: when a vertex has more than one distance updates, only the smallest
is sent out; for a vertex that has a lot of neighbors and neighboring to all
GPUs, its communication cost is capped by p x 8 bytes. 

## Summary of Results

| Application | Computation to communication ratio | Scalability | Implementation difficulty |
|-------------|----------------|------|------|
| Louvain     | E/p : 2V       | Okay | Hard |
| Graph SAGE  | \~ CF : min(C, 2p)x4 | Good | Easy |
| Random walk | Duplicated graph: infinity<br> Distributed graph: 1 : 24 | Perfect <br> Very poor | Trivial <br> Easy |
| Geo location| Explicit movement: 25E/p : 4V<br> UVM or peer access: 25 : 1 | Okay <br> Good | Easy |
| Vertex nomination | E : 8V x min(d, p) | Okay | Easy |

