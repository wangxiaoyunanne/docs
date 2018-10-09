---
title: Geolocation (HIVE)

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Geolocation

Identifies user locations using the position of friends through spatial label propagation. Given a graph `G`, geolocation examines each vertex `v` neighbors and computes the spatial median of neighbors' location list, the output is a list of predicted locations for all vertices with unknown locations.

## Summary of Results

One or two sentences that summarize "if you had one or two sentences to sum up your whole effort, what would you say". I will copy this directly to the high-level executive summary in the first page of the report. Talk to JDO about this. Write it last, probably.

## Summary of Gunrock Implementation

We implemented Geolocation using two `compute` operators with the help of `ForAll()`. The first `ForAll()` is a `gather` operation, gathering all the values of neighbors with known locations for an active vertex `v`, and the second `ForAll()` uses those values to compute the `spatial_center`.

<code>
def gather_op(Vertex v):
    for neighbor in G.neighbors(v):
	if isValid(neigbor.location):
	    locations_list[v].append(neigbor.location)

def compute_op(Vertex v):
    if !isValid(v.location):
	v.location = spatial_center(locations_list[v])
</code>


## How To Run This Application on DARPA's DGX-1

### Prereqs/input

<code>
git clone --recursive https://github.com/gunrock/gunrock -b dev-refactor
cd gunrock
mkdir build
ctest ..
cd ../tests/geo/
make clean && make
</code>

### Running the application

<code>

</code>

### Output

How do you make sure your output is correct/meaningful? (What are you comparing against?)

## Performance and Analysis

How do you measure performance? What are the relevant metrics? Runtime? Throughput? Some sort of accuracy/quality metric?

### Implementation limitations

e.g.:

- Size of dataset that fits into GPU memory (what is the specific limitation?)
- Restrictions on the type/nature of the dataset

### Comparison against existing implementations

- [HIVE reference implementation](https://gitlab.hiveprogram.com/ggillary/geotagging.git)
- [GTUSC implementation](https://gitlab.hiveprogram.com/gtusc/geotagging)


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
