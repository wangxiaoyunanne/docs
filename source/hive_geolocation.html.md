---
title: Geolocation (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Geolocation

Infers user locations using the location (latitude, longitude) of friends through spatial label propagation. Given a graph `G`, geolocation examines each vertex `v`'s neighbors and computes the spatial median of the neighbors' location list. The output is a list of predicted locations for all vertices with unknown locations.

## Summary of Results

One or two sentences that summarize "if you had one or two sentences to sum up your whole effort, what would you say". I will copy this directly to the high-level executive summary in the first page of the report. Talk to JDO about this. Write it last, probably.

## Summary of Gunrock Implementation

There are two approaches we took to implement Geolocation within gunrock: 

- **[Fewer Reads] Global Gather:** uses two `compute` operators as `ForAll()`. The first `ForAll()` is a `gather` operation, gathering all the values of neighbors with known locations for an active vertex `v`, and the second `ForAll()` uses those values to compute the `spatial_center` where the spatial center of a list's points is the center of those points on the earth's surface.

```python
def gather_op(Vertex v):
    for neighbor in G.neighbors(v):
        if isValid(neigbor.location):
            locations_list[v].append(neigbor.location)

def compute_op(Vertex v):
    if !isValid(v.location):
        v.location = spatial_center(locations_list[v])
```

- **[Less Memory] Repeated Compute:** skips the global gather and uses only one `compute` operator as a `ForAll()` to find the spatial center of every vertex. During the spatial center computation, instead of iterating over all valid neighbors (where valid neighobor is a neighbor with a known location), we iterate over all neighbors for each vertex, doing more random reads than the global gather approach, but using `3x` less memory.

```python
def spatial_center(Vertex v):
    if !isValid(v.location):
        v.location = spatial_median(neighbors_list[v])
```

- **[Optimization] Early Exit:** fuses the global gather approach with the repeated compute, by performing one local gather for every vertex within the spatial center operator (without a costly device barrier), and exiting early if a vertex `v` has only one or two valid neighbors:

```python
def spatial_center(Vertex v):
    if !isValid(v.location):
	if v.valid_locations == 1:
	    v.location = valid_neighbor[v].location:
	    exit
	else if v.valid_locations == 2:
	    v.location = mid_point(valid_neighbors[v].location)
	else:
            v.location = spatial_median(neighbors_list[v])
```


| Approach         | Memory Usage | Memory Reads/Vertex  | Device Barriers | Largest Dataset (P100) |
|------------------|--------------|----------------------|-----------------|------------------------|
| Global Gather    | O(3x\|E\|)   | # of valid locations | 1               | ~160M Edges            |
| Repeated Compute | O(\|E\|)     | degree of vertex     | 0               | ~500M Edges            |


**Note:** `spatial_median()` is defined as center of points on earth's surface -- given a set of points `Q`, the function computes the point `p` such that: `sum([haversine_distance(p, q) for q in Q])` is minimized. See `gunrock/app/geo/geo_spatial.cuh` for details on the spatial median implementation.

## How To Run This Application on DARPA's DGX-1

### Prerequisites

```shell
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock
mkdir build
ctest ..
cd ../tests/geo/
make clean && make
```

### HIVE Data Preparation

Prepare the data, skip this step if you are just running the sample dataset. Assuming we are in `tests/geo` directory:

```shell
export TOKEN= # get this Authentication TOKEN from
              # https://api-token.hiveprogram.com/#!/user
wget --header "Authorization:$TOKEN" \
  https://hiveprogram.com/data/_v0/geotagging/instagram/instagram.tar.gz
tar -xzvf instagram.tar.gz && rm instagram.tar.gz
cd instagram/graph
cp ../../generate-data.py ./
python generate-data.py
```

This will generate two files, `instagram.mtx` and `instagram.labels`, which can be used as an input to the geolocation app.

### Running the application

Application specific parameters:

```
    --labels-file
        file name containing node ids and their locations.

    --geo-iter
        number of iterations to run geolocation or (stop condition).
        (default = 3)

    --spatial-iter
        number of iterations for spatail median computation.
        (default = 1000)

    --geo-complete
        runs geolocation for as many iterations as required
        to find locations for all nodes.
        (default = false because it uses atomics)

    --debug
        Debug label values, this prints out the entire labels 
	array (longitude, latitude).
        (default = false)
```

Example command-line:

```shell
# geolocation.mtx is a graph based on chesapeake.mtx dataset
./bin/test_geo_10.0_x86_64 --graph-type=market --graph-file=./geolocation.mtx \
  --labels-file=./locations.labels --geo-iter=2 --geo-complete=false
```

Sample input (labels):

```
% Nodes Latitude Longitude
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
```

Sample output:

```
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
 (nans represent unknown locations)
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
```

### Output

When `quick` mode is disabled, the application performs the CPU reference implementation, which is used to validate the results from the GPU implementation by comparing the predicted latitudes and longitudes of each vertex with the CPU reference implementation. Further correctness checking was performed by comparing results to the [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/geotagging.git). 

Geolocation application also supports the `quiet` mode, which allows the user to skip the output and just report the performance metrics (note, this will run the CPU implementation in the background without any output).

## Performance and Analysis

Runtime is the key metric for measuring performance for Geolocation. We also check for prediction accuracy of the labels, but that is a threshold for correctness. If a certain threshold is not met (while comparing results to the CPU reference code), the output is considered incorrect and that run is invalid. Therefore, for the report we just focus on runtime.

### Implementation limitations

One of our biggest limitations is that we are currently use a `|V|x|V|` array to store all the neighbors' locations for all the vertices. For a graph of size 60k nodes, it can take approximately 16 GB of GPU memory. In a worst-case scenario, we have a fully connected graph and require this much storage, but in most real-world cases, we won't see this connectivity within a graph. Some tricks can be done to determine the degree of each vertex beforehand and allocate just enough memory required to store the locations of valid neighbors. For simplicity at this point, our baseline currently uses a `|V|x|V|` size array.

### Comparison against existing implementations

|  GPU  | Dataset            | \|V\|    | \|E\|     | Iterations | Spatial Iters | GT CPU (8 threads) | GT CPU (serial) | Gunrock  |
|-------|--------------------|----------|-----------|------------|---------------|--------------------|-----------------|----------|
|  P100 | geolocation-sample | 39       | 170       | 3          | 1000          | 0.466108           | N/A             | 0.286102 |
|  P100 | instagram          | 23731995 | 41355870  | 3          | 1000          | 10.643214          | 63.82181        | 1.910632 |
|  V100 | twitter            | 50190344 | 251154219 | 3          | 1000          |                    |                 |          |

On a workload that fills the GPU, gunrock outperforms GT's OpenMP C++ implementation by 5.5x. There is a lack of available datasets against which we can compare performance, so we use only the provided instagram dataset, and a toy sample for a sanity check on NVIDIA's P100 with 16GB of global memory. All tested implementations meet the criteria of accuracy, which is validated against the output of the original python implementation.

- [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/geotagging.git) uses distributed PySpark.
- [GTUSC implementation](https://gitlab.hiveprogram.com/gtusc/geotagging) uses C++ OpenMP.

### Performance limitations

As discussed later in the "Alternate approaches" section, the current implementation of geolocation uses a compute operator with minimal load balancing. In cases where the graph is not so nicely distributed (where there is a great deal of difference in the degrees of vertices), the entire application will suffer significantly from load imbalance.

Profiling the application shows 98.78% of the compute time in GPU activities is in the `spatial_median` kernel, which gives us a good direction to focus our efforts on load-balancing the workloads within the operator. Specifically, we must target the `for` loops iterating over the neighbor list for spatial center calculations.

## Next Steps

### Alternate approaches

- **Neighborhood Reduce w/ Spatial Center:** We can perform better load balancing by leveraging a neighbor-reduce (`advance` operator + `cub::DeviceSegmentedReduce`) instead of using a compute operator. In graphs where the degrees of nodes vary a lot, the compute operator will be significantly slower than a load-balanced advance + segmented reduce.

- **Push Based Approach:** Instead of gathering all the locations from all the neighbors of an active vertex, we could instead perform a scatter of valid locations of all active vertices to their neighbors; this is a push approach vs. our current implementation's pull.

### Gunrock implications

- **The `predicted` atomic:** Geolocation and some other applications exhibit the same behavior where the stop condition of the algorithm is such that when all vertices' labels are predicted or determined, the algorithm stops. In Geolocation's case, when a location for all nodes is predicted, geolocation converges. We currently implement this with a loop and an atomic. This needs to be more of a core operation (mini-operator) such that when `isValidCount(labels|V|) == |V|`, a stop condition is met. Currently, we sidestep this issue by using a number-of-iterations parameter to determine the stop condition.

### Notes on multi-GPU parallelization

No complicated partitioning scheme is required for multi-GPU implementation; the challenging part for a multi-GPU Geolocation would be to obtain the updated node location from a seperate device if the two vertices on different devices share an edge. An interesting approach here would be leveraging the P2P memory bandwidth with the new NVLink connectors to exchange a small amount of updates across the NVLink's memory lane.

### Notes on dynamic graphs

Streaming graphs is an interesting problem for the Geolocation application, because when predicting the location of a certain node, if another edge is introduced, the location of the vertex has to be recomputed entirely. This can still be done in an iterative manner, where if a node was inserted as a neighbor to a vertex, that vertex's predicted location will be marked invalid and during the next iteration it will be computed again along with all the other invalid vertices (locations).

### Notes on larger datasets

If the datasets are larger than a single or multi-GPU's aggregate memory, the straightforward solution would be to let Unified Virtual Memory (UVM) in CUDA automatically handle memory movement.

### Notes on other pieces of this workload

Geolocation calls a lot of CUDA math functions (`sin`, `cos`, `atan`, `atan2`, `median`, `mean`, `fminf`, `fmaxf`, etc.).  Some of these micro-workloads can also leverage the GPU's parallelism; for example, a mean could be implemented using `reduce-mean/sum`. We currently don't have these math operators exposed within Gunrock in such a way they can be used in graph applications.
