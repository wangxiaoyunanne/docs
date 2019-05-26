---
title: Sparse Fused Lasso (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Sparse Fused Lasso

Given a graph where each vertex on the graph has a weight, _sparse fused lasso (SFL)_, also named _sparse graph trend filter (GTF)_, tries to learn a new weight for each vertex that is (1) sparse (most vertices have weight 0), (2) close to the original weight in the l2 norm, and (3) close to its neighbors' weight(s) in the l1 norm. This algorithm is usually used in main trend filtering (denoising). For example, an image (grid graph) with noisy pixels can be filtered with this algorithm to get a new image without the noisy pixels, which are "smoothed out" by its neighbors.
<https://arxiv.org/abs/1410.7690>

## Summary of Results

The SFL problem is mainly divided into two parts, computing residual graphs from maxflow and renormalizing the weights of the vertices. Maxflow is performed with the parallelizable lock-free push-relabel algorithm. For renormalization: each vertex has to compute which communities it belongs to, and normalize the weights with other vertices in the same community. SFL iterates on maxflow and renormalization kernels with a global synchronization in between them until convergence. Current analysis show that maxflow is the bottleneck of the whole workflow, with over 90% of the runtime being spent on the maxflow kernels.

GPU SFL runs ~2 times slower than the CPU benchmark on the largest dataset provided. On smaller datasets, GPU SFL is much slower because there just isn't enough work to fill up a GPU and leverage the compute we have available. Analyzing the runs on the larger datasets, show that the parametric maxflow on the CPU converges much faster than our parallel push-relabel max flow algorithm on the GPU. Investigating the parallelization of parametric maxflow is an interesting research challenge.

## Summary of Gunrock Implementation

The loss function is $0.5 \cdot \sum((y' - y)^2) + \lambda_1 \cdot \sum(|y_i' - y_j'|) + \lambda_2 \cdot \sum(|y_i'|)$, where $y$ is the input weight (observation) for each vertex and $y'$ (fitted weight) is the new weight for each vertex. $\lambda_1$ and $\lambda_2$ are required parameters to process the graph in SFL.

The input graph is specified in two files. The first file contains the original vertices' weights and the second file contains the directed graph connectivity without weights (edge pairs only). These two files and a edge_regularization_strength ($\lambda_1$) of the directed graph edge weights are the input to preprocessing. Two extra vertices, source and sink, are added to the original graph as well. They serve as two "labels" of different segments on the graph. This results in a graph where edges that connect to the source or sink have edge-weights as in the `vertices' weights` file, and the other edges are assigned an edge weight of $\lambda_1$.

The Gunrock implementation of this application has two parts. The first part is the maxflow algorithm. We choose a lock-free push-relabel maxflow formulation, which is well-suited for parallelization on a GPU with Gunrock. Computing a valid maxflow also implies a solution to the mincut problem, which is a segmentation of a graph into two pieces where the division is across a set of edges with the minimum possible weights. The output of this maxflow algorithm is (1) a residual graph where each edge weight is computed as `residual_capacity` equals `capacity - edge_flow`, and (2) a Boolean array that marks which vertices are reachable from the source after the mincut.

The second part is a renormalization of the residual graph and clustering based on reachability of the vertex. The renormalization is a process where (1) averages of the new weights of vertices that are grouped together as communities are computed, and (2) the new weights then subtract their own community averages. After the renormalization is done, this renormalized residual graph is passed into the maxflow again. Several iterations of maxflow then renormalization are needed before the new weights of different communities converge because vertices can be reassigned to different communities. In each of the SFL iterations, two non-overlapped subgraphs will be generated by maxflow/mincut, and thus the big communities in the last SFL iteration will have split into small communities. The vertices in a specific community will have the same new weights assigned to them.

The outputs will be the normalized values assigned to each vertex.

Lastly, these values will be passed into a soft-threshold function with $\lambda_2$ to achieve the sparse representation by dropping the small absolute values. More specifically, the new weight will be subtracted by $\lambda_2$ if the new weight is positive and larger than $\lambda_2$, or added by $\lambda_2$ if the new weight is negative and smaller than $-\lambda_2$. If the new weight is in between $-\lambda_2$ to $\lambda_2$, then the new weights will be 0.

Pseudocode for the core SFL algorithm is as follows:

```python
Load the graph and normalize edge weights

Repeat iteration till convergence:

    # Part 1: Maxflow
    do
        lockfree_op (num-repeats, V)
        global_relabeling_heuristic // update heights of all vertices
    while no more updates

    # Lock-free Push-Relabel operator
    def lockfree_op (num-repeats, V):
        for i from 1 to num-repeats do:
            for each vertex v in V:
                if v.excess > 0:
                    u := lowest_neighbor_in_residual_network (v)
                    if u.height < v.height:
                        Push (v, u)
                    else:
                        Relabel (v, u)

    # Finding lowest neighbor in residual network phase
    def lowest_neighbor_in_residual_network (v):
        min_height := infinity
        min_u := undefined
        for each e<v, u> of v:
            if e.residual_capacity <= 0:
                    continue;
            if min_height > u.height:
                    min_height := u.height
                    min_u := u
        return min_u

    # Push phase
    def Push (e<v, u>):
        move := min(e.residual_capacity, v.excess)
        v.excess -= move
        e.flow += move
        u.excess += move
        e.reverse.flow -= move

    # Relabel phase
    def Relabel (e<v, u>):
        v.height := u.height + 1

    # Min-cut
    Run a BFS to mark the accessibilities of vertices from the source vertex
    in the residue graph

    # Part 2: renormalization
    # Reset available community
    for each community comm:
        community_weights[comm] := 0
        community_sizes  [comm] := 0
        next_communities [comm] := 0

    # Accumulate the weights and count the number of vertices belong to the communities
    for each vertex v:
        if v is accessible from the source
            comm := next_communities[curr_communities[v]];
            if (comm == 0) update comm
            community_sizes[comm]++
            community_weights[comm] += weight[source -> v]
        else
            community_weights[comm] -= weight[v -> sink]
            community_sizes [comm] ++

    # Normalize community
    for each community comm:
        community_weights[comm] /= community_sizes[comm]
        community_accus [comm] += community_weights[comm]

    # Update the residual graph
    for each vertex v:
        comm = curr_communities[v]
        if (v is accessible from the source):
            weight[source->v] -= community_weights[comm]
            if (weight[source->v] < 0):
                Swap(-weight[source->v], weight[v->sink])
        else
            weight[v->sink] += community_weights[comm]
            if (weight[v->sink] < 0):
                Swap(weight[source->v], -weight[v->sink])

    # End of Repeats

# Part 3 Sparsify community_accus by \lambda_2
for i in len(each community_accus):
    if (community_accus < 0):
        community_accus[i] := min(community_accus[i] + \lambda_2, 0)
    else:
        community_accus[i] := max(community_accus[i] - \lambda_2, 0)

return community_accus
```


## How To Run This Application on DARPA's DGX-1

### Prereqs/input

CUDA should have been installed; `$PATH` and `$LD_LIBRARY_PATH` should have been
set correctly to use CUDA. The current Gunrock configuration assumes boost
(1.58.0 or 1.59.0) and Metis are installed; if not, changes need to be made in
the Makefiles. DARPA's DGX-1 has both installed when the tests are performed.


```shell
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock/tests/gtf
make clean && make
```

At this point, there should be an executable `gtf_main_<CUDA version>_x86_64`
in `tests/gtf/bin`.

The testing is done with <https://github.com/wetliu/gunrock/tree/master> using `stable` branch at commit `a2159ce060d4dbc89a88f8d5fb0fd0d571ba907b`
(Nov. 14, 2018), using CUDA 10.1 with NVIDIA driver 390.30.

### HIVE Data Preparation

Prepare the data; skip this step if you are just running the sample dataset.

Refer to `parse_args()` in `taxi_tsv_file_preprocessing.py` for dataset preprocessing options.

If you don't have the `e` or `n` files:


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
```

Two files, `e` and `n`, are generated.

Set $\lambda_1$ (see equation above) in generate_graph.py. If you have the `e` and `n` files, generated by the above commands or copied from `/raid/data/hive/gtf/{small, medium, large}`, you can do the following (`/raid/data/hive/gtf/small/` as an example):

```shell
cd gunrock/tests/gtf/_data
cp /raid/data/hive/gtf/small/n .
cp /raid/data/hive/gtf/small/e .
python generate_graph.py
```

A file called `std_added.mtx` is generated for Gunrock input.

### Running the application
```
--lambda_2 is the sparsity regularization strength
```
Sample command line with argument.
```shell
./bin/test_gtf_10.0_x86_64 market ./_data/std_added.mtx --lambda_2 3
```
Please also note that we have set the number of MF iterations to 10000 as a default. In larger graphs, a larger number may be required.

### Output

The code will output two files in the current directory. One is called `output_pr.txt` (for CPU reference) and the other is called `output_pr_GPU.txt` (for GPU SFL with push-relabel backend).
Each vertex's new weight will be stored in each line of the two files. These outputs could be further processed into the resulting heatmap.
The printout after running `gtf_main_<CUDA version>_x86_64` includes the timing of the application.

Sample `txt` output:

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

Sample output on console:

```
______CPU reference algorithm______                                                                                                                                  [9/1944]
offset is 58522 num edges 76366
!!!!!!!!!! avg is -0.876037
Iteration 0
...
Iteration 11
-----------------------------------
Elapsed: 5500.730991 ms
in side that weird function1
offset in GPU preprocess is 58522 num edges 76366
avg in GPU preprocess is -0.876037
Using advance mode LB
Using filter mode CULL
Using advance mode LB
Using filter mode CULL
offset is 58522 num edges 76366
h_community_accus is -0.876037
______GPU SFL algorithm____
enact calling successfully!!!!!!!!!!!
-----------------------------------
Run 0, elapsed: 3341.358185 ms, #iterations = 12
transfering to host!!!: 8924
[gtf] finished.
 avg. elapsed: 3341.358185 ms
 iterations: 0
 min. elapsed: 3341.358185 ms
 max. elapsed: 3341.358185 ms
 load time: 138.952 ms
 preprocess time: 342.184000 ms
 postprocess time: 0.258923 ms
 total time: 3845.412016 ms

```

## Performance and Analysis

We measure the runtime and loss function $0.5 \cdot \sum((y' - y)^2) + \lambda_1 \cdot \sum(|y_i' - y_j'|) + \lambda_2 \cdot \sum(|y_i'|)$, where $y$ is the input weight (observation) for each vertex and $y'$ (fitted weight) is the new weight for each vertex.

### Implementation limitations

- **Memory usage** Each edge in the graph needs at least 28 bytes of GPU device memory: 64 bits for the residual_capacity value, 64 bits for the capacity value, 64 bits for the flow value, 16 bits for the index of the reverse edge. Each node in the graph needs at least 16 bytes of GPU device memory: 64 bits for the excess value, 16 bits for the height value and 16 bits for the index of the lowest neighbor.

- **Data type** For edges we have the following arrays: residual_capacity, capacity, flow, reverse. For nodes we have the following arrays: height, excess, lowest_neighbor. Residual_capacity, capacity, flow and excess arrays and all computation around them are double-precision floating point values (64-bit `double` in C/C++). We use an epsilon value of 1e-6 to compare floating-point numbers to zero. Reverse, height, and lowest_neighbor arrays and all computation around them are 32-bit integer values.

### Comparison against existing implementations
Graphtv is an official implementation of the sparse fused lasso algorithm with a parametric maxflow backend. It is a CPU serial implementation <https://www.cs.ucsb.edu/~yuxiangw/codes/gtf_code.zip>. The Gunrock GPU runtime is measured between the application enactor and it is an output of the application.

All datasets in the table below are generated from `taxi-small.tar.gz` with different timestamps. $\sim 20K$-node graph is used as a sample test, $\sim 300K$ is a medium-sized dataset, and the largest available is $\sim 600K$ nodes.

| Dataset | time starts | time ends | $\cardinality{E}$ | $\cardinality{V}$ | Graphtv runtime | Gunrock GPU runtime |
|--------------|---------------------|--------------------|----------|----------|------|---|
| NY Taxi-20K | 2011-06-26 12:00:00 |2011-06-26 14:00:00 | 20349 | 8922 | 0.11s | 4.98s |
| NY Taxi-300K | 2011-06-26 00:00:00 |2011-06-27 00:00:00 | 293259 | 107064 | 8.71s | 143.91s |
| NY Taxi-600K | 2011-06-19 00:00:00 |2011-06-27 00:00:00 | 588211 | 213360 | 103.62s | 211.07 |

| Dataset | time starts | time ends | $\cardinality{E}$ | $\cardinality{V}$ | Graphtv loss | Gunrock GPU loss |
|--------------|---------------------|--------------------|----------|----------|-------------------|-------------------|
| NY Taxi-20K | 2011-06-26 12:00:00 |2011-06-26 14:00:00 | 20349 | 8922 | 132789.32 | 132789.32 |
| NY Taxi-300K | 2011-06-26 00:00:00 |2011-06-27 00:00:00 | 293259 | 107064 | 1094282.51 | 1094282.51 |
| NY Taxi-600K | 2011-06-19 00:00:00 |2011-06-27 00:00:00 | 588211 | 213360 | 1670947.26 | 1670947.26 |

### Performance limitations

We observe a slowdown when we compare Graphtv and Gunrock's current SFL implementation on the three datasets provided. On the smaller datasets there just isn't enough work to fill up a GPU and leverage the compute we have available. Even on the larger dataset we do not see a speed-up because of superior serial algorithm within the CPU implementation of maxflow that converges much earlier than our parallel push-relabel max flow algorithm on the GPU.

We make a detailed performance analysis on the `NY Taxi` dataset with time from `2011-06-19 00:00:00` to `2011-06-27 00:00:00`:

- The maxflow algorithm uses serial global relabeling and gap heuristics performed in device memory by one CUDA thread. The profiling shows this heuristics computation takes about 42% of MF's whole computation time, while the rest (58%) is push relabel (precisely: Gunrock `RepeatFor` operator running the lock-free push-relabel operator). Since maxflow takes up about 96% of SFL's computation time, this makes the SFL kernel launch-overhead-bound. Further optimization of the maxflow algorithm is discussed below in the "maxflow optimization opportunities" paragraph.

- This dataset, with $\sim 213k$ vertices and $\sim 588k$ edges, is still too small to fill up the GPU. It makes the kernel launching overhead issue much worse than it would with larger graphs.

- There are some engineering limitations in our current implementation:

    1. The global relabeling and gap heuristics in maxflow are performed by one
    thread; although they only run once per a few 1000 iterations, these
    procedures take almost half the computation time.

    2. The current min-cut finding and renormalization are serial on GPU (i.e.,
    only using a single thread to perform the computation).

### Maxflow lessons learned

- Our first approach to the maxflow problem was the push-relabel algorithm in its simplest form. This implementation used 3 operators with 2 synchronizations between them. Because we had a large number of iterations of this algorithm, our computation was dominated by kernel-launch overhead.

- To reduced the number of kernels and synchronizations, we implemented push-relabel with a lock-free approach proposed by Bo Hong in "A Lock-free Multi-threaded Algorithm for the Maximum Flow Problem"
<http://people.cs.ksu.edu/~wls77/weston/projects/cis598/hong.pdf>. This modification allowed us
to reduce the operators down to only one lock-free push-relabel operator and one
synchronization call.

- Our next optimization was reducing the iteration count of push-relabel, thus reducing the number of synchronizations. For this purpose, we used the Gunrock operator `RepeatFor`. The `RepeatFor` operator allowed us to merge several kernel launches into one stacked kernel with a global barrier between each kernel call. We have also experimented with the new CUDA 10 feature called `cudaGraphs` in attempt to reduce the overall kernel launch overhead by creating a task graph of all kernels, but quickly found that a stacked kernel approach worked the best. Now instead of launching hundreds of thousands of iterations (thus kernels) until convergence, we only have to perform tens of iterations with hundreds of thousands of repeated kernels within each iteration.

## Next Steps

### Maxflow optimization opportunities

- We are looking at optimization to speed up the global reabeling-gap heuristic.
  It is currently performed in the Device memory by one thread. This algorithm is based on BFS, which could be parallelized as well.

- We would like to explore the parallelization of another approach, the
  Boykov Kolmogorov algorithm proposed by Yuri Boykov and Vladimir Kolmogorov in
  "An Experimental Comparison of Min-Cut/Max-Flow Algorithms for Energy
  Minimization in Vision" <http://www.csd.uwo.ca/faculty/yuri/Papers/pami04.pdf>.
  Instead of finding a new augmenting path or edge (push-relabel)
  on the graph in each iteration, the Boykov Kolmogorov algorithm keeps the
  already found items in two search trees. We would like to use this idea
  in our push-relabel implementation as well.

### Gunrock implications

SFL is the first application in Gunrock that calls another application (maxflow). Some common data pre-processing on the CPU requires better designs of the APIs to facilitate this usage. For example, `gtf_enactor` needs to call `mf_problem.reset()`, but because the current maxflow code uses CPU to preprocess the graph, SFL has to transfer the data back and forth between CPU and GPU. Using GPU to preprocess the graph for maxflow would be preferable.

### Notes on multi-GPU parallelization

To parallelize the push-relabel algorithm across multiple GPUs, all arrays related to the graph have to be stored on each GPU. Moreover, the GPUs have to update their adjacent neighbors' data. Because the push-relabel algorithm needs to store at least three arrays of size $O(|E|)$ and three arrays of size $O(|V|)$, communicating so much data efficiently between GPUs is challenging.

The SFL renormalization should be able to be easily parallelized across different GPUs, because it is array operations only. However, extra data transfer is necessary if the graph is not copied across multiple GPUs.

### Notes on dynamic graphs

Push relabel is not directly related to dynamic graphs. But it should be able to run on a dynamic graph, provided the source and the sink are given at the beginning of the algorithm and the way to access all the nodes and the edges is the same. Capacities of edges from the previous graph can be used as a good starting point, if the edges and the node ids are consistent and the graph is not dramatically changed.

However, SFL would be a significant challenge with dynamic graphs (the topology of the graph would change). The residual graph includes a swapping edge value (see pseudocode above) and we need to know characteristics of the new graph in order to allocate enough memory space for the new edges and vertices.

### Notes on larger datasets

SFL renormalization can be done without having its temporary arrays on the same GPU, but extra communication costs are necessary if these arrays are in different GPUs' global memories. Unified memory can also be used to handle larger datasets by oversubscribing and paying the cost of CPU to GPU transfer. Gunrock needs no specific new support to support SFL renormalization on larger datasets.

### Research opportunities

Prof. Sharpnack indicates that this implementation could be generalized to multi-graph fused lasso. The idea is to set multiple edge values for the edges connecting to source/sink, while keeping the graph topology and edge values $(\lambda_1)$ for the edges in the original graph (excluding source and sink) the same.