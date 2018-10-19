---
title: HIVE workflow report for Louvain GPU implementation

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Community Detection (Louvain)

Community detection in graphs is to group vertices together, such that those
closer (have more connections) to each other are placed in the same cluster.
A common used algorithm for community detection is Louvain
(https://arxiv.org/pdf/0803.0476.pdf ).

## Summary of Results

One or two sentences that summarize "if you had one or two sentences to sum up
your whole effort, what would you say". I will copy this directly to the high-level
executive summary in the first page of the report. Talk to JDO about this.
Write it last, probably.

## Summary of Gunrock Implementation

The Gunrock implementation uses sort and segmented reduction, instead of the
commonly used hash table approach. The Pseudocode is listed below:
```
m2 <- sum(edge_weights);
//Outer-loop
Do
    // Pass-initialization, assign each vertex to its own community
    For each vertex v in graph:
        current_communities[v] <- v;
        weights_v2any      [v] <- 0;
        weights_v2self     [v] <- 0;
    For each edge e<v, u> in graph: //an advance operator on all edges
        weights_v2any[v] += edge_weights[e];
        if (v == u)
            weights_v2self[v] += edge_weights[e];
    For each vertex v in graph:
        weights_community2any[v] <- weights_v2any[v];
    pass_gain <- 0;

    // Modularity optimizing iterations
    Do
        // Get weights between vertex and community
        For each edge e<v, u> in graph:
            edge_pairs  [e] <- <v, current_communities[u]>;
            pair_weights[e] <- edge_weights[e];
        Sort(edge_pairs, pair_weights)
            by edge_pair.first, then edge_pair.second if tie;
        segment_offsets <- offsets of continuous edge_pairs;
        segment_weights <- SegmentedReduce(pair_weights, segment_offsets, sum);

        // Compute base modularity gains
        // if moving vertices out of current communities
        For each vertex v in graph:
            comm <- current_communities[v];
            w_v2comm <- Find weights from v to comm in segment_weights;
            gain_bases[v] = weights_v2self[v] - w_v2comm
                - (weights_v2any[v] - weights_community2any[comm])
                    * weights_v2any[v] / m2;

        // Find the max gains if moving vertices into adjacent communities
        For each vertex v in graph:
            gains[v] <- 0;
            next_communities[v] <- current_communities[v];
        For each seg<v, comm> segment:
            if (comm == current_communities[v])
                continue;
            gain <- gain_bases[v] + segment_weights[seg]
                - weights_community2any[comm] * weights_v2any[v] / m2;
            atomicMax(max_gains + v, gain);
            seg_gains[seg] <- gain;
        For each seg<v, comm> segment:
            if (seg_gains[seg] != max_gains[v])
                continue;
            next_communities[v] <- comm;

        // Update communities
        For each vertex v in graph:
            curr_comm <- current_communities[v];
            next_comm <- next_communities[v];
            if (curr_comm == next_comm)
                continue;

            atomicAdd(weights_community2any[next_comm],  weights_v2any[v]);
            atomicAdd(weights_community2any[curr_comm], -weights_v2any[v]);
            current_communities[v] <- next_comm;

        iteration_gain <- Reduce(max_gains, sum);
        pass_gain += iteration_gain;
    While iterations stop condition not met
    // End of modularity optimizing iterations

    // Contract the graph
    // renumber occupied communities
    new_communities <- Renumber(current_communities);
    For each edge e<v, u> in graph: //an advance operator on all edges
        edge_pairs[e] <- <new_communities[current_communities[v]],
                          new_communities[current_communities[u]]>
    Sort(edge_pairs, edge_weights) by pair.x, then pair.y if tie;
    segment_offsets <- offsets of continuous edge_pairs;
    new_graph.Allocate(|new_communities|, |segments|);
    new_graph.edges <- first pair of each segments;
    new_graph.edge_values <- SegmentedReduce(edge_weights, segment_offsets, sum);

While pass stop condition not met
```

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

CUDA should have been installed; `$PATH` and `$LD_LIBRARY_PATH` should have been
set correctly to use CUDA. The current Gunrock configuration assumes boost
(1.58.0 or 1.59.0) and metis are installed; if not, changes need to be made in
the Makefiles. DARPA's DGX-1 has both installed when the tests are performed.

```
git clone --recursive https://github.com/gunrock/gunrock/
cd gunrock
git checkout dev-refactor
git submodule init
git submodule update
mkdir build
cd build
cmake ..
cd ../tests/louvain
make
```
At this point, there should be an executable `louvain_main_<CUDA version>_x86_64`
in `tests/louvain/bin`.

The datasets are assumed to have been placed in `/raid/data/hive`, and converted
to proper matrix market format (.mtx). At the time of testing, `ca`, `amazon`,
`akamai`, and `pokec` are available in that directory. `ca` and `amazon` are taken
from PNNL's implementation, and originally use 0-based vertex index; 1 is added
to each vertex Id to make them proper .mtx files.

The testing is done with Gunrock using `dev-refactor` branch at commit `2699252`
(Oct. 18, 2018), using CUDA 9.1 with NVIDIA driver 390.30.

### Running the application

<code>
./bin/louvain_main_9.1_x86_64 --omp-threads=32 --iter-stats --pass-stats
--advance-mode=ALL_EDGES --unify-segments=true --validation=each --num-runs=10
--graph-type=market --graph-file=/raid/data/hive/[DataSet]/[DataSet].mtx
--jsondir=[LogDir] > [LogDir]/[DataSet].txt 2>&1
</code>

Add `--undirected`, if the graph is indeed undirected.
Remove `--iter-stats` or `--pass-stats`, if detailed timings are not required.
Remove `--validation=each`, to only compute the modularity for the last run.

For example, when DataSet = `akamai`, and LogDir = `eval/DGX1-P100x1`, the command is
<code>
./bin/louvain_main_9.1_x86_64 --omp-threads=32 --iter-stats --pass-stats
--advance-mode=ALL_EDGES --unify-segments=true --validation=each --num-runs=10
--graph-type=market --graph-file=/raid/data/hive/akamai/akamai.mtx
--jsondir=eval/DGX1-P100x1 > eval/DGX1-P100x1/akamai.txt 2>&1
</code>

### Output

The outputs are in the `louvain` directory.
Look for the `.txt` files: running time is after `Run x elapsed:`, the number of
communities and the resulted modularity is in the line started with `Computed:`.
There are 12 runs in each `.txt` file: 1 single thread CPU run for reference,
1 OpenMP multiple-thread (32 threads in the example, may not be optimal) run,
and 10 GPU runs.

The output was compared against PNNL's results on the number of communities and
modularity, for amazon and ca datasets. Note that PNNL's code does not count
dangling vertices in the communities. Results are listed below use the number of
communities minus dangling vertices.

| DataSet | #V     | #E      | #dangling vertices | Gunrock GPU     | OMP (32T)      | Serial         | PNNL (8T)      | PNNL (serial)  |
|---------|--------|---------|-------------------|-----------------|----------------|----------------|----------------|----------------|
| amazon  | 548551 | 1851744 | 213688            | 7667 / 0.908073 | 213 / 0.925721 | 240 / 0.926442 | 298 / 0.923728 | 251 / 0.925557 |
| ca      | 108299 | 186878  | 85166             | 1120 / 0.711971 | 616 / 0.730217 | 617 / 0.731292 | 654 / 0.713885 | 623 / 0.727127 |

Note for these kind of small graphs, more parallelism could hurt the modularity. Multi-thread
CPU implementations by both Gunrock and PNNL yield modularities a little less than the serial
versions, and the GPU implementation sees ~0.02 drop. The reason could be concurrent updates to
the communities: vertex A moves to community C, thinking vertex B is in C; but B may have
moved to other communities. The modularity gain could be inaccurate, without heavy workload
increase. When the graph is larger in size, this issue seems to disappear, and modularities
from the GPU implementation could be even bigger than the serial implementation.

## Performance and Analysis
The Louvain performance is measured by three metrics: the number of resulted communities (#Comm),
the modularity of resulted communities (Q), and the running time (Time, in seconds). Higher Q and
lower running time are better. * indicates the graph is given as undirected, and the number of
edges is counted after edge doubling and removing of self loops or duplicate edges; otherwise,
the graph is taken as directed, and self loops or duplicate edges are also removed. If edge
weights are available in the input graph, they follow the input; otherwise, the initial edge
weights are set to 1.

| GPU  | DataSet          | #V    | #E | #dangling vertices| GPU #Comm |     Q | Time  | OMP #Comm | Q     | Time  | Serial #Comm | Q  | Time   |
|------|------------------|---------:|-----------:|-------:|-------:|---------:|------:|-------:|---------:|-------|-------:|---------:|-------:|
| P100 | amazon           |   548551 |    1851744 | 213688 |   7667 | 0.908073 | 0.160 |    213 | 0.925721 | 0.203 |    240 | 0.926442 |  0.648 |
| P100 | ca               |   108299 |     186878 |  85166 |   1120 | 0.711971 | 0.108 |    616 | 0.730217 | 0.026 |    617 | 0.731292 |  0.065 |
| P100 | akamai           | 16956250 |   53300364 |      0 |  90285 | 0.933362 | 1.278 | 130639 | 0.907232 | 6.560 | 145785 | 0.900488 | 14.427 |
| P100 | pokec            |  1632803 |   30622564 |      0 | 154988 | 0.693353 | 0.929 | 161709 | 0.691351 | 1.244 | 166156 | 0.694540 |  6.521 |
| V100 | amazon           |   548551 |    1851744 | 213688 | 221359 | 0.908944 | 0.122 | 213921 | 0.925799 | 0.198 | 213928 | 0.926442 |  0.631 |
| V100 | ca               |   108299 |     186878 |  85166 |  86242 | 0.716568 | 0.089 |  85781 | 0.728962 | 0.029 |  85783 | 0.731292 |  0.067 |
| V100 | akamai           | 16956250 |   53300364 |      0 |  90245 | 0.933281 | 0.934 | 127843 | 0.907444 | 6.343 | 145785 | 0.900488 | 13.266 |
| V100 | pokec            |  1632803 |   30622564 |      0 | 155100 | 0.674148 | 0.624 | 162464 | 0.676286 | 1.083 | 166156 | 0.694540 |  6.110 |
| V100 | cnr-2000         |   325557 |    3128710 |      0 |  65621 | 0.876618 | 0.235 |  59219 | 0.878374 | 0.133 |  59253 | 0.879678 |  0.388 |
| V100 | coPapersDBLP     |   540486 |  *30481458 |      0 |     70 | 0.849409 | 0.358 |    111 | 0.843996 | 0.437 |    237 | 0.849065 |  1.860 |
| V100 | soc-LiveJournal1 |  4847571 |   68475391 |    962 | 506826 | 0.733556 | 1.548 | 434272 | 0.545648 | 4.016 | 447426 | 0.723852 | 16.311 |
| V100 | channel-500x100x100-b050 | 4802000 | 85362744 | 0 |     24 | 0.900354 | 1.133 |     54 | 0.951188 | 0.768 |     12 | 0.850520 |  4.449 |
| V100 | uk-2002          | 18520486 |  292243663 |  37300 | 2402560| 0.950671 | 4.921 | 2245355| 0.960437 | 5.682 | 2245678| 0.960437 | 31.006 |
| V100 | europe_osm       | 50912018 | *108109320 |      0 |  17320 | 0.997856 | 4.902 | 784171 | 0.984438 | 34.875| 828662 | 0.983616 | 101.320|
| V100 | rgg_n_2_24_s0    | 16777216 | *265114400 |      1 |    344 | 0.992145 | 3.378 |    359 | 0.991991 | 2.664 |    311 | 0.989576 | 17.816 |
| V100 | webbase-1M       |  1000005 |   2105531  |   2453 |   4430 | 0.894534 | 0.107 |   1469 | 0.947102 | 0.168 |   1362 | 0.955795 |  0.318 |
| V100 | preferentialAttachment | 100000 | *999970 |     0 |     18 | 0.175757 | 0.076 |     14 | 0.228699 | 0.096 |     39 | 0.285213 |  0.235 |
| V100 | caidaRouterLevel |   192244 |   *1218132 |      0 |    410 | 0.850029 | 0.063 |    467 | 0.836249 | 0.065 |    745 | 0.843553 |  0.229 |
| V100 | citationCiteseer |   268495 |   *2313294 |      0 |     67 | 0.788792 | 0.074 |     48 | 0.760494 | 0.111 |    141 | 0.802499 |  0.432 |
| V100 | coAuthorsDBLP    |   299067 |   *1955352 |      0 |     95 | 0.809231 | 0.082 |    138 | 0.813649 | 0.133 |    273 | 0.827131 |  0.414 |
| V100 | coPapersCiteseer |   434102 |  *32073440 |      0 |    108 | 0.907459 | 0.353 |    110 | 0.905869 | 0.391 |    358 | 0.911000 |  1.592 |
| V100 | hollywood-2009   | 11399905 | *112751422 |  32662 |  12218 | 0.743242 | 1.230 |  12593 | 0.750153 | 1.721 |  12741 | 0.751122 |  9.419 |
| V100 | as-Skitter       |  1696415 |  *22190596 |      0 |    924 | 0.836608 | 0.376 |   1945 | 0.822323 | 0.660 |   2531 | 0.813229 |  2.480 |

Published results (timing and modularity) are included in the `Reference.xlsx`
file in the `louvain` directory.

### Implementation limitations

- **Memory usage** Each edge in the graph needs at least 88 bytes GPU device memory:
 32-bit for destination vertex, 64-bit for edge weight, 64 bit x 2 x 4 for edge
 pairs and sorting, 32 bit for segment offsets and 64 bit for segment weights,
 assuming both vertex and edge Ids are represent as 32-bit integers, and edge
 weights are represent as 64-bit floating points. So using a 32GB GPU, the maximum
 graph the Louvain implementation can take is at about 300 million edges.
 The largest graph successfully run so far is `uk-2002` with 292M edges and 18.5M
 vertices.

- **Data types** The edge weights and all computation around them are double
 precision floating point values (64-bit `double` in C/C++); single precision
 was tried, but resulted in very poor modularities. The
 `weight * weight / m2` part in modularity calculation may be
 the reason for this limitation. Vertex Ids should be 32-bit, as the implementation
 uses 64-bit integers to represent an edge pair for the sort function; if fast
 GPU sorting is available for 128-bit integers, 64-bit Vertex Ids might be used.

### Comparison against existing implementations

Comparison is done against serial CPU and OpenMP implementations, both are
Gunrock's CPU reference routines. PNNL's results and pervious published works
are also referenced, to make sure the resulted modularities and running times
are not far off.

- **Modularity** The modularities have some variation from different implementations,
mostly within +- 0.05. As mentioned in the output section, that variation could
be caused by concurrent movement of vertices. Small graphs could suffer more than
larger graphs, as movements to a communities have higher chance to happen concurrently.

- **Running time** Overall, the Gunrock implementation is 2X to 5X faster than
pervious works on GPU. The OMP implementation is a bit faster than PNNL's, and
much faster than pervious works using multiple CPU threads. The sequential CPU
is an order faster than pervious sequential CPU work. Comparing across different
Gunrock implementations, the GPU is not always the fastest: on small graphs, GPU
could actually be slower, caused by GPU kernel overheads and hardware under utilizations; so for small graphs, the OpenMP implementation may be a better choice.

### Performance limitations

The performance bottleneck is the sort function, especially in the first pass.
Using `akamai` dataset to profile the GPU Louvain implementation on a V100, an
iteration in the first pass takes 64.08 ms, and the sort takes 42.05 ms, which
is two third of the iteration time. The Louvain implementation uses CUB's radix
sort pair function. CUB is considered to be one of the GPU primitive libraries
that provide the best performance. Further profiling shows during the sort kernel,
the device memory controller is ~75% utilized, in other words, the sort is
memory bound. This is as expected, as in each iteration of radix sort, the whole
`edge_pairs` and `pair_weights` arrays are shuffle, with cost in the order of
`O(|E|)`, although the memory accesses are mostly coalesced. The memory system
utilizations are as below (from NVIDIA profiler):

|Type     | Transactions | Bandwidth | Utilization |
|--------------|--------:|----------:|-------------|
|Shared Loads  | 2141139 | 1168.859 GB/s | |
|Shared Stores | 2486946 | 1357.636 GB/s | |
|Shared Total  | 4628085 | 2526.495 GB/s | Low |
|L2 Reads      | 2533302 |  345.736 GB/s | |
|L2 Writes     | 2831732 |  386.464 GB/s | |
|L2 Total      | 5365034 |  732.200 GB/s | Low |
|Local Loads   |     588 |   80.248 MB/s | |
|Local Stores  |     588 |   80.248 MB/s | |
|Global Loads  | 2541637 |  346.873 GB/s | |
|Global Stores | 2675820 |  365.186 GB/s | |
|Texture Reads | 2515533 | 1373.242 GB/s | |
|Unified Cache Total| 7734166 | 2085.462 GB/s | Idle to Low |
|Device Reads  | 2469290 |  336.999 GB/s | |
|Device Writes | 2596403 |  354.347 GB/s | |
|**Device Memory Total**| **5065693** | **691.347 GB/s** | **High** |
|PCIe Reads    |       0 |        0 B/s  | None |
|PCIe Writes   |       5 |  682.381 kB/s | Idle to Low |

![Louvain_akamai]( attachments/louvain/Louvain_akamai.png "Memory statistics")

It's clear that the bottleneck is at the device memory: most data are read-once
and write-once, no much possibility to reuse the data. The kernel achieved 691 GB/s
bandwidth utilization, ~77% of the 32GB HBM2's 900 GB/s capability. This high
bandwidth utilization fits the memory access pattern: mostly regular and coalesced.
The particular issue here is not the kernel implementation itself, it's the usage
of sorting: fully sorting the whole edge list maybe overkill.

One possible improvement is to use a custom hash table on the GPU, to replace the
sort + segmented reduce part. The hash table can also cut the memory requirement
by about 50%.

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
