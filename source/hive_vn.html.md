---
title: Template for HIVE workflow report

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# VertexNomination

The `VertexNomination` workflow is an implementation of the kind of algorithms discussed in [Coppersmith and Priebe](https://arxiv.org/abs/1201.4118).  The motivation is that we often have an attributed graph where we know that some of the nodes are "interesting", and we want to rank the rest of the nodes by their likelihood of being interesting.  Coppersmith and Priebe propose using both node features (content) and network features (context) to propose potentially interesting nodes.  

## Summary of Gunrock Implementation

Since HIVE is focused on graph analytics, the content piece is not relevant, and the Gunrock implementation only includes the context piece.  Coppersmith and Priebe propost a number of possible network statistics that could be used for context similarity, but the reference implementation ranks nodes by their minimum distance to a node in a set of seed nodes, so we have implemented that in Gunrock.  This amounts to something very close to a single source shortest paths (SSSP) problem, but instead of starting from a single node, we start from a set of seeds nodes.

Because of the similarity to SSSP, the [Gunrock VN implementation](https://github.com/gunrock/gunrock/tree/dev-refactor/tests/vn) just involved a minor modification of the [Gunrock SSSP implementation](https://github.com/gunrock/gunrock/tree/dev-refactor/tests/sssp) that accepts a list of source nodes instead of a single source node.  Thus, the core VN operation is a parallel version of Djikstra's algorithm.  In `python`:

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
 a) adding a dummy source node to the graph; and
 b) adding an edge between the dummy node and the nodes in the seed set; and
 c) subtracting 1 from the final results.

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

```
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock/tests/vn
cp ../../gunrock/util/gitsha1.c.in ../../gunrock/util/gitsha1.c
make clean
make
# !! May need to change compute capability in `gunrock/tests/BaseMakefile.mk`
```

### Running the application

```
./bin/test_vn_9.1_x86_64 \
    --graph-type market \
    --graph-file ../../dataset/small/chesapeake.mtx \
    --src 0,1,2
```
yields
```
Loading Matrix-market coordinate-formatted graph ...
Reading from ../../dataset/small/chesapeake.mtx:
  Parsing MARKET COO format edge-value-seed = 1537904627
 (39 nodes, 340 directed edges)... 
Done parsing (0 s).
  Converting 39 vertices, 340 directed edges ( ordered tuples) to CSR format...
Done converting (0s).
Computing reference value ...
srcs_vector | num_srcs=3
test_vn srcs[i]=0
test_vn srcs[i]=1
test_vn srcs[i]=2
__________________________
CPU num_srcs=3
--------------------------
Run 0 elapsed: 0.005007 ms, srcs = 0,1,2
Using advance mode LB
Using filter mode CULL
__________________________
--------------------------
Run 0 elapsed: 0.334024 ms, srcs = 0,1,2, #iterations = 3
Distance Validity: PASS
First 40 distances of the GPU result:
[0:0 1:0 2:0 3:2 4:2 5:2 6:1 7:1 8:1 9:2 10:1 11:1 12:1 13:1 14:1 15:1 16:1 17:1 18:2 19:2 20:2 21:1 22:1 23:2 24:2 25:2 26:2 27:2 28:2 29:2 30:2 31:2 32:2 33:1 34:1 35:1 36:1 37:2 38:1 ]
First 40 distances of the reference CPU result.
[0:0 1:0 2:0 3:2 4:2 5:2 6:1 7:1 8:1 9:2 10:1 11:1 12:1 13:1 14:1 15:1 16:1 17:1 18:2 19:2 20:2 21:1 22:1 23:2 24:2 25:2 26:2 27:2 28:2 29:2 30:2 31:2 32:2 33:1 34:1 35:1 36:1 37:2 38:1 ]

[vn] finished.
 avg. elapsed: 0.334024 ms
 iterations: 3
 min. elapsed: 0.334024 ms
 max. elapsed: 0.334024 ms
 rate: 1.017890 MiEdges/s
 src: 1
 nodes_visited: 39
 edges_visited: 340
 load time: 85.8979 ms
 preprocess time: 962.881000 ms
 postprocess time: 0.576019 ms
 total time: 963.964939 ms
```

### Output

Currently, the VN app does not produce any output. It prints runtime statistics and the results of a correctness check.  A successfuly run will print 
```
Distance Validity: PASS
```
in the output.

The Gunrock VN implementation was tested against the [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/vertex_nomination_Enron/blob/master/snap_vertex_nomination.py) to verify correctness.  We also implemented a CPU reference implementation inside of the Gunrock VN app.

## Performance and Analysis

Performance is measured by runtime.

#### Python reference implementation
The Python+SNAP reference implementation is found [here](https://gitlab.hiveprogram.com/ggillary/vertex_nomination_Enron/blob/master/snap_vertex_nomination.py).  This implementation does 10 runs w/ 5 random seeds each on the Enron email dataset.  Runtimes in ms are as follows:
```
4239.80593681
3326.16710663
3951.03907585
4371.74320221
3791.98694229
3920.63999176
6871.20199203
3738.28697205
3509.23800468
3435.40382385
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
