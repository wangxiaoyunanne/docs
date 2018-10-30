---
title: Sparse Graph Trend Filtering (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Sparse Graph Trend Filtering

Given each vertex on the graph has its own weight, the sparse graph trend filtering tries to learn a weight that is (1) sparse (mostly of the vertices have weights 0), (2) close to the original weight in l2 norm, and (3) close to its neighbors' weight(s) in l1 norm. This algorithm is usually used in main trend filtering (denoising). The loss function is `0.5 * sum(y' - y)^2 + lambda1 * sum|yi' - yj'| + lambda2 * sum|yi'|`, where y
is the input value for each vertex and y' is the output denoising value for each vertex.
<https://arxiv.org/abs/1410.7690>

## Summary of Results

(fill this in)

## Summary of Gunrock Implementation

The graph is preprocessed by two files. The first file contains the original vertices' weights and the second file contains the directed graph connectivity without weights. These two files and a edge weight parameter (lambda1) are the input to the preprocessing file.

The Gunrock implementation of this application has two parts. The first part is the maxflow algorithm. We choose a push-relabel maxflow formulation, which is well-suited to parallelize on GPU with Gunrock. The output of this maxflow algorithm is (1) a residual graph where each edge value is computed as capacity `input edge weight - edge_flow`, and (2) a min-cut of the vertices, a Boolean array indicating if the this vertex is reachable from the source given the residual graph.

The second part is a renormalization of the residual graph and clustering based on reachability of the vertex. After the renormalization is done, this renormalized residual graph is passed into the maxflow again. Several iterations between maxflow and renormalization are needed before the normalized values of different labels converge.

The outputs will be the normalized values assigned to each vertex.

Lastly, these values will be passed into a soft-threshold function with `lambda2` to achieve the sparse representation by dropping the small absolute values.

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

CUDA should have been installed; `$PATH` and `$LD_LIBRARY_PATH` should have been
set correctly to use CUDA. The current Gunrock configuration assumes boost
(1.58.0 or 1.59.0) and metis are installed; if not, changes need to be made in
the Makefiles. DARPA's DGX-1 has both installed when the tests are performed.

```shell
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

The testing is done with Gunrock using `dev-refactor` branch at commit `2699252`
(Oct. 18, 2018), using CUDA 9.1 with NVIDIA driver 390.30.

### HIVE Data Preparation

Prepare the data; skip this step if you are just running the sample dataset.

Refer to `parse_args()` in taxi_tsv_file_preprocessing.py for dataset preprocessing options.
Set the lambda1 (see equation above) in generate_graph.py for Gunrock.

```shell
cd gunrock/tests/gtf/_data

export TOKEN= # get this Authentication TOKEN from https://api-token.hiveprogram.com/#!/user
mkdir -p _data
wget --header "Authorization:$TOKEN" \
  https://hiveprogram.com/data/_v0/sparse_fused_lasso/taxi/taxi-small.tar.gz
tar -xzvf taxi-small.tar.gz && rm -r taxi-small.tar.gz
mv taxi-small _data/

wget --header "Authorization:$TOKEN" \
  https://hiveprogram.com/data/_v0/sparse_fused_lasso/taxi/taxi-1M.tar.gz
tar -xzvf taxi-1M.tar.gz && rm -r taxi-1M.tar.gz
mv taxi-1M _data/

python taxi_tsv_file_preprocessing.py
python generate_graph.py
```

Then three files are generated. The files `e` and `n` are for benchmarks, and `std_added.mtx` is for Gunrock input.

### Running the application
```
market is the graph type for Gunrock
--lambda2 is the sparsity regularization constant
```
Sample command line with argument.
```shell
./bin/test_gtf_10.0_x86_64 market ./_data/std_added.mtx --lambda2 3
```

### Output

The code will output two files in the current directory. One is called `output_pr.txt` (for CPU reference) and the other is called `output_pr_GPU.txt`.
Each vertex's new weight will be stored in each line of the two files. These outputs could be further processed into the resulting heatmap.

Sample output is
```
0
0
0
0
0
0
-11.375
-0.307292
0
```

## Performance and Analysis

We measure the runtime, and accuracy, and loss function `0.5 * sum(y' - y)^2 + lambda1 * sum|yi' - yj'| + lambda2 * sum|yi'|`, where `y` is the old weight per vertex and `y'` is the new weight per vertex.

### Implementation limitations

The time is mostly spent on maxflow computation. Each iteration of the GTF calls a maxflow. The time spent on maxflow vs. the rest of the GTF post-processing is around 100:1. The maxflow implementation has room for further optimization; we expect to have shorter runtime on maxflow in the future. The time complexity of the maxflow is `O(VE2)`, while the time complexity of the GTF renormalization is `O(V+E)`.

### Comparison against existing implementations
Graphtv is a graph trend filtering algorithm with parametric maxflow backend. It is CPU serial implementation. We measure accuracy with a side-by-side comparison of the output weights per node.

| DataSet       | time starts         | time ends          | #E       | #V       | graphtv runtime   | Gunrock GPU runtime |
|-------------- |--------------------:|-------------------:|---------:|---------:|------------------:| -------------------:|
| NY Taxi-small | 2011-06-26 12:00:00 |2011-06-26 14:00:00 | 20349    | 8922     | 0.11s             |                     |
| NY Taxi-small | 2011-06-26 00:00:00 |2011-06-27 00:00:00 | 293259   | 107064   | 8.71s             |                     |
| NY Taxi-1M    | 2011-06-19 00:00:00 |2011-06-27 00:00:00 | 588211   | 213360   | 103.62s           |                     |


### Performance limitations

e.g., random memory access? talks about MF more?

## Next Steps

### Alternate approaches(Done)

> If you had an infinite amount of time, is there another way (algorithm/approach) we should consider to implement this?

For CPU, the parametric maxflow algorithm works pretty well, but it is not parallelizable to GPU. The push-relabel algorithm we have on Gunrock's maxflow should be the best implementation among the parallelizable algorithms on GPU.

### Gunrock implications

> What did we learn about Gunrock? What is hard to use, or slow? What potential Gunrock features would have been helpful in implementing this workflow?

Python interfaces will help the students in statistics learn and utilize Gunrock for graph analysis.

### Notes on multi-GPU parallelization

> What will be the challenges in parallelizing this to multiple GPUs on the same node?
>
> Can the dataset be effectively divided across multiple GPUs, or must it be replicated?

### Notes on dynamic graphs

(Only if appropriate)

> Does this workload have a dynamic-graph component? If so, what are the implications of that? How would your implementation change? What support would Gunrock need to add?

### Notes on larger datasets

> What if the dataset was larger than can fit into GPU memory or the aggregate GPU memory of multiple GPUs on a node? What implications would that have on performance? What support would Gunrock need to add?

### Notes on other pieces of this workload

> Briefly: What are the important other (non-graph) pieces of this workload? Any thoughts on how we might implement them / what existing approaches/libraries might implement them?

### Research opportunities

> "{what you've done with respect to this workflow / what you could do} that you think has research value and could lead to a paper". We should write those down now when they're fresh in our minds. This is less for DARPA and more for us, for our discussion. I know not every one of these workflows will lead to a research advance. But there are research advances in implementing the workflow AND implementing interesting parts of the workflow (e.g., sparse data structures) AND other things we could use pieces of the workflow to solve (e.g., auction algorithm)
