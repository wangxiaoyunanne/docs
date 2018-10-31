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

__TODO__
One or two sentences that summarize "if you had one or two sentences to sum up your whole effort, what would you say". I will copy this directly to the high-level executive summary in the first page of the report. Talk to JDO about this. Write it last, probably.

## Summary of Gunrock Implementation

## Reference
[Scan Statistics on Enron Graphs](http://www.cis.jhu.edu/~parky/CEP-Publications/PCMP-CMOT2005.pdf)

[Statistical inference on random graphs: Comparative power analyses via Monte Carlo](http://cis.jhu.edu/~parky/CEP-Publications/PCP-JCGS-2010.pdf)

## Algorithm: Scan Statistics
Input is an undirected graph
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
scan_stats[nodes] = degrees[nodes]
node_ids[nodes]

Advance + Filter (src_node_ids): remove all edges whose src id is larger than dest to avoid visiting the same edge two times later
Intersection (src_node_ids, scan_stats): intersect neighoring nodes of both nodes of each edge to get number of triangles and accumulate the count to each node in scan_stats
Sort(scan_stats, node_ids): sort the node ids based on the scan_stats' values from largest to smallest

return [scan_stats[0], node_ids[0]]
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
	--graph-file=./scan_statistics.mtx
```

### Output

The output of this app is two values: the maximum scan statistic value we've found and the node id that has this statistic.  The output file will be in `.txt` format with the aforementioned two values.

We compare our GPU output with the [HIVE CPU reference implementation] which is implemented using python and the SNAP graph processing library.

## Performance and Analysis

We measure the performance by runtime. The whole process is ran on the GPU and we don't include the data copy time which is included in the pre-procesing time. The accuracy measurement is set since the algorithm is deterministic.

### Implementation limitations

__TODO__

e.g.:

- Size of dataset that fits into GPU memory (what is the specific limitation?)
- Restrictions on the type/nature of the dataset

### Comparison against existing implementations

- Reference implementation is in python on the CPU
- OpenMP reference is not available yet

Comparison is both performance and accuracy/quality.

### Performance limitations

__TODO__

e.g., random memory access?

## Next Steps

### Alternate approaches

__TODO__

If you had an infinite amount of time, is there another way (algorithm/approach) we should consider to implement this?

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
