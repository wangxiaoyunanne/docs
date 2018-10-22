---
title: Vertex Nomination (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Vertex Nomination

The `VertexNomination` workflow is an implementation of the kind of algorithms discussed in [Coppersmith and Priebe](https://arxiv.org/abs/1201.4118).  Often, we have an attributed graph where we know of some "interesting" nodes, and we want to rank the rest of the nodes by their likelihood of being "interesting".  Coppersmith and Priebe propose using both node attributes (eg "content") and network features (eg "context") to rank nodes. The specific content, context and fusion functions can be arbitrary, user-defined functions.

## Summary of Gunrock Implementation

Since HIVE is focused on graph analytics, the content scoring function is not relevant, and we only implement the context scoring function.  Coppersmith and Priebe propose a number of possible network statistics that could be used for context scoring, but the [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/vertex_nomination_Enron/blob/master/snap_vertex_nomination.py) ranks each node `u` in a graph `G = (U, E)` by the minimum distance from `u` to a node in a set of seed nodes `S`.  This is the VN variant we have implemented in Gunrock.  This choice of scoring function ends up being very close to a single source shortest paths (SSSP) problem, but instead of starting from a single node, we start from the set of seeds nodes `S`.

Because of the similarity to SSSP, the [Gunrock VN implementation](https://github.com/gunrock/gunrock/tree/dev-refactor/tests/vn) consists of a minor modification to the [Gunrock SSSP implementation](https://github.com/gunrock/gunrock/tree/dev-refactor/tests/sssp), so that it can accept a list of source nodes instead of a single source node.  Thus, the core of the VN algorithm is a Gunrock advance operator implementing a parallel version of Djikstra's algorithm.  Specifically, in `python`:

```
class IterationLoop(BaseIterationLoop):
    def _advance_op(self, src, dest, problem, enactor_stats):
        src_distance = problem.distances[src]
        edge_weight  = problem.edge_weights[(src, dest)]
        new_distance = src_distance + edge_weight
        
        old_distance = problem.distances[dest]
        problem.distances[dest] = min(old_distance, new_distance)
        
        return new_distance < old_distance
        
    def _filter_op(self, src, dest, problem, enactor_stats):
        if problem.labels[dest] == enactor_stats['iteration']:
            return False
        
        problem.labels[dest] = enactor_stats['iteration']
        return True
```

Note we could have used the Gunrock SSSP implementation directly by
 a) adding a dummy node `d` to `G`; then
 b) adding an edge `(d, s)` between `d` and each node `s` in `S` with weight 0; then
 c) running SSSP from `d`

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

```bash
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock/tests/vn
cp ../../gunrock/util/gitsha1.c.in ../../gunrock/util/gitsha1.c
make clean
make
```

### Application specific parameters
```
--src
 Comma separated list of seed nodes (eg, `0,1,2`)
```

### Example command

```bash
./bin/test_vn_9.1_x86_64 \
    --graph-type market \
    --graph-file ../../dataset/small/chesapeake.mtx \
    --src 0,1,2
```

### Example output
```
Loading Matrix-market coordinate-formatted graph ...
  Reading from ../../dataset/small/chesapeake.mtx:
  Parsing MARKET COO format (39 nodes, 170 directed edges)...   Done (0 s).
  Writing meta data into ../../dataset/small/chesapeake.mtx.meta
  Writting edge pairs in binary into ../../dataset/small/chesapeake.mtx.coo_edge_pairs
  Assigning 1 to all 170 edges
  Substracting 1 from node Ids...
  Edge doubleing: 170 -> 340 edges
  graph loaded as COO in 0.052936s.
Converting 39 vertices, 340 directed edges ( ordered tuples) to CSR format...Done (0s).
Degree Histogram (39 vertices, 340 edges):
    Degree 0: 0 (0.000000 %)
    Degree 2^0: 0 (0.000000 %)
    Degree 2^1: 1 (2.564103 %)
    Degree 2^2: 22 (56.410256 %)
    Degree 2^3: 13 (33.333333 %)
    Degree 2^4: 2 (5.128205 %)
    Degree 2^5: 1 (2.564103 %)

Computing reference value ...
srcs_vector | num_srcs=3
test_vn srcs[i]=0
test_vn srcs[i]=1
test_vn srcs[i]=2
__________________________
CPU num_srcs=3
--------------------------
Run 0 elapsed: 0.007153 ms, srcs = 0,1,2
==============================================
 mark-pred=0 advance-mode=LB
Using advance mode LB
Using filter mode CULL
__________________________
--------------------------
Run 0 elapsed: 0.319004 ms, srcs = 0,1,2, #iterations = 3
Distance Validity: PASS
First 40 distances of the GPU result:
[0:0 1:0 2:0 3:2 4:2 5:2 6:1 7:1 8:1 9:2 10:1 11:1 12:1 13:1 14:1 15:1 16:1 17:1 18:2 19:2 20:2 21:1 22:1 23:2 24:2 25:2 26:2 27:2 28:2 29:2 30:2 31:2 32:2 33:1 34:1 35:1 36:1 37:2 38:1 ]
First 40 distances of the reference CPU result.
[0:0 1:0 2:0 3:2 4:2 5:2 6:1 7:1 8:1 9:2 10:1 11:1 12:1 13:1 14:1 15:1 16:1 17:1 18:2 19:2 20:2 21:1 22:1 23:2 24:2 25:2 26:2 27:2 28:2 29:2 30:2 31:2 32:2 33:1 34:1 35:1 36:1 37:2 38:1 ]

[vn] finished.
 avg. elapsed: 0.319004 ms
 iterations: 3
 min. elapsed: 0.319004 ms
 max. elapsed: 0.319004 ms
 rate: 1.065817 MiEdges/s
 src: 1
 nodes_visited: 39
 edges_visited: 340
 load time: 117.792 ms
 preprocess time: 955.240000 ms
 postprocess time: 0.524998 ms
 total time: 956.246138 ms
```

