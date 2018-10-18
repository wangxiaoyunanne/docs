---
title: Geolocation (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Geolocation

Infers user locations using the location (latitude, longitude) of friends through spatial label propagation. Given a graph `G`, geolocation examines each vertex `v`'s neighbors and computes the spatial median of neighbors' location list, the output is a list of predicted locations for all vertices with unknown locations.

## Summary of Results

One or two sentences that summarize "if you had one or two sentences to sum up your whole effort, what would you say". I will copy this directly to the high-level executive summary in the first page of the report. Talk to JDO about this. Write it last, probably.

## Summary of Gunrock Implementation

We implemented Geolocation using two `compute` operators as `ForAll()`. The first `ForAll()` is a `gather` operation, gathering all the values of neighbors with known locations for an active vertex `v`, and the second `ForAll()` uses those values to compute the `spatial_center` where the spatial center of a list points is the center of those points on earth's surface.

<pre>
def gather_op(Vertex v):
    for neighbor in G.neighbors(v):
	if isValid(neigbor.location):
	    locations_list[v].append(neigbor.location)

def compute_op(Vertex v):
    if !isValid(v.location):
	v.location = spatial_center(locations_list[v])
</pre>

See `gunrock/app/geo/geo_spatial.cuh` for details on the spatial center implementation.

## How To Run This Application on DARPA's DGX-1

### Prerequisites

<pre>
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock
mkdir build
ctest ..
cd ../tests/geo/
make clean && make
</pre>

### Data Preparation

Prepare the data, skip this step if you are just running the sample dataset. Assuming we are in `tests/geo` directory:

<pre>
export TOKEN= # get this Authentication TOKEN from https://api-token.hiveprogram.com/#!/user
wget --header "Authorization:$TOKEN" https://hiveprogram.com/data/_v0/geotagging/instagram/instagram.tar.gz
tar -xzvf instagram.tar.gz && rm instagram.tar.gz
cd instagram/graph
cp ../../generate-data.py ./
python generate-data.py
</pre>

This will generate two files: `instagram.mtx` and `instagram.labels`, which can be used as an input to the geolocation app.

### Running the application

Application specific parameters:

<pre>
    --labels-file
        file name containing node ids and their locations.

    --geo-iter
        number of iterations to run geolocation or (stop condition).
        (default = 3)

    --geo-complete
        runs geolocation for as many iterations as required to find locations for all nodes.
        (default = false because it uses atomics)
</pre>

Example command-line:

<pre>
# geolocation.mtx is a graph based on chesapeake.mtx dataset
./bin/test_geo_10.0_x86_64 --graph-type=market --graph-file=./geolocation.mtx --labels-file=./locations.labels --geo-iter=2 --geo-complete=false
</pre>

Sample input (labels):

<pre>
% Node Label Label(optional)
39 2 2
1 37.7449063493 -122.009432884
2 37.8668048274 -122.257973253
4 37.869112506 -122.25910604
6 37.6431858915 -121.816156983
11 37.8652346572 -122.250634008
19 38.2043433677 -114.300341275
21 36.7582225593 -118.167916598
22 33.9774659389 -114.886512278
30 39.2598884729 -106.804662071
31 37.880443573 -122.230147039
39 9.4276164485 -110.640705659
</pre>

Sample output:

<pre>
Loading Matrix-market coordinate-formatted graph ...
Reading from ./geolocation.mtx:
  Parsing MARKET COO format edge-value-seed = 1539674096
 (39 nodes, 340 directed edges)...
Done parsing (0 s).
  Converting 39 vertices, 340 directed edges ( ordered tuples) to CSR format...
Done converting (0s).
Labels File Input: ./locations.labels
Loading Labels into an array ...
Reading from ./locations.labels:
  Parsing LABELS
 (39 nodes)
Done parsing (0 s).
Debugging Labels -------------
    locations[ 0 ] = < 37.744907 , -122.009430 >
    locations[ 1 ] = < 37.866806 , -122.257973 >
    locations[ 2 ] = < nan , nan >
    locations[ 3 ] = < 37.869114 , -122.259109 >
    locations[ 4 ] = < nan , nan >
    locations[ 5 ] = < 37.643185 , -121.816154 >
    locations[ 6 ] = < nan , nan >
    locations[ 7 ] = < nan , nan >
    locations[ 8 ] = < nan , nan >
    locations[ 9 ] = < nan , nan >
    locations[ 10 ] = < 37.865234 , -122.250633 >
    locations[ 11 ] = < nan , nan >
    locations[ 12 ] = < nan , nan >
    locations[ 13 ] = < nan , nan >
    locations[ 14 ] = < nan , nan >
    locations[ 15 ] = < nan , nan >
    locations[ 16 ] = < nan , nan >
    locations[ 17 ] = < nan , nan >
    locations[ 18 ] = < 38.204342 , -114.300339 >
    locations[ 19 ] = < nan , nan >
    locations[ 20 ] = < 36.758221 , -118.167915 >
    locations[ 21 ] = < 33.977467 , -114.886513 >
    locations[ 22 ] = < nan , nan >
    locations[ 23 ] = < nan , nan >
    locations[ 24 ] = < nan , nan >
    locations[ 25 ] = < nan , nan >
    locations[ 26 ] = < nan , nan >
    locations[ 27 ] = < nan , nan >
    locations[ 28 ] = < nan , nan >
    locations[ 29 ] = < 39.259888 , -106.804665 >
    locations[ 30 ] = < 37.880444 , -122.230148 >
    locations[ 31 ] = < nan , nan >
    locations[ 32 ] = < nan , nan >
    locations[ 33 ] = < nan , nan >
    locations[ 34 ] = < nan , nan >
    locations[ 35 ] = < nan , nan >
    locations[ 36 ] = < nan , nan >
    locations[ 37 ] = < nan , nan >
    locations[ 38 ] = < 9.427616 , -110.640709 >
__________________________
______ CPU Reference _____
--------------------------
 Elapsed: 0.267029
Initializing problem ...
Number of nodes for allocation: 39
Initializing enactor ...
Using advance mode LB
Using filter mode CULL
nodes=39
__________________________
0        0       0       queue3          oversize :      234 ->  342
0        0       0       queue3          oversize :      234 ->  342
--------------------------
Run 0 elapsed: 11.322021, #iterations = 2
Node [ 0 ]: Predicted = < 37.744907 , -122.009430 > Reference = < 37.744907 , -122.009430 >
Node [ 1 ]: Predicted = < 37.866806 , -122.257973 > Reference = < 37.866806 , -122.257973 >
Node [ 2 ]: Predicted = < 9.427616 , -110.640709 > Reference = < 9.427616 , -110.640709 >
Node [ 3 ]: Predicted = < 37.869114 , -122.259109 > Reference = < 37.869114 , -122.259109 >
Node [ 4 ]: Predicted = < 23.634264 , -115.614845 > Reference = < 23.634264 , -115.614845 >
Node [ 5 ]: Predicted = < 37.643185 , -121.816154 > Reference = < 37.643185 , -121.816154 >
Node [ 6 ]: Predicted = < 37.743797 , -122.011337 > Reference = < 37.864948 , -122.250595 >
Node [ 7 ]: Predicted = < 33.535606 , -116.003227 > Reference = < 33.535610 , -116.003235 >
Node [ 8 ]: Predicted = < 23.754425 , -115.802628 > Reference = < 23.754425 , -115.802628 >
Node [ 9 ]: Predicted = < 9.427616 , -110.640709 > Reference = < 9.427616 , -110.640709 >
Node [ 10 ]: Predicted = < 37.865234 , -122.250633 > Reference = < 37.865234 , -122.250633 >
Node [ 11 ]: Predicted = < 10.187306 , -110.838608 > Reference = < 37.744308 , -122.008415 >
Node [ 12 ]: Predicted = < 37.744141 , -122.010750 > Reference = < 37.744141 , -122.010750 >
Node [ 13 ]: Predicted = < 9.427616 , -110.640709 > Reference = < 9.427616 , -110.640709 >
Node [ 14 ]: Predicted = < 23.826635 , -112.263268 > Reference = < 23.826635 , -112.263268 >
Node [ 15 ]: Predicted = < 23.826635 , -112.263268 > Reference = < 23.826635 , -112.263268 >
Node [ 16 ]: Predicted = < 9.427615 , -110.640709 > Reference = < 23.755602 , -115.803055 >
Node [ 17 ]: Predicted = < 23.826635 , -112.263268 > Reference = < 23.826635 , -112.263268 >
Node [ 18 ]: Predicted = < 38.204342 , -114.300339 > Reference = < 38.204342 , -114.300339 >
Node [ 19 ]: Predicted = < 9.427616 , -110.640709 > Reference = < 9.427616 , -110.640709 >
Node [ 20 ]: Predicted = < 36.758221 , -118.167915 > Reference = < 36.758221 , -118.167915 >
Node [ 21 ]: Predicted = < 33.977467 , -114.886513 > Reference = < 33.977467 , -114.886513 >
Node [ 22 ]: Predicted = < 37.744621 , -122.008858 > Reference = < 37.744621 , -122.008873 >
Node [ 23 ]: Predicted = < 9.427616 , -110.640709 > Reference = < 9.427616 , -110.640709 >
Node [ 24 ]: Predicted = < 9.427616 , -110.640709 > Reference = < 37.744907 , -122.009430 >
Node [ 25 ]: Predicted = < 9.427616 , -110.640709 > Reference = < 9.427616 , -110.640709 >
Node [ 26 ]: Predicted = < 33.934067 , -114.746063 > Reference = < 33.933800 , -114.745186 >
Node [ 27 ]: Predicted = < 21.715958 , -112.579689 > Reference = < 21.715958 , -112.579689 >
Node [ 28 ]: Predicted = < 9.427616 , -110.640709 > Reference = < 9.427616 , -110.640709 >
Node [ 29 ]: Predicted = < 39.259888 , -106.804665 > Reference = < 39.259888 , -106.804665 >
Node [ 30 ]: Predicted = < 37.880444 , -122.230148 > Reference = < 37.880444 , -122.230148 >
Node [ 31 ]: Predicted = < 33.975193 , -114.890976 > Reference = < 33.975193 , -114.890976 >
Node [ 32 ]: Predicted = < 33.981956 , -114.889862 > Reference = < 33.981964 , -114.889854 >
Node [ 33 ]: Predicted = < 37.744907 , -122.009430 > Reference = < 37.744907 , -122.009430 >
Node [ 34 ]: Predicted = < 37.744907 , -122.009430 > Reference = < 37.744907 , -122.009430 >
Node [ 35 ]: Predicted = < 37.864429 , -122.199409 > Reference = < 37.864429 , -122.199409 >
Node [ 36 ]: Predicted = < 23.755602 , -115.803055 > Reference = < 37.807079 , -122.134163 >
Node [ 37 ]: Predicted = < 37.053715 , -115.913658 > Reference = < 37.053719 , -115.913628 >
Node [ 38 ]: Predicted = < 9.427616 , -110.640709 > Reference = < 9.427616 , -110.640709 >
0 errors occurred.
[geolocation] finished.
 avg. elapsed: 11.322021 ms
 iterations: 2
 min. elapsed: 11.322021 ms
 max. elapsed: 11.322021 ms
 load time: 68.671 ms
 preprocess time: 496.136000 ms
 postprocess time: 0.463009 ms
 total time: 508.110046 ms
</pre>

### Output

When `quick` mode is disabled, the application performs the CPU Reference implementation, which is used to validate the results from the GPU implementation. Geolocation application also supports the `quiet` mode, which allows user to skip the output and just report the performance metrics (note, this will run CPU implementation in the background without any output).

## Performance and Analysis

How do you measure performance? What are the relevant metrics? Runtime? Throughput? Some sort of accuracy/quality metric?

### Implementation limitations

One of the biggest limitation is that we are currently using `|V|x|V|` to store all the neighbors locations for all the vertices. For a graph of size `60K` nodes, it can take approximately `16GB` of a GPU memory. In the worst case scenario, we have a fully connected graph, but in most real world we won't see this connectivity within a network. Some tricks can be done to determine the degree of each vertex before hand and allocate just enough memory required to store the locations of valid neighbors. For the sake of complexity and time, we currently using `|V|x|V|` size array.

### Comparison against existing implementations

- [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/geotagging.git)
- [GTUSC implementation](https://gitlab.hiveprogram.com/gtusc/geotagging)

Comparison is both performance and accuracy/quality.

### Performance limitations

e.g., random memory access?

## Next Steps

### Alternate approaches

- **Neighborhood Reduce w/ Spatial Center:** We can perform better load balancing by opting in for neighbor reduce (`advance` operator + `cub::DeviceSegmentedReduce`) instead of using a compute operator. In graphs where the degree of a nodes could vary a lot, the compute operator will significantly be slower than a load balanced advance + segmented reduce.

- **Push Based Approach:** Instead of gathering all the locations from all the neighbors of an active vertex, we perform a scatter of valid locations of all active vertices to their neighbors; push vs. pull approach.

### Gunrock implications

- **The `predicted` atomic:** Geolocation and some other application exhibit the same behavior where the stop condition of the algorithm is such that when all vertices' label is predicted or determined, the algorithm stops. In Geolocation's case, when a location for all nodes is predicted, geolocation converges. This is currently being done with a loop and an atomic and it needs to be more of a core operation (mini-operator) such that when `isValidCount(labels|V|) == |V|)` stop condition is met. Currently, I am skipping this using number of iterations parameter to determine how long geolocation should run for.

### Notes on multi-GPU parallelization

No complicated partitioning scheme is required for multi-GPU implementation; the challenging part for a multi-GPU Geolocation would be to obtain the updated node location from a seperate device if the two vertices on different devices share an edge. An interesting approach here would be leveraging the P2P memory bandwidth with the new NVLink connectors to exchange small amount of updates across the NVLink's memory lane.

### Notes on dynamic graphs

Streaming graphs is an interesting problem for Geolocation application, because when predicting a location of a certain node, if another edge is introduced the location of the vertex has to be recomputed entirely. This can still be done in an iterative manner, where if a node was inserted as a neighbor to a vertex, that vertex's predicted location will be marked invalid and during the next iteration it will be computed again along with all the other invalid vertices (locations).

### Notes on larger datasets

If the datasets are larger than a single or multi-GPU's aggregate memory, an easier solution to this would be to let Unified Virtual Memory (UVM) in CUDA handle the memory movement for us.

### Notes on other pieces of this workload

Geolocation application calls a lot of  CUDA math functions (`sin`, `cos`, `atan`, `atan2`, `median`, `mean`, `fminf`, `fmaxf`, etc.), and I believe some of these micro workloads can also leverage GPU's parallelism; for example, a mean could be implemented using `reduce-mean/sum`. We currently don't have these math operators within gunrock that can be used in graph applications.

