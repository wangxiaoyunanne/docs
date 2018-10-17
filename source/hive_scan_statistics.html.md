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
cd ../tests/scan_statistics/
make clean && make
</pre>

### Running the application
Application specific parameters:
 
<pre>
    --labels-file
    file name containing node ids and their locations.
</pre>
 
Example command-line:

<pre>
location.mtx is a graph based on chesapeake.mtx dataset
./bin/test_geo_10.0_x86_64 --graph-type=market --graph-file=./geolocation.mtx --labels-file=./locations.labels
</pre>

Note: This run / these runs need to be on DARPA's DGX-1.

### Output

What is output when you run? Output file? JSON? Anything else? How do you extract relevant statistics from the output?

How do you make sure your output is correct/meaningful? (What are you comparing against?)

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

What will be the challenges in parallelizing this to multiple GPUs on the same node?

Can the dataset be effectively divided across multiple GPUs, or must it be replicated?

### Notes on dynamic graphs

(Only if appropriate)

Does this workload have a dynamic-graph component? If so, what are the implications of that? How would your implementation change? What support would Gunrock need to add?

### Notes on larger datasets

What if the dataset was larger than can fit into GPU memory or the aggregate GPU memory of multiple GPUs on a node? What implications would that have on performance? What support would Gunrock need to add?

### Notes on other pieces of this workload

Briefly: What are the important other (non-graph) pieces of this workload? Any thoughts on how we might implement them / what existing approaches/libraries might implement them?
