-i-
title: Template for HIVE workflow report

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

<aside class="notice">
  JDO notes, delete these when you copy this to `hive_yourworkflowname`: The goal of this report is to be useful to DARPA and to your colleagues. This is not a research paper. Be very honest. If there are limitations, spell them out. If something is broken or works poorly, say so. Above all else, make sure that the instructions to replicate the results you report are good instructions, and the process to replicate are as simple as possible; we want anyone to be able to replicate these results in a straightforward way.
</aside>

# GraphSage

This application is based on GraphSage paper (Inductive Representation Learning on Large Graphs).  
We implement Algorithm 2 in our code. Given a graph G, input features, and weight matrix W^k, non-linear activition function, the output is embedding vector of each node.
Note that we only impletement the inference part of the paper, we did not implement the training part to get W^k and parameters of aggregation functions. The aggregation function we use is Mean aggregator. 
## Summary of Results

One or two sentences that summarize "if you had one or two sentences to sum up your whole effort, what would you say". I will copy this directly to the high-level executive summary in the first page of the report. Talk to JDO about this. Write it last, probably.

## Summary of Gunrock Implementation

As long as you need. Provide links (say, to papers) where appropriate. What was the approach you took to implementing this on a GPU / in Gunrock? Pseudocode is fine but not necessary. Whatever is clear.

Be specific about how to map the algorithm to Gunrock operators. That is helpful for everyone.

Be specific about what you actually implemented with respect to the entire workflow (most workflows have non-graph components; as a reminder, our goal is implementing single-GPU code on only the graph components where the graph is static).

We implement Inductive Representation Learning on Large Graphs (GraphSage) paper https://www-cs-faculty.stanford.edu/people/jure/pubs/graphsage-nips17.pdf. 
We implement algorithm 2, GraphSage minibatch forward popagation algorithm. 
In our implementatoin, we employee depth K = 2 which is the same as GraphSage paper and other graph machine learning papers such as GCN, FastGCN, PinSage. K =2 gives the best result in these methods.
The aggegration fucntion we use is the Mean aggregator. And activation function we use is ReLu. 
We sample neighbours based on the uniform distribution. 
The default batch size is 512. 

Instead of using B2, B1 and B0 name the nodes, we use `source`, `child`, and `leaf` to name three different groups of nodes. 
In GraphSage paper, figure 1 (2) shows aggregating feature information from neighbors, where read node is what we called `source` here and blue nodes are `child`, and green nodes are `leaf`. 

The CPU psudocode is as follows:

```
    for source in Batch:
        // sample n neighbors as children of source
        children <- selectNeighbor (source, n) ;

        for child in children :
            //sample m neighbors as leaves of child:
            leafs <- selectNeighbor (child, m) ;
            
            child_temp <- relu (concat (child.features * wf1, Mean (leaf.features) * wa1)); 
            child_temp <- child_temp / ||child_temp||_2;
                    
        source_temp <- relu(concat (source.features * wf1, Mean(child.features) * wa1));
        source_temp <- source_temp / ||source_temp||_2;
   
        source_result <- relu(concat (source_temp * wf2, Mean(child_temp) * wa2));
        source_result <- source_result / ||source_result||_2;   
          
        save source_result;
```

where `source_result` is each node's embedding vector `z_u` in algorithm 2. `|| . ||_2` is the L2-norm of a vector.  
The `selectNeighbor ()`  function we use is uniform, you can change it to the algorithm you need, 
such as weighted uniform, importance sampling (FaseGCN paper use this) or random walk probability like DeepWalk or Node2vec (PinSage paper use this). 

The GPU is very similar to CPU code. We did not use advance operator or filter operator. 
Our parallelism is based on source-child pairs. i.e. .... do not know how to discribe this. 
 

## How To Run This Application on DARPA's DGX-1

### Prereqs/input

CUDA should have been installed; `$PATH` and `$LD_LIBRARY_PATH` should have been
set correctly to use CUDA. The current Gunrock configuration assumes boost
(1.58.0 or 1.59.0) and Metis are installed; if not, changes need to be made in
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
cd ../tests/sage
make
```

At this point, there should be an executable `test_sage_<CUDA version>_x86_64`
in `tests/sage/bin`.

The datasets are assumed to have been placed in `/raid/data/hive`, and converted
to proper matrix market format (.mtx). At the time of testing,
  `pokec` is available in that directory. 

Note that GraphSage is an inductive representation learning algorithm.
We assume that there is no dangling nodes in graph. 
So before running it please remove the dangling nodes in graph. 

The testing is done with Gunrock using `dev-refactor` branch at commit `2699252`
(Oct. 18, 2018), using CUDA 10.2 with NVIDIA driver 390.30.
### Running the application

<code>
./bin/test_sage_10.0_x86_64 \
 market /raid/data/hive/[DataSet]/[DataSet].mtx  --undirected \
 --vertex-start-from-zero=true --Wf1 ../../gunrock/app/sage/wf1.txt \
 --Wa1 ../../gunrock/app/sage/wa1.txt --Wf2 ../../gunrock/app/sage/wf2.txt \
 --Wa2 ../../gunrock/app/sage/wa2.txt --features ../../gunrock/app/sage/features.txt \
 --num-runs=10 --device=2 \
 --batch-size=128,256,512,1024,2048 \
 --validation=each
</code>



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
