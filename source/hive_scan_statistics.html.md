---
title: Template for HIVE Scan Statistics workflow report

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Scan Statistics

Scan statistics as described in [Priebe et al](http://www.cis.jhu.edu/~parky/CEP-Publications/PCMP-CMOT2005.pdf) are the generic method that computes a statistic for the neighborhood of each node in the graph, and looks for anomalies in those statistics. In this workflow, we implement the specific version of scan statistics where we compute the number of edges in the subgraph induced by the one-hop neighborhood of each node u in the graph. It turns out that this statistic is equal to the number of triangles that node u participates in plus the degree of u. Thus, we are able to implement scan statistics by making relatively minor modifications to our existing Gunrock triangle counting (TC) application.

## Summary of Results
Scan statistics problem on solving static graphs fits perfectly in Gunrock framework. Using a combination of ForAll and Intersection operations, we are able to beat the parallel OpenMP CPU reference by up to 45.4 times speedup on small enron graph provided by hive workflows and up to 580 times speedup on larger graphs which saturates the thoughouput of the GPU device.

## Algorithm: Scan Statistics
Input is an undirected graph w/o self loops.
```
scan_stats = [len(graph.neighbors(u)) for u in graph.nodes]
for (u, v) in graph.edges:
    if u < v:
        u_neibs = graph.neighbors(u)
        v_neibs = graph.neighbors(v)
        for shared_neib in intersect(u_neibs, v_neibs):
            scan_stats[shared_neib] += 1
return argmax([scan_stats(node) for node in graph.nodes])
```
## Summary of Gunrock implementation

```
max_scan_stat = -1
node = -1
src_node_ids[nodes]
scan_stats[nodes]

ForAll (src_node_ids, scan_stats): fill scan_stats with the degree of each node.
Intersection (src_node_ids, scan_stats): intersect neighoring nodes of both nodes of each edge, add 1 to scan_stats[common_node] for each common_node we get from intersection.

return [scan_stats]
```

## How To Run This Application on DARPA's DGX-1

### Prereqs/input
```bash
git clone --recursive https://github.com/gunrock/gunrock \
	-b dev-refactor
cd gunrock
mkdir build
ctest ..
cd ../tests/ss/
make clean && make
```

### Running the application
Application specific parameters:
 
Example command-line:

```bash
./bin/test_ss_main_10.0_x86_64 \
	--graph-type=market \
	--graph-file=./enron.mtx \
        --undirected --num_runs=10
```

### Output

The output of this app is an array of uint values: the scan statistics values for each node.  The output file will be in `.txt` format with the aforementioned values.

We compare our GPU output with the [HIVE CPU reference implementation] which is implemented using OpenMP.

Details of the datasets:

| DataSet          | #V    | #E | #dangling vertices|
|------------------|---------:|-----------:|-------:|
| enron            |    15056 |     57074  |      0 |
| ca               |   108299 |    186878  |  85166 |
| amazon           |   548551 |   1851744  | 213688 |
| coAuthorsDBLP    |   299067 |   1955352* |      0 |
| citationCiteseer |   268495 |   2313294* |      0 |
| as-Skitter       |  1696415 |  22190596* |      0 |
| coPapersDBLP     |   540486 |  30481458* |      0 |
| pokec            |  1632803 |  30622564  |      0 |
| coPapersCiteseer |   434102 |  32073440* |      0 |
| akamai           | 16956250 |  53300364  |      0 |
| soc-LiveJournal1 |  4847571 |  68475391  |    962 |
| europe_osm       | 50912018 | 108109320* |      0 |
| hollywood-2009   | 11399905 | 112751422* |  32662 |
| rgg_n_2_24_s0    | 16777216 | 265114400* |      1 |


Running time in milli seconds:

| GPU  | Dataset          | Gunrock GPU | Speedup vs. OMP | OMP |
|------|------------------|------------:|-----:|-------:|-------:|
| P100 | enron            |     **0.461** | 45.4 | 20.95 |
| P100 | ca               |     **0.219** | 71.6 | 15.681 |
| P100 | amazon           |     **1.354** | 74.5 | 100.871 |
| P100 | coAuthorsDBLP    |     **1.569** | 88.0 | 138.111 |
| P100 | citationCiteseer |     **3.936** | 65.22 | 256.694 |
| P100 | as-Skitter       |     **111.738**| 579.22  | 64721.414 |
| P100 | coPapersDBLP     |     **226.672** | 25.4 | 5766.4 |
| P100 | pokec            |     **202.185** | 80.7 | 16316.474 |
| P100 | coPapersCiteseer |     **451.582** | 16.34 | 7378.188 |
| P100 | akamai           |     **151.47** | 5.13 | 12596.36 |
| P100 | soc-LiveJournal1 |     **1.548** | 2.59 | 4.016 |
| P100 | europe_osm       |     **9.59** | 153.35 | 1470.632 |
| P100 | hollywood-2009   |     **10032.46** | 18.76 | 188206.234 |
| P100 | rgg_n_2_24_s0    |     **539.559** | 29.45 | 15887.536 |

## Performance and Analysis

We measure the performance by runtime. The whole process is ran on the GPU and we don't include the data copy time which is included in the pre-procesing time. The accuracy measurement is set since the algorithm is deterministic.

### Implementation limitations

Since the implementation only needs /number of nodes/'s size of memory allocated on the GPU, so the largest dataset which can fit on a single GPU is limited by GPU on-die memory size / number of nodes.

Because our implementation takes the graph as undirected graph. The graph type limitation is that it needs to be undirected.

### Comparison against existing implementations

- Reference implementation is in OpenMP on the CPU

Comparison is both performance and accuracy/quality.

### Performance limitations

We have to use atomic adds to accumulate the number of triangles each node is included in and atomic operations is relatively slow here. 

## Next Steps

### Alternate approaches

There's still improvement space for intersection operation in Gunrock which is the most time consuming part for scan statistics. 

Currently we divide the edge lists into two groups:
(1) small neighbor lists; and (2) large neighbor lists. We implement two kernels (TwoSmall and TwoLarge) that cooperatively compute intersections. Our TwoSmall kernel uses one thread to compute the intersection of a node pair. Our TwoLarge kernel partitions the edge list into chunks and assigns each chunk to a separate thread block. Then each block uses the balanced path primitive to cooperatively compute intersections. But there's one other case we haven't covered which is one small neighbor list and one large neighbor list. By using 3-kernel strategy and carefully choosing a threshold value to divide the edge list into two groups, we can process intersections with same level of workload together to gain load balancing and higher GPU resource utilization.

### Gunrock implications

Gunrock is helpful in the implementation. The only hard part is the accumulation when doing intersection. Intersection is designed to ount the total number of triangles. But in the app, we need the triangle counts for each node which introduces extra atomic add when doing the accumulation if multiple edges share the same node since we are doing traingle counting in parallel for each edge.

### Notes on multi-GPU parallelization

A non-ideal graph partitioning could be a bottle-neck on multi-GPU parallelization. Because we need the info of each node's two-hop neighbors, unbalanced workload will decrease the performance and increase the communication bottleneck. 

### Notes on dynamic graphs

This workload have a dynamic-graph component as it can potentially take in time-series graph and try to find any abnormal behavior in any statistics change as mentioned in the referenced papers. We would need Gunrock to support dynamic graph in its advance and intersection operators. The application could be easily changed to record all history scan statistics and try to find any significant changes with a certain threshold.

### Notes on larger datasets

For a dataset which is too large to fit into a single GPU, we can leverage the multi-GPU implementation of Gunrock to make it work on multiple GPUs on a single node. The implementation won't change a lot since Gunrock already has good support in its multi-GPU implementation. We expect the performance and memory usage to scale linearly with good graph partionling method. 

For a dataset which cannot fit multiple GPUs on a single node, we need distributed level of computation which Gunrock doesn't support yet. However, we can reference open source libraries such as NCCL and Horovad that support this. Performance-wise, the way of partitioning the graph as well as the properties of a graph will effect the communication bottleneck. Since we need to calculate the total number of triangles each node is involved in, if we couldn't fit all neighorhood of a node on a single node, we need other compute resources' help in solving that. Worst case senario is that the graph is fully connected, and we have to wait for the counting results from all other compute resources and sum them up. In this case, if we can do good scheduling of load balancing, we can minimize the communication bottleneck and reduce latency.

### Notes on other pieces of this workload

Other important pieces of this work includes statistical time series analysis on the dynamic changes of the graph. Gunrock currently doesn't support dealing with dynamic graphs, but other libraries such as cuSTINGER might solve the problem.

### Research value

This application takes the advantage of a classic traingle counding problem to solve a more complex statistics problem. Instead of directly using the existing solution, it's solved from a different angle. Instead of counting the total number of triangles in the graph, we count triangles from each node's respective.

From this app, we find the flexibility our Gunrock's intersection operation. And it could be potentially used in other graph analytics research such as community detection, etc.

## Reference
[Scan Statistics on Enron Graphs](http://www.cis.jhu.edu/~parky/CEP-Publications/PCMP-CMOT2005.pdf)

[Statistical inference on random graphs: Comparative power analyses via Monte Carlo](http://cis.jhu.edu/~parky/CEP-Publications/PCP-JCGS-2010.pdf)

