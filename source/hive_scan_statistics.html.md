---
title: Template for HIVE Scan Statistics workflow report

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Scan Statistics

Finds the cardinality of the induced subgraph of the 1-hop neighborhood for each vertex. In time series analysis, this is used to find if any group that has an increase in connectivity compared to at other times. In Enron, this detects planning of conferences.

## Summary of Results

One or two sentences that summarize "if you had one or two sentences to sum up your whole effort, what would you say". I will copy this directly to the high-level executive summary in the first page of the report. Talk to JDO about this. Write it last, probably.

## Summary of Gunrock Implementation

## Reference
[Scan Statistics on Enron Graphs](http://www.cis.jhu.edu/~parky/CEP-Publications/PCMP-CMOT2005.pdf)

[Statistical inference on random graphs: Comparative power analyses via Monte Carlo](http://cis.jhu.edu/~parky/CEP-Publications/PCP-JCGS-2010.pdf)

## Algorithm: Scan Statistics
<pre>
max_scan_stat = -1;
node = -1;
For each node i in G:
    scan_stat[i] = number_of_triangles_including i + degree of i;
    If scan_stat[i] > max_scan_stat:
        max_scan_stat = scan_stat[i];
        node = i;
return [node, max_scan_stat];
</pre>

## How To Run This Application on DARPA's DGX-1

### Prereqs/input
<pre>
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock
mkdir build
ctest ..
cd ../tests/ss/
make clean && make
</pre>

### Running the application
Application specific parameters:
 
Example command-line:

<pre>
./bin/test_ss_main_10.0_x86_64 --graph-type=market --graph-file=./scan_statistics.mtx
</pre>

Note: This run / these runs need to be on DARPA's DGX-1.

### Output

The output of this app is two values: one is the scan statistic value we've got and the other is the node id which has this statistic. The output file will be in txt format with the aforementioned two values.

We compare the output with python version of this app on the CPU.

## Performance and Analysis

How do you measure performance? What are the relevant metrics? Runtime? Throughput? Some sort of accuracy/quality metric?

### Implementation limitations

e.g.:

- Size of dataset that fits into GPU memory (what is the specific limitation?)
- Restrictions on the type/nature of the dataset

### Comparison against existing implementations

- Reference implementation (python? Matlab?)
- OpenMP reference

Comparison is both performance and accuracy/quality.



### Performance limitations

e.g., random memory access?

## Next Steps

### Alternate approaches

If you had an infinite amount of time, is there another way (algorithm/approach) we should consider to implement this?

### Gunrock implications

What did we learn about Gunrock? What is hard to use, or slow? What potential Gunrock features would have been helpful in implementing this workflow?

### Notes on multi-GPU parallelization

Graph partitioning will be a bottle neck on multi-GPU parallelization. Because we need the info of each node's two-hop neighbors, unbalanced workload will decrease the performance and increase the communication bottleneck. 

Dataset needs to be replicated if we cannot fit all two-hop neighors of each node on the same GPU.


### Notes on dynamic graphs

This workload have a dynamic-graph component as it can potentially take in time-series graph and try to find any abnormal behavior in any statistics change as mentioned in the referenced papers. We would need Gunrock to support dynamic graph in its advance and intersection operators. And this application would be changed to record all history scan statistics and try to find any significant changes with a certain threshold.

### Notes on larger datasets

For dataset which is too large to fit into a single GPU, we can leverage the multi-GPU implementation of Gunrock to make it work on multiple GPUs on a single node. The implementation won't change a lot since Gunrock already has good support in its multi-GPU implementation. For dataset which cannot fit multiple GPUs on a single node, we need distributed level of computation which Gunrock doesn't support yet. But open source libs such as NCCL and Horovad support thiswhich we can reference. Performance-wise, the way of partitioning the graph as well as the properties of a graph will effect the communication bottleneck. Since we need to calculate the total number of triangles each node is involved in, if we couldn't fit all neighorhood of a node on a single node, we need other compute resouces' help in solving that. Worst case senario is that the graph is fully connected, and we have to wait for the counting results from all other compute resources and sum them up. In this case, if we can do good scheduling of load balancing, we can minimize the communication bottleneck and reduce latency.

### Notes on other pieces of this workload

Other importand pieces of this work includes some statistics time series analysis on the dynamic changes of the graph. Gunrock currently doesn't support dealing with dynamic graphs. But other libraries such as cuSTINGER might solve the problem.

### Research value

This application takes the advantage of a classic traingle counding problem to solve a more complex statistics problem. Instead of directly using the exisitng solution, it's solved from a different angle. Instead of counting how many triangles there are in the whole graph, we count triangles from the node respective.
