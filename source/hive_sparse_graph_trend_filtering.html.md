---
title: Template for HIVE workflow report

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Sparse Graph Trend Filtering

Given each vertex on the graph has its own weight, the sparse graph trend filtering tries to learn a weight that is (1) sparse (mostly of the vertices have weights 0), (2) close to the original weight in l2 norm, and (3) close to its neighbors' weight(s) in l1 norm. This algorithm is usually used in main trend filtering (denoising).
(https://arxiv.org/abs/1410.7690)

## Summary of Results

## Summary of Gunrock Implementation

The graph is preprocessed by two files. The first file contains the original vertices weights and the second file contains the directed graph connectivity without weights. These two files and a edge weight parameter (lambda1) are the input to the preprocessing file.  

The Gunrock implementation of this application has two parts. The first part is the maxflow algorithm. We decide to utilize a push-relabel algorithm, which is perfect to parallelize on GPU with Gunrock. The output of this maxflow algorithm is (1) residual graph where each edge value is computed as capacity (input edge weight) - edge_flow, and (2) min-cut of the vertices, an array that is boolean type indicating if the this vertex is reachable from the source given the residual graph.

The second part is a renormalization of the residual graph and clustering based on reachability of the vertex. After the renormalization is done, this renormalized residual graph is passed into the maxflow again. Several iterations between maxflow and renormalization are needed before the normalized values of different labels converge.   

The outputs will be the normalized values assigned to each vertex.

Lastly, these values will be passed into soft-threshold function with lambda2 to achieve the sparse representation by dropping the small absolute values.

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
cd ../tests/gtf
make
```
At this point, there should be an executable `gtf_main_<CUDA version>_x86_64`
in `tests/gtf/bin`.

The datasets are assumed to have been placed in `/raid/data/hive`, and converted
to proper matrix market format (.mtx). At the time of testing, `ca`, `amazon`,
`akamai`, and `pokec` are available in that directory. `ca` and `amazon` are taken
from PNNL's implementation, and originally use 0-based vertex index; 1 is added
to each vertex Id to make them proper .mtx files.

The testing is done with Gunrock using `dev-refactor` branch at commit `2699252`
(Oct. 18, 2018), using CUDA 9.1 with NVIDIA driver 390.30.


### Running the application

We will attach a run file in the repository as well. The command is
<code>

<code>

Note: This run / these runs need to be on DARPA's DGX-1.

### Output

The code will output two files in the current directory. One is called output_pr.txt and the other is called ouput_pr_GPU.txt.
Each vertex's new weight will be stored in each line of the two files. These output could be further processed to the heatmap.

## Performance and Analysis

We will measure the runtime, and accuracy, and loss function 0.5*sum(y' - y)^2 + lambda1*sum|yi' - yj'| + lambda2 * sum|yi'|,
where y is old weight per vertex and y' is the new weight per vertex.

### Implementation limitations

The time is mostly spent on Maxflow algorithm. Each iteration of the GTF, a maxflow is called. The time spent on maxflow vs
the rest of the GTF post-processing is around 100:1. It is because of the maxflow algorithm is not yet optimzed on GPU implementation.
We expect to have shorter runtime on the maxflow in the future. The time complexity of the O(VE2), while the time complexity of the GTF
renormalization is O(V+E).

### Comparison against existing implementations
Graphtv is the graph trend filtering algorithm with parametric maxflow backend. It is CPU serial implementation.
The metrics to measure the accuracy is side by side comparison of the output weights per node.
| DataSet       | time starts         | time ends          | #E       | #V       | graphtv runtime   | Gunrock GPU runtime |
|-------------- |---------------------|--------------------|----------|--------- |-------------------| --------------------|
| NY Taxi-small | 2011-06-26 12:00:00 |2011-06-26 14:00:00 | 20349    | 8922     | 0.11s             |                     |
| NY Taxi-small | 2011-06-26 00:00:00 |2011-06-27 00:00:00 | 293259   | 107064   | 8.71s             |                     |
| NY Taxi-1M    | 2011-06-19 00:00:00 |2011-06-27 00:00:00 | 588211   | 213360   | 8.71s             |                     |


### Performance limitations

e.g., random memory access? talks about MF more?

## Next Steps

### Alternate approaches(Done)

If you had an infinite amount of time, is there another way (algorithm/approach) we should consider to implement this?

For CPU, the parametric maxflow algorithm works pretty well, but it is not parallelizable to GPU. The push-relabel algorithm we have on Gunrock's maxflow should be the best implementation among the parallelizable algorithms on GPU.

### Gunrock implications

What did we learn about Gunrock? What is hard to use, or slow? What potential Gunrock features would have been helpful in implementing this workflow?

Python interfaces will help the students in statistics learn and utilize Gunrock for graph analysis.

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
