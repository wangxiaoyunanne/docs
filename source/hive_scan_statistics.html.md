---
title: Template for HIVE Scan Statistics workflow report

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Scan Statistics

The scan statistics workflow finds the cardinality of the induced subgraph of the 1-hop neighborhood for each vertex. In time series analysis, this is used to discover nodes that have anomolously high local connectivity in a given timeslice. In the Enron email dataset, these anomalies often correspond to people planning conferences.

## Summary of Results

__TODO__
One or two sentences that summarize "if you had one or two sentences to sum up your whole effort, what would you say". I will copy this directly to the high-level executive summary in the first page of the report. Talk to JDO about this. Write it last, probably.

## Summary of Gunrock Implementation

## Reference
[Scan Statistics on Enron Graphs](http://www.cis.jhu.edu/~parky/CEP-Publications/PCMP-CMOT2005.pdf)

[Statistical inference on random graphs: Comparative power analyses via Monte Carlo](http://cis.jhu.edu/~parky/CEP-Publications/PCP-JCGS-2010.pdf)

## Algorithm: Scan Statistics
```
max_scan_stat = -1
node = -1
for each node i in G:
    scan_stat[i] = (number_of_triangles_including i) + \
    	(degree of i)
    if scan_stat[i] > max_scan_stat:
        max_scan_stat = scan_stat[i]
        max_node = i

return [max_node, max_scan_stat]
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

We compare the output with python version of this app on the CPU.

## Performance and Analysis

__TODO__

How do you measure performance? What are the relevant metrics? Runtime? Throughput? Some sort of accuracy/quality metric?

### Implementation limitations

__TODO__

e.g.:

- Size of dataset that fits into GPU memory (what is the specific limitation?)
- Restrictions on the type/nature of the dataset

### Comparison against existing implementations

__TODO__

- Reference implementation (python? Matlab?)
- OpenMP reference

Comparison is both performance and accuracy/quality.

### Performance limitations

__TODO__

e.g., random memory access?

## Next Steps

### Alternate approaches

__TODO__

If you had an infinite amount of time, is there another way (algorithm/approach) we should consider to implement this?

### Gunrock implications

__TODO__

What did we learn about Gunrock? What is hard to use, or slow? What potential Gunrock features would have been helpful in implementing this workflow?

### Notes on multi-GPU parallelization

Graph partitioning will be a bottle neck on multi-GPU parallelization. Because we need the info of each node's two-hop neighbors, unbalanced workload will decrease the performance and increase the communication bottleneck. 

The dataset needs to be replicated if we cannot fit all two-hop neighors of each node on the same GPU.

### Notes on dynamic graphs

This workload have a dynamic-graph component as it can potentially take in time-series graph and try to find any abnormal behavior in any statistics change as mentioned in the referenced papers. We would need Gunrock to support dynamic graph in its advance and intersection operators. The application could be easily changed to record all history scan statistics and try to find any significant changes with a certain threshold.

### Notes on larger datasets

For a dataset which is too large to fit into a single GPU, we can leverage the multi-GPU implementation of Gunrock to make it work on multiple GPUs on a single node. The implementation won't change a lot since Gunrock already has good support in its multi-GPU implementation.

For a dataset which cannot fit multiple GPUs on a single node, we need distributed level of computation which Gunrock doesn't support yet. However, we can reference open source libraries such as NCCL and Horovad that support this. Performance-wise, the way of partitioning the graph as well as the properties of a graph will effect the communication bottleneck. Since we need to calculate the total number of triangles each node is involved in, if we couldn't fit all neighorhood of a node on a single node, we need other compute resources' help in solving that. Worst case senario is that the graph is fully connected, and we have to wait for the counting results from all other compute resources and sum them up. In this case, if we can do good scheduling of load balancing, we can minimize the communication bottleneck and reduce latency.

### Notes on other pieces of this workload

Other important pieces of this work includes statistical time series analysis on the dynamic changes of the graph. Gunrock currently doesn't support dealing with dynamic graphs, but other libraries such as cuSTINGER might solve the problem.

### Research value

This application takes the advantage of a classic traingle counding problem to solve a more complex statistics problem. Instead of directly using the existing solution, it's solved from a different angle. Instead of counting the total number of triangles in the graph, we count triangles from each node's respective.
