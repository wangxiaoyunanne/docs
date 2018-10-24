---
title: Template for HIVE workflow report

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

<aside class="notice">
  JDO notes, delete these when you copy this to `hive_yourworkflowname`: The goal of this report is to be useful to DARPA and to your colleagues. This is not a research paper. Be very honest. If there are limitations, spell them out. If something is broken or works poorly, say so. Above all else, make sure that the instructions to replicate the results you report are good instructions, and the process to replicate are as simple as possible; we want anyone to be able to replicate these results in a straightforward way.
</aside>

# Local Graph Clustering (LGC)

From [Andersen et al](https://projecteuclid.org/euclid.im/1243430567): > A local graph partitioning algorithm finds a cut near a specified starting vertex, with a running time that depends largely on the size of the small side of the cut, rather than the size of the input graph.

## Summary of Gunrock Implementation

As long as you need. Provide links (say, to papers) where appropriate. What was the approach you took to implementing this on a GPU / in Gunrock? Pseudocode is fine but not necessary. Whatever is clear.

Be specific about what you actually implemented with respect to the entire workflow (most workflows have non-graph components; as a reminder, our goal is implementing single-GPU code on only the graph components where the graph is static).

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

```bash
git clone --recursive https://github.com/gunrock/gunrock.git
cd gunrock

# build Gunrock
cmake .
make -j16

# build App
cd tests/pr_nibble
make -j16

```

### Running the application

```bash
./bin/test_pr_nibble_9.1_x86_64 \
    --graph-type market \
    --graph-file ../../dataset/small/chesapeake.mtx \
    --src 0 \
    --max-iter 1
```

Output:
```
Loading Matrix-market coordinate-formatted graph ...
Reading from ../../dataset/small/chesapeake.mtx:
  Parsing MARKET COO format
 (39 nodes, 340 directed edges)...
Done parsing (0 s).
  Converting 39 vertices, 340 directed edges ( ordered tuples) to CSR format...
Done converting (0s).
__________________________
pr_nibble::CPU_Reference: reached max iterations. breaking at it=1
--------------------------
 Elapsed: 0.018835
Using advance mode LB
Using filter mode CULL
__________________________
pr_nibble::Stop_Condition: reached max iterations. breaking at it=1
--------------------------
Run 0 elapsed: 0.252008, #iterations = 1
0 errors occurred.
[pr_nibble] finished.
 avg. elapsed: 0.252008 ms
 iterations: 140734444779008
 min. elapsed: 0.252008 ms
 max. elapsed: 0.252008 ms
 src: 0
 nodes_visited: 5326555
 edges_visited: 2
 nodes queued: 140734444778192
 edges queued: 38878400
 load time: 82.2091 ms
 preprocess time: 978.001000 ms
 postprocess time: 0.098944 ms
 total time: 978.564978 ms
 ```
 
### Output

We output information about the quality of the match in each iteration. The most important number is X errors occurred, which gives the number of disagreements between our CPU validation and our result. X = 0 indicates that LGC has generated an output that matches exactly with our CPU validation.

This implementation is validated against the [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/local_graph_clustering_socialmedia). 

## Performance and Analysis

Performance is primarily measured in runtime of the clustering portion of the LGC procedure. We do not compare the sweep-cut component, because we do not find it to be the meaningful component in this application.  In particular, the LSAP solver in the first iteration tends to take 10-100x longer than in subsequent iterations.

### Implementation limitations

e.g.:

- Size of dataset that fits into GPU memory (what is the specific limitation?)
- Restrictions on the type/nature of the dataset
- (@bkj any input here would be valuable) 

### Comparison against existing implementations

- UCB reference implementation (Python wrapper around C++ library)
- CPU reference implementation (C++)

Comparison can be replicated by doing the following.

```bash
# download datasets
cd dataset/large
make -j16

# run script
sh test_big.sh
```
All runtimes are in milliseconds (ms):

Dataset | UCB C++ | Our C++ | Gunrock
------------ | ------------- | ------------ | ------------- 
ak2010 | 97.99 | 72.08 | 3.04
belgium_osm | 2270 | 1663 | 2.97
cit-Patents | 40574 | 22148 | 16.41
coAuthorsDBLP | 1004 | 1399 | 4.86
delaunay_n13 | 21.52 | 16.33 | 2.86
delaunay_n21 | 5733 | 4084 | 2.98
delaunay_n24 | 49299 | 34655 | 3.28
europe_osm | 97022 | 72973 | 2.95
hollywood-2009 | 43024 | 30430 | 46.30
indochina-2004 | 101877 | 71902 | 11.05
kron_g500-logn21 | 110309 | 89438 | 627.55
roadNet-CA | 3403 | 2475 | 3.03
road_usa | 48232 | 31617 | 3.01
soc-LiveJournal1 | 63151 | 37936 | 19.29
soc-orkut | 111391 | 89752 | 18.05

We find the Gunrock implementation is 3 orders of magnitude faster than either reference CPU implementation implemented by C++.

### Performance limitations

We profiled the primitives while running `kron_g500-logn21`. The profiler adds ~100ms of overhead (728.48ms with profiler vs. 627.55ms without profiler). The breakdown looks like

Gunrock Kernel | Runtime (ms) | Percentage
------------ | ------------- | ------------
Advance (EdgeMap) | 566.76 | 77.8%
Filter (VertexMap) | 10.85 | 1.49%
ForAll (VertexMap) | 2.90 | 0.40%
Other | 147.89 | 20.3%

Note: "Other" includes HtoD and DtoH memcpy, smaller kernels such as scan, reduce, etc.

## Next Steps

### Alternate approaches

If you had an infinite amount of time, is there another way (algorithm/approach) we should consider to implement this?

### Gunrock implications

What did we learn about Gunrock? What is hard to use, or slow? What potential Gunrock features would have been helpful in implementing this workflow?

### Notes on multi-GPU parallelization

What will be the challenges in parallelizing this to multiple GPUs on the same node?

Can the dataset be effectively divided across multiple GPUs, or must it be replicated?
(@bkj any input here would be great)

### Notes on dynamic graphs

N/A

### Notes on larger datasets

What if the dataset was larger than can fit into GPU memory or the aggregate GPU memory of multiple GPUs on a node? What implications would that have on performance? What support would Gunrock need to add?
(@bkj any input here would be great)

### Notes on other pieces of this workload

Briefly: What are the important other (non-graph) pieces of this workload? Any thoughts on how we might implement them / what existing approaches/libraries might implement them?