### Expected Output

Currently, the VN app does write any output to disk. It prints runtime statistics and the results of a correctness check.  A successfuly run will print 
```
Distance Validity: PASS
```
in the output.

## Validation

The Gunrock VN implementation was tested against the [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/vertex_nomination_Enron/blob/master/snap_vertex_nomination.py) to verify correctness.  We also implemented a CPU reference implementation inside of the Gunrock VN app, with results that match the HIVE reference implementation.  Also, for ease of exposition, we implemented a [pure Python version of the app](https://github.com/gunrock/pygunrock/blob/master/apps/vn.py) that lets people new to Gunrock see the relevant logic without all of the complexity of C++/CUDA data structures, memory management, etc.

## Performance and Analysis

Performance is measured by the runtime of the app, given:
 - an input graph
 - a set of seed nodes

### Other implementations

#### Python reference implementation

The Python+SNAP reference implementation can be found [here](https://gitlab.hiveprogram.com/ggillary/vertex_nomination_Enron/blob/master/snap_vertex_nomination.py).  This is a very naive implementation of the context function -- instead of running the SSSP variant we describe above, it runs a separate BFS from each node `s` in the seed set `S` to each node `u` in `U`.  Thus, it's algorithmic complexity is aproximately `|S|x|U|` times larger than the Gunrock implementation. 

#### Performer OpenMP implementation

We were unable to locate any C/OpenMP implementation of VN from TA1/TA2 performers.

#### Gunrock CPU implementation

For correctness checking, we implement VN via the SSSP variant described above in C++ within the Gunrock testing framework.  This is a serial implementation of Djikstra's algorithm using a CSR graph representation and `std::priority_queue`.  We expect this to be substantially faster than the HIVE reference implementation due to improved algorithmic complexity.

#### Experiments 

##### HIVE Enron dataset

The Enron graph is a graph of email communications between employees of Enron, w/ `|U|=15056` and `|E|=57075`.


This implementation does 10 runs w/ 5 random seeds each on the [Enron email dataset](https://hiveprogram.com/data/_v0/vertex_nomination_and_scan_statistics/).  Runtimes (in ms) are as follows:
```
3326.16
3435.40
3509.23
3738.28
3791.98
3920.63
3951.03
4239.80
4371.74
6871.20
```

#### Our CPU reimplementation

### Implementation limitations

__TODO__
Size of dataset that fits into GPU memory (what is the specific limitation?)

The Gunrock VN algorithm works on weighted/unweighted directed/undirected graphs.  No particular graph topology or node/edge metadata is required.  In general, vertex nomination is run on graphs with node/edge attributes, but since the Gunrock implementation only implements the graph analytic portion of the workflow, we are not subject to those restrictions.

### Comparison against existing implementations

The HIVE reference implementation is implemented via the [SNAP python bindings](https://snap.stanford.edu/snappy/), which runs Djikstra's from each node in the seed set to each node in the graph.  Thus it's algorithmic complexity is approximately `|S| * |V|` times larger than the Gunrock implementation, where `|S|` is the size of the seed set and `|V|` is the number of vertices in the graph.  On the reference Enron dataset, the python SNAP implementation takes > 4 seconds while the Gunrock implementation takes approximately 1ms.

There is no HIVE OpenMP implementation of `VertexNomination` at this time (2018-09-25).

This instantiation of VN is a deterministic algorithm, so all correct solutions have the same accuracy/quality.

### Performance limitations

__TODO__

## Next Steps

### Alternate approaches/further work

Given more time, we could implement more variations on context similiarity as described in Coppersmith and Priebe's paper.

### Gunrock implications

This was a fairly straightforward adapatation of an existing Gunrock app.  SSSP is also one of the simpler apps -- only one advance/filter operation without a ton of logic -- so implementing VN was not very difficult. 

### Notes on multi-GPU parallelization

__TODO__
What will be the challenges in parallelizing this to multiple GPUs on the same node?

__TODO__
Can the dataset be effectively divided across multiple GPUs, or must it be replicated?

### Notes on dynamic graphs

The reference implementation does not cover a dynamic graph version of this workflow, though one could imagine having a static set of seed nodes and a streaming graph on which you'd like to compute context scores in real time.

### Notes on larger datasets

<TODO> What if the dataset was larger than can fit into GPU memory or the aggregate GPU memory of multiple GPUs on a node? What implications would that have on performance? What support would Gunrock need to add?

### Notes on other pieces of this workload

The context scoring component of vertex nomination is incredibly general, and could include versions ranging in complexity from simple Euclidean distance metrics to the output of complex deep learning pipelines.  If we were to integrate these kinds of components more closely w/ Gunrock, we'd likely need to use other CUDA libraries (cuBLAS; cuDNN) as well as interface w/ higher level machine learning libraries (tensorflow, pytorch, etc)
