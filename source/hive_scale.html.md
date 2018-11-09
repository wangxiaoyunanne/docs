<h1 id="scaling-analysis-for-hive-applications">Scaling analysis for HIVE applications</h1>
<p>The purpose of this study is to understand how the HIVE v0 applications would scale out on multiple GPUs, with a focus on the DGX-1 platform. Before diving into per-application analysis, we give a brief summary of the potential hardware platforms, the communication methods and models, and graph partitioning schemes.</p>
<h2 id="hardware-platforms">Hardware platforms</h2>
<p>There are at least three kinds of potential multi-GPU platforms for HIVE apps. They have different GPU communication properties, and that may affect the choice of communication models and/or graph partitioning schemes, thus may have different scaling results.</p>
<h3 id="dgx-1">DGX-1</h3>
<p>The DGX-1 with P100 GPUs has 4 NVLink lanes per GPU, connected as follows. <img src="attachments/scaling/NVLink-DGX1.png" title="DGX1 NVLink Topology" alt="DGX1-NVLink" /></p>
<p>Each of the NVLink links runs at 20 GBps per direction, higher than PCIe 3.0 x16 (16 GBps for the whole GPU). But the topology is not all-to-all, and GPUs may not be able to access every other GPU's memory. For example, GPU0 can't use peer access on GPUs 5, 6 and 7. This makes implementations using peer access more complex than a full all-to-all topology. DGX-1 with V100 GPUs increases the NVLink speed to 25 GBps per direction per lane, and increases the number of lanes per GPU to 6, but peer accessibility has not been changed. This issue is finally addressed in DGX-2 with the NVSwitch.</p>
<p>Using a benchmark program to test throughput and latency shows the following results. <code>Self</code> indicates local GPU accesses, <code>peer</code> indicates peer accesses, <code>host</code> indicates accesses to the CPU memory via UVM, and <code>all</code> indicates accesses to all peer-accessible GPUs. The <code>regular</code> operations access the memory in continous places by neighboring threads; in CUDA terms, these operations are coalesced memory accesses. The <code>random</code> operations access the memory space randomly, and neighboring threads may be touching memory that are far away from each other; in CUDA terms, these operations are non-coalesced memory accesses. The memory access patterns of graph workflows are a mix of both, and one main target of kernel optimizations is to make the memory accesses as coalesced as possible. But at the end, depending on the algorithm, some random accesses may be unavoiable. Random accesses across GPUs are particularly slow.</p>
<p>Throughput in GBps:</p>
<table>
<thead>
<tr class="header">
<th>Operation</th>
<th align="right">Self</th>
<th align="right">Peer</th>
<th align="right">Host</th>
<th align="right">All</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Regular read</td>
<td align="right">448.59</td>
<td align="right">14.01</td>
<td align="right">444.74</td>
<td align="right">12.17</td>
</tr>
<tr class="even">
<td>Regular write</td>
<td align="right">442.98</td>
<td align="right">16.21</td>
<td align="right">16.18</td>
<td align="right">12.17</td>
</tr>
<tr class="odd">
<td>Regular update</td>
<td align="right">248.80</td>
<td align="right">11.71</td>
<td align="right">0.0028</td>
<td align="right">6.00</td>
</tr>
<tr class="even">
<td>Random read</td>
<td align="right">6.78</td>
<td align="right">1.43</td>
<td align="right">2.39</td>
<td align="right">4.04</td>
</tr>
<tr class="odd">
<td>Random write</td>
<td align="right">6.63</td>
<td align="right">1.14</td>
<td align="right">3.47E-5</td>
<td align="right">3.82</td>
</tr>
<tr class="even">
<td>Random update</td>
<td align="right">3.44</td>
<td align="right">0.83</td>
<td align="right">1.92E-5</td>
<td align="right">2.08</td>
</tr>
</tbody>
</table>
<p>Latency in microseconds (us):</p>
<table>
<thead>
<tr class="header">
<th>Operation</th>
<th align="right">Self</th>
<th align="right">Peer</th>
<th align="right">Host</th>
<th align="right">All</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Regular read</td>
<td align="right">2.12</td>
<td align="right">1.18</td>
<td align="right">1.30</td>
<td align="right">1.49</td>
</tr>
<tr class="even">
<td>Regular write</td>
<td align="right">1.74</td>
<td align="right">1.00</td>
<td align="right">13.83</td>
<td align="right">1.01</td>
</tr>
<tr class="odd">
<td>Regular update</td>
<td align="right">2.43</td>
<td align="right">1.20</td>
<td align="right">79.29</td>
<td align="right">1.44</td>
</tr>
<tr class="even">
<td>Random read</td>
<td align="right">3.11</td>
<td align="right">1.08</td>
<td align="right">13.61</td>
<td align="right">1.40</td>
</tr>
<tr class="odd">
<td>Random write</td>
<td align="right">3.28</td>
<td align="right">1.05</td>
<td align="right">15.88</td>
<td align="right">1.39</td>
</tr>
<tr class="even">
<td>Random update</td>
<td align="right">5.69</td>
<td align="right">1.28</td>
<td align="right">21.76</td>
<td align="right">1.38</td>
</tr>
</tbody>
</table>
<p>All the regular throughputs are at least 80% of their theoretical upper bounds. The latencies when accessing local GPUs seem odd, but other latencies look reasonable. It's clear that local regular accesses have much higher throughput than inter-GPU connections, about 20 to 30 times from this experiment. The ratio of random accesses are lower, but still at about 5 times. The implication on the scalabilities of graph applications is that for scalable behavior, the local-memory-access-to-communication ratio needs to be at least 10 to 1. Because most graph implementations are memory bound, the computation cost is counted by the number of elements accessed by the kernels; this means the computation to communication ratio should be at least 2.5 operations to 1 byte to exhibit scalable behavior.</p>
<p>Unified virtual memory (UVM) doesn't work as expected for most cases, instead only when the accesses are read only and the data can be duplicated on each GPU. Otherwise the throughputs are significantly lower, caused by memory migration and going over the PCIe interfaces. The less than 0.5 GBps throughputs from write and update operations via UVM could possibily caused by problems in the UVM support or the way how UVM is configured in the benchmark code. It must be noted that, at the time of testing, the DGX-1 has CUDA 9.1 and NVIDIA driver 390.30 installed, which are more than one year old. A newer CUDA version and NVIDIA driver could potentially improve the UVM performance. Testing using V100 GPUs with CUDA 10.0 and NVIDIA driver 410 shows considerablly better throughputs.</p>
<h3 id="dgx-2">DGX-2</h3>
<p>The DGX-2 system has a very different NVLink topology: the GPUs are connected by NVSwitches, and all to all peer accesses are available.</p>
<p><img src="attachments/scaling/NVLink-DGX2.png" title="DGX2 NVLink Topology" alt="DGX2-NVLink" />.</p>
<p>At the time of this report, the DGX-2 is hardly available, and not to us. What we have locally at UC Davis are two Quadro GV100 GPUs directly connected by 4 NVLink2 lanes. Although the setup is much smaller than the DGX-2, it still can provide some ideas on how the inter-GPU communication would perform on the DGX-2.</p>
<p>Throughput in GBps</p>
<table>
<thead>
<tr class="header">
<th>Operation</th>
<th align="right">Self</th>
<th align="right">Peer</th>
<th align="right">Host</th>
<th align="right">All</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Regular read</td>
<td align="right">669.68</td>
<td align="right">76.74</td>
<td align="right">679.52</td>
<td align="right">76.72</td>
</tr>
<tr class="even">
<td>Regular write</td>
<td align="right">590.01</td>
<td align="right">85.00</td>
<td align="right">170.113</td>
<td align="right">76.28</td>
</tr>
<tr class="odd">
<td>Regular update</td>
<td align="right">397.26</td>
<td align="right">39.67</td>
<td align="right">80.00</td>
<td align="right">37.86</td>
</tr>
<tr class="even">
<td>Random read</td>
<td align="right">17.39</td>
<td align="right">7.46</td>
<td align="right">17.27</td>
<td align="right">10.51</td>
</tr>
<tr class="odd">
<td>Random write</td>
<td align="right">13.25</td>
<td align="right">7.96</td>
<td align="right">1.23</td>
<td align="right">7.24</td>
</tr>
<tr class="even">
<td>Random update</td>
<td align="right">6.83</td>
<td align="right">3.88</td>
<td align="right">0.68</td>
<td align="right">3.85</td>
</tr>
</tbody>
</table>
<p>Latency in microsecond (us)</p>
<table>
<thead>
<tr class="header">
<th>Operation</th>
<th align="right">Self</th>
<th align="right">Peer</th>
<th align="right">Host</th>
<th align="right">All</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Regular read</td>
<td align="right">0.37</td>
<td align="right">0.47</td>
<td align="right">0.37</td>
<td align="right">0.41</td>
</tr>
<tr class="even">
<td>Regular write</td>
<td align="right">0.08</td>
<td align="right">0.08</td>
<td align="right">0.08</td>
<td align="right">0.15</td>
</tr>
<tr class="odd">
<td>Regular update</td>
<td align="right">0.37</td>
<td align="right">0.47</td>
<td align="right">0.43</td>
<td align="right">0.41</td>
</tr>
<tr class="even">
<td>Random read</td>
<td align="right">0.11</td>
<td align="right">0.10</td>
<td align="right">0.10</td>
<td align="right">0.16</td>
</tr>
<tr class="odd">
<td>Random write</td>
<td align="right">0.13</td>
<td align="right">0.08</td>
<td align="right">0.08</td>
<td align="right">0.15</td>
</tr>
<tr class="even">
<td>Random update</td>
<td align="right">0.15</td>
<td align="right">0.09</td>
<td align="right">0.09</td>
<td align="right">0.17</td>
</tr>
</tbody>
</table>
<p>On this machine configuration, the local-to-peer memory throughput ratios, about 8 for regular accesses and about 2 for random accesses, are much lower than the DGX-1. The decreases are mainly from using all the 4 lanes for communication, instead of 1 in the DGX-1 cases. If using only a single lane, the ratios would become 32 and 8, even higher than the DGX-1. The actual effect from the NVSwitch is still unclear, but DGX-2 is expected to have similar scalabilities as DGX-1 for graph applications.</p>
<h3 id="gpu-clusters">GPU clusters</h3>
<p>Going from multiple GPUs within the same node to multiple GPUs across different nodes significantly decreases the inter-GPU throughput. While NVLink runs at 80 GBps per direction per GPU for the DGX-1, the aggregated InfiniBand bandwidth is only 400 Gbps, which is only one twelfth of the aggregated inter-GPU bandwidth. This means the local access-to-communication-bandwidth ratio drops an order of magnitude, making scaling graph applications across nodes a corresponding order of magnitude harder. Using the same approximation method as the DGX-1, a graph implementation needs to have 30 operations / local memory operations for each byte going across the nodes. The implementation focus may need to switch to communication, rather than local computation, to achieve a scalable implementation on GPU clusters.</p>
<h2 id="communication-methods-models">Communication methods / models</h2>
<p>There are multiple ways to move data between GPUs: explicit movement, peer accesses, and unified virtual memory (UVM). They have different performance and implications in implementing graph workflows.</p>
<h3 id="explicit-data-movement">Explicit data movement</h3>
<p>The most traditional way to communicate is to explicitly move the data: use <code>cudaMemcpyAsync</code> to copy a block of memory from one GPU to another. The source and destination GPUs are not required to be peer accessible. CUDA will automatically select the best route: if GPUs are peer-accessible, the traffic will go through the inter-GPU connection, be it NVLink or PCIe; if they are not peer-accessible, the data will be first copied to CPU memory, and then copied to the destination GPU.</p>
<p>One of the advantage of explicit data movement is throughput. <code>cudaMemcpyAsync</code> is highly optimized, and the data for communication are always dense. The throughput should be close to the hardware limit, if the size of data is not too small, say at least a few tens of MB. Explicit data movement also isolates local computation and communication. Because there is no need to consider the data layout or different access latencies from local or remote data, the implementation and optimization of computation kernels can be much simpler. It also enables connection to other communication libraries, such as MPI.</p>
<p>However, explicit memory copy requires that data for communication are packed in a continuous memory space. For most applications, this means additional computation to prepare the data. Since the computing power of GPUs is huge, and graph applications are mostly memory-bound, this extra computation should only have minimal impact on the running time.</p>
<p>Many graph algorithms are written using the bulk synchronous parallel (BSP) model: computations are carried out in iterations, and the results of computation are only guaranteed to be visible after the iteration boundary. The BSP model provides a natural communication point: at the iteration boundary. The current Gunrock multi-GPU framework follows the BSP model.</p>
<p>Depending on the algorithm, there are several communication models that can be used:</p>
<ul>
<li><p><em>Peer to host GPU</em> This communication model is used when data of a vertex or edge on peer GPUs need to be accumulated / aggregated onto the host GPU of the vertex. When the vertex or edge is only adjacent to a few GPUs, it may be beneficial to use direct p2p communication; when the vertex is adjacent to most GPUs, a <code>Reduce</code> from all GPUs to the host GPU may be better.</p></li>
<li><p><em>Host GPU to peers</em> This is the opposite to the peer-to-host model. It propagates data of a vertex or edge from its host GPU to all GPUs adjacent to the vertex. Similarly, if the number of adjacent GPUs are small, point-to-point communication should do the work; otherwise, <code>broadcast</code> from the host GPU may be better.</p></li>
<li><p><em>All reduce</em> When updates on the same vertex or edge come from many GPUs, and the results are needed on many GPUs, <code>AllReduce</code> may be the best choice. It can be viewed as an <code>peers to host</code> followed by an <code>host to peers</code> communication. It can also be used without partitioning the graph: it works without knowing or assigning a host GPU to an vertex or edge.</p></li>
<li><p><em>Mix all reduce with peers to host GPU or host GPU to peers</em> This is a mix of <code>AllReduce</code> and peer-to-peer communications: for vertices or edges that touch a large number of GPUs, <code>AllReduce</code> is used; for other vertices or edges, direct peer-to-peer communications are used. This communication model is coupled with the high / low degree partitioning scheme. The paper &quot;Scalable Breadth-First Search on a GPU Cluster&quot; <a href="https://arxiv.org/abs/1803.03922" class="uri">https://arxiv.org/abs/1803.03922</a> has more details on this model.</p></li>
</ul>
<h3 id="peer-accesses">Peer accesses</h3>
<p>If a pair of GPUs is peer-accessible, they can directly dereference each other's memory pointers within CUDA kernels. This provides a more asynchronous way for inter-GPU communication: there is no need to wait for the iteration boundary. Atomic operations are also supported if the GPUs are connected by NVLink. The implementation can also be kept simple, since no data preparing and explicit movement is needed. The throughput is also acceptable, although not as good as explicit movement.</p>
<p>However, this essentially forces the kernel to work on a NUMA (non-uniform memory access) domain formed by local and remote GPU memory. Some kernels optimized under the assumption of a flat memory domain may not work well. Peer accesses also give up the opportunity to aggregate local updates on the same vertex or edge before communication, so the actual communication volume may be larger.</p>
<h3 id="unified-virtual-memory-uvm">Unified virtual memory (UVM)</h3>
<p>UVM is similar to peer accesses, as it also enables multiple GPUs to access the same memory space. However, the target memory space is allocated in the CPU memory. When needed on a GPU, a memory page will be moved to the GPU's memory via the page fault mechanism. Updates to the data are cached in GPU memory first, and will eventually be written to the CPU memory. UVM provides a transparent view of the CPU memory on GPU, and significantly reduces the coding complexity if running time is not a concern. It also enables the GPU to process datasets that can't fit in combined GPU memory without explicitly streaming the data from CPU to GPU.</p>
<p>But there are some caveats. The actual placement of a memory page/piece of data relies on hints given by <code>cudaMemAdvise</code>, otherwise it will need to be fetched from CPU to GPU when first used by any GPU, and bounces between GPUs when updated by multiple GPUs. The hints essentially come from partitioning the data, but sometimes there is no good way to partition, and data bouncing is unavoidable. In the worst cases, the data can be moved back to CPU, and any further access will need to go through the slow PCIe bridge again. The performance of UVM is not as good as explicit data movement or peer accesses; in the worst cases, it can be a few orders of magnitude slower. When data is larger than the GPU memory, UVM's throughput drops significantly; as a result, it's easier to code, but it will be slower than streaming the graph for datasets larger than GPU memory.</p>
<h2 id="graph-partitioning-scheme">Graph partitioning scheme</h2>
<p>Graphs may be cut into smaller pieces to put them onto multiple GPUs. Duplicating the graph on each may work for some problems, provided the graph is not too large; but duplication is not suitable for all problems, and does not scale in graph size. Graph partitioning is a long-lasting research topic, and we decided to use existing partitioners, such as Metis, instead of implementing some complicated ones of our own. A large number of graphs, especially those with high connectivities, are really difficult to partition; our results suggest that random partitioning works quite well in terms of time taken by the partitioner, load balancing, programming simplicity and still manageable communication cost. By default, Gunrock uses the random partitioner.</p>
<p>What makes a bigger difference is the partitioning scheme: whether the graph is partitioned in 1 dimension, 2 dimensions, or differently for low and high degree vertices.</p>
<h3 id="d-partitioning">1D partitioning</h3>
<p>1D partitioning distributes the edges in a graph either by the source vertices or the destination vertices. It's simple to work with, and scales well when the number of GPUs are small. It should still work on the DGX-1 with 8 GPUs for a large number of graph applications. But that may approach 1D partitioning's scalability limit.</p>
<h3 id="d-partitioning-1">2D partitioning</h3>
<p>2D partitioning distributes the edges by both the source and the destination vertices. When a graph is visualized in a dense matrix representation, 2D partitioning is like cutting the matrix by a 2D grid. 8 GPUs in the DGX-1 may be too small for 2D partitioning to be useful; it may worth trying out on DGX-2 with 16 GPUs. 2D partitioning of sparse graphs may create significant load imbalance between partitions.</p>
<h3 id="highlow-degree-partitioning">High/low degree partitioning</h3>
<p>The main idea of high/low degree partitioning is simple: for vertices with low out-degrees and their outgoing edges, distribute edges based on their source vertices; for vertices with high out-degrees and their outgoing edges, distribute edges based on the destination vertices; if both vertices have high out-degrees, distribute the edge based on the one with lower degree. The result is that low degree vertices are only adjacent to very few GPUs, while high degree vertices' edges are scattered among all GPUs. Graph applications scale very well when using the p2p communication model for low degree vertices, and the <code>AllReduce</code> model for high degree vertices.</p>
<h2 id="scaling-of-the-hive-applications">Scaling of the HIVE applications</h2>
<p>The target platform DGX-1 has 8 GPUs. Although that is more than we normally see for single scaling studies, the simple 1D graph partitioning scheme should (in general) still work. The marginal performance improvement by using more GPUs may be insignificant at this scale, and a small number of applications might even see performance decreases with some datasets. However, the 1D partitioning makes the scaling analysis simple and easily understandable. If other partitioning schemes could work better for a specific application, it would be noted.</p>
<h3 id="how-scaling-is-considered">How scaling is considered</h3>
<p>The bandwidth of NVLink is much faster than PCIe 3.0: 20x3 and 25x6 GBps bidirectionally for each Tesla P100 and V100 GPUs respectively in an DGX-1. But compared to the several TFLOPs computing power and several hundred GBps device bandwidth, the inter-GPU bandwidth is still considerably less. For any application to have good scalability, the communication time should be able to be either: 1) hidden by overlap with computation, or 2) kept as a small portion of the computation. The computation-to-communication ratio is a good indicator to predict the scalability: a higher ratio means better scalability. Specific to the DGX-1 system with P100 GPUs, a ratio larger than about 10 to 1 is expected for an app to have at least marginal scalability. For GPUs newer than P100, the computation power and memory bandwidth improve faster than interconnect bandwidth, so the compute-to-communicate ratio needs to grow even more to start seeing positive scaling.</p>
<h3 id="community-detection-louvain">Community Detection (Louvain)</h3>
<p>The main and most time-consuming part of the Louvain algorithm is the modularity optimization iterations. The aggregated edge weights between vertices and their respective adjacent communities, as well as the outgoing edge weights of each community, are needed for the modularity optimization. The vertex-community weights can be computed locally, if the community assignments of all neighbors of local vertices are available; to achieve this, a vertex needs to broadcast its new community when the assignment changes. The per-community outgoing edge weights can be computed by <code>AllReduce</code> across all GPUs. The modularity optimization with inter-GPU communication can be done as:</p>
<pre><code>Do
    Local modularity optimization;
    Broadcast updated community assignments of local vertices;
    local_weights_community2any := sums(local edges from an community);
    weights_community2any := AllReduce(local_weights_community2any, sum);
While iterations stop condition not met</code></pre>
<p>The local computation cost is on the order of O(|E| + |V|)/p, but with a large constant hidden by the O() notation. From experiments, the constant factor is about 10, considering the cost of sort or the random memory access penalty of hash table. The community assignment broadcast has a cost of |V| x 4 bytes, and the 'AllReduce' costs 2|V| x 8 bytes. These communication costs are the upper bound, assuming there are |V| communities, and all vertices update their community assignments. In practice, the communication cost can be much lower, depending on the dataset.</p>
<p>The graph contraction can be done as below on multiple GPUs:</p>
<pre><code>temp_graph := Contract the local sub-graph based on community assignments;
Send edges &lt;v, u, w&gt; in temp_graph to host_GPU(v);
Merge received edges and form the new local sub-graph;</code></pre>
<p>In the worst case, assuming the number of edges in the contracted graph is |E'|, the communication cost could be |E'| x 8 bytes, with the computation cost at about 5|E|/p + |E'|. For most datasets, the size reduction of graph from the contraction step is significant, so the memory needed to receive edges from the peer GPUs is manageable; however, if |E'| is large, it can be significant and may run out of GPU memory.</p>
<p><em>Summary of Louvain multi-GPU scaling</em></p>
<p>Because the modularity optimization runs multiple iterations before each graph contraction phase, the computation and communication of modularity optimization is dominant.</p>
<table>
<thead>
<tr class="header">
<th>Parts</th>
<th>Comp cost</th>
<th>Comm cost</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
<th>Memory usage (B)</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Modularity optim.</td>
<td>$10(E + V) /p$</td>
<td>$20V$ bytes</td>
<td>$E/p : 2V$</td>
<td>Okay</td>
<td>$88E/p + 12V$</td>
</tr>
<tr class="even">
<td>Graph contraction</td>
<td>$5E / p + E'$</td>
<td>$8E'$ bytes</td>
<td>$5E/p + E' : 8E'$</td>
<td>Hard</td>
<td>$16E'$</td>
</tr>
<tr class="odd">
<td>Louvain</td>
<td>$10(E + V) / p$</td>
<td>$20V$ bytes</td>
<td>$E/p : 2V$</td>
<td>Okay</td>
<td>$88E/p + 12V + 16E'$</td>
</tr>
</tbody>
</table>
<p>Louvain could be hard to implement on multiple GPUs, especially for the graph contraction phase, as it forms a new graph and distributes it across the GPUs. But the scalability should be okay.</p>
<h3 id="graphsage">GraphSAGE</h3>
<p>The main memory usage and computation of SAGE are related to the features of vertices. While directly accessing the feature data of neighbors via peer access is possible and memory-efficient, it will create a huge amount of inter-GPU traffic that makes SAGE unscalable in terms of running time. Using UVM to store the feature data is also possible, but that will move the traffic from inter-GPU to the GPU-CPU connection, which is even less desirable. Although there is a risk of using up the GPU memory, especially on graphs that have high connectivity, a more scalable way is to duplicate the feature data of neighboring vertices. Depending on the graph size and the size of features, not all of the above data distribution schemes are applicable. The following analysis focuses on the feature duplication scheme, with other schemes' results in the summary table.</p>
<p>SAGE can be separated into three parts, depending on whether the computation and data access is source-centric or child-centric.</p>
<pre><code>// Part1: Select the children
For each source in local batch:
    Select num_children_per_source children form source&#39;s neighbors;
    Send &lt;source, child&gt; pairs to host_GPU(child);

// Part2: Child-centric computation
For each received &lt;source, child&gt; pair:
    child_feature = feature[child];
    send child_feature to host_GPU(source);

    feature_sums := {0};
    For i from 1 to num_leaves_per_child:
        Select a leaf from child&#39;s neighbors;
        leaves_feature += feature[leaf];
    child_temp = L2_normalize( concatenate(
        feature[child] * Wf1, leaves_feature * Wa1));
    send child_temp to host_GPU(source);

// Part3: Source-centric computation
For each source in local batch:
    children_feature := sum(received child_feature);
    children_temp := sum(received child_temp);
    source_temp := L2_normalize( concatenate(
        feature[source] * Wf1, children_feature * Wa1));

    source_result := L2_normalize( concatenate(
        source_temp * Wf2, children_temp * Wa2));</code></pre>
<p>Assume the size of local batch is B, the number of children per source is C, the number of leaves per child is L, and the feature length per vertex is F. Dimensions of 2D matrices are noted as (x, y). The computation and communication costs for each part are:</p>
<pre><code>Part 1, computation  : B x C.
Part 1, communication: B x C x 8 bytes.
Part 2, computation  : B x C x F + B x C x (F + L x F + F x (Wf1.y + Wa1.y)).
Part 2, communication: B x C x (F + Wf1.y + Wa1.y) x 4 bytes.
Part 3, computation  : B x (C x (F + Wf1.y + Wa1.y) + F x (Wf1.y + Wa1.y) +
                       (Wf1.y + Wa1.y) x (Wf2.y + Wa2.y)).
Part 3, communication: 0.</code></pre>
<p>For Part 2's communication, if C is larger than about 2p, using <code>AllReduce</code> to sum up <code>child_feature</code> and <code>child_temp</code> for each source will cost less, at B x (F + Wf1.y + Wa1.y) x 2p x 4 bytes.</p>
<p><em>Summary of Graph SAGE multi-GPU scaling</em></p>
<table style="width:100%;">
<colgroup>
<col width="21%" />
<col width="16%" />
<col width="28%" />
<col width="20%" />
<col width="12%" />
</colgroup>
<thead>
<tr class="header">
<th>Parts</th>
<th>Computation cost</th>
<th>Communication cost (Bytes)</th>
<th>Comp. to comm. ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Feature duplication</strong></td>
<td></td>
<td></td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>Children selection</td>
<td>$BC$</td>
<td>$8BC$</td>
<td>1 : 8</td>
<td>Poor</td>
</tr>
<tr class="odd">
<td>Child-centric comp.</td>
<td>$BCF (2 + L + .y + .y)$</td>
<td>$4B (F + .y + .y) (C, 2p)$</td>
<td>$~ CF : (C, 2p) 4$</td>
<td>Good</td>
</tr>
<tr class="even">
<td>Source-centric comp.</td>
<td>$B (CF + (.y + .y) (C + F + .y + .y)$</td>
<td>0</td>
<td>N.A.</td>
<td>N.A.</td>
</tr>
<tr class="odd">
<td>Graph SAGE</td>
<td>$B (C + 3CF + 3LCF + (.y + .y) (CF + C + F + .y + .y))$</td>
<td>$8BC + 4B (F + .y + .y) (C, 2p)$</td>
<td>at least $~ CF :<br />
min(C, 2p) 4$</td>
<td>Good</td>
</tr>
<tr class="even">
<td></td>
<td></td>
<td></td>
<td></td>
<td></td>
</tr>
<tr class="odd">
<td><strong>Direct feature access</strong></td>
<td></td>
<td></td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>Child-centric comp.</td>
<td>$BCF (2 + L + .y + .y)$</td>
<td>$4B ((F + .y + .y) (C, 2p) + CLF)$</td>
<td>$~ (2 + L + .y + .y) : 4L$</td>
<td>poor</td>
</tr>
<tr class="odd">
<td>Graph SAGE</td>
<td>$B (C + 3CF + 3LCF + (.y + .y) (CF + C + F + .y + .y))$</td>
<td>$8BC + 4B (F + .y + .y) (C, 2p) + 4BCFL$</td>
<td>$~ (2 + L + .y + .y) : 4L$</td>
<td>poor</td>
</tr>
<tr class="even">
<td></td>
<td></td>
<td></td>
<td></td>
<td></td>
</tr>
<tr class="odd">
<td><strong>Feature in UVM</strong></td>
<td></td>
<td></td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>Child-centric comp.</td>
<td>$BCF (2 + L + .y + .y)$</td>
<td>$4B (F + .y + .y) (C, 2p)$ bytes over GPU-GPU + $4BCLF$ bytes over GPU-CPU</td>
<td>$~ (2 + L + .y + .y) : 4L$ over GPU-CPU</td>
<td>very poor</td>
</tr>
<tr class="odd">
<td>Graph SAGE</td>
<td>$B (C + 3CF + 3LCF + (.y + .y) (CF + C + F + .y + .y))$</td>
<td>$8BC + 4B (F + .y + .y) (C, 2p)$ bytes over GPU-GPU + $4BCFL$ bytes over GPU-CPU</td>
<td>$~ (2 + L + .y + .y) : 4L$ over GPU-CPU</td>
<td>very poor</td>
</tr>
</tbody>
</table>
<p>When the number of features is at least several tens, the computation workload will be much more than communication, and SAGE should have good scalability. Implementation should be easy, as only simple p2p or AllReduce communication models are used. If memory usage is an issue, falling back to peer-access or UVM will result in very poor scalability; problem segmentation (i.e,. only process portion of the graph at a time) may be necessary to have a scalable implementation for large graphs, but that will be quite complex.</p>
<h3 id="random-walks-and-graph-search">Random walks and graph search</h3>
<p>If the graph can be duplicated on each GPU, the random walk multi-GPU implementation is trivial: just do a subset of the walks on each GPU. The scalability will be perfect, as there is no communication involved at all.</p>
<p>A more interesting multi-GPU implementation would be when the graph is distributed across the GPUs. In this case, each step of a walk not only needs to send the <code>&lt;walk#, step#, v&gt;</code> information to <code>host_GPU(v)</code>, but also to the GPU that stores the result for such walk.</p>
<pre><code>For each walk starting from local vertex v:
    Store v for ;
    Select a neighbor u of v;
    Store u for ;
    Send  to host_GPU(u) for visit;

Repeat until all steps of walks finished:
    For each received  for visit:
        Select a neighbor u of v;
        Send  to host_GPU(u) for visit;
        Send  to host_GPU_walk(walk#) for record;

    For each received  for record:
        Store v for ;</code></pre>
<p>Using W as the number of walks, for each step, we have</p>
<table>
<thead>
<tr class="header">
<th>Parts</th>
<th>Comp. cost</th>
<th>Comm. cost</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Random walk</td>
<td>$W/p$</td>
<td>$W/p * 24$ bytes</td>
<td>$1 : 24$</td>
<td>very poor</td>
</tr>
</tbody>
</table>
<p>Graph search is very similar to random walk, except that instead of randomly selecting any neighbor, it selects the neighbor with the highest score (when using the <code>greedy</code> strategy), or with probabilities proportional to the neighbors' scores (when using the <code>stochastic_greedy</code> strategy). For the <code>greedy</code> strategy, a straightforward implementation, when reaching a vertex, goes through the whole neighbor list of thatsuch vertex and finds the one with maximum score. A more optimized implementation could perform a pre-visit to find the neighbor with maximum scored neighbor, with a cost of E/p; during the random walk process, the maximum scored neighbor will be known without going through the neighbor list.</p>
<p>For the <code>stochastic_greedy</code> strategy, the straightforward implementation would also go through all the neighbors, selecting one based on their scores and a random number. Preprocessing can also help: perform a scan on the scores of each vertex's neighbor list, with a cost of E/p; during the random walk, a binary search would be sufficient to select a neighbor, with weighted probabilities.</p>
<p>The cost analysis, depending on the walk strategy and optimization, results in:</p>
<table>
<colgroup>
<col width="20%" />
<col width="26%" />
<col width="19%" />
<col width="18%" />
<col width="14%" />
</colgroup>
<thead>
<tr class="header">
<th>Strategy</th>
<th>Comp. cost</th>
<th>Comm. cost</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Uniform</td>
<td>$W/p$</td>
<td>$W/p * 24$ bytes</td>
<td>$1 : 24$</td>
<td>Very poor</td>
</tr>
<tr class="even">
<td>Greedy</td>
<td>Straightforward: $dW/p$</td>
<td>$W/p * 24$ bytes</td>
<td>$d : 24$</td>
<td>Poor</td>
</tr>
<tr class="odd">
<td>Greedy</td>
<td>Pre-visit: $W/p$</td>
<td>$W/p * 24$ bytes</td>
<td>$1 : 24$</td>
<td>Very poor</td>
</tr>
<tr class="even">
<td>Stochastic Greedy</td>
<td>Straightforward: $dW/p$</td>
<td>$W/p * 24$ bytes</td>
<td>$d : 24$</td>
<td>Poor</td>
</tr>
<tr class="odd">
<td>Stochastic Greedy</td>
<td>Pre-visit: $log(d)W/p$</td>
<td>$W/p * 24$ bytes</td>
<td>$log(d) : 24$</td>
<td>Very poor</td>
</tr>
</tbody>
</table>
<p>If the selection of a neighbor is weighted-random, instead of uniformly-random, it will increase the computation workload to Wd /p, where d is the average degree of vertices in the graph. As a result, the computation-to-communication ratio will increase to d:24; for most graphs, this is still not high enough to have good scalability.</p>
<h3 id="geolocation">Geolocation</h3>
<p>In each iteration, Geolocation updates a vertex's location based on its neighbors. For multiple GPUs, neighboring vertices's location information needs to be available, either by direct access, UVM, or explicit data movement. The following shows how explicit data movement can be implemented.</p>
<pre><code>Do
    Local geo location updates on local vertices;
    Broadcast local vertices&#39; updates;
While no more update</code></pre>
<p>The computation cost is on the order of O(|E|/p), if in each iteration all vertices are looking for possible location updates from neighbors. Because the spatial median function has a lot of mathematical computation inside, particularly a haversine() for each edge, the constant factor hidden by O() is large; for simplicity, 100 is used as the constant factor here. Assuming that we broadcast every vertex's location gives the upper bound of communication, but in reality, the communication should be much less, because 1) not every vertex updates its location every iteration and 2) vertices may not have neighbors on each GPU, so instead of broadcast, p2p communication may be used to reduce the communication cost, especially when the graph connectivity is low.</p>
<table>
<thead>
<tr class="header">
<th>Comm. method</th>
<th>Comp. cost</th>
<th>Comm. cost</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Explicit movement</td>
<td>$100E/p$</td>
<td>$2V * 8$ bytes</td>
<td>$25E/p : 4V$</td>
<td>Okay</td>
</tr>
<tr class="even">
<td>UVM or peer access</td>
<td>$100E/p$</td>
<td>$E/p * 8$ bytes</td>
<td>$25 : 1$</td>
<td>Good</td>
</tr>
</tbody>
</table>
<h3 id="vertex-nomination">Vertex Nomination</h3>
<p>Vertex nomination is very similar to a single source shortest path (SSSP) problem, except it starts from a group of vertices, instead of a single source. One possible multi-GPU implementation is:</p>
<pre><code>Set the starting vertex / vertices;
While has new distance updates
    For each local vertex v with distance update:
        For each edge &lt;v, u, w&gt; of vertex v:
            new_distance := distance[v] + w;
            if (distance[u] &gt; new_distance)
                distance[u] = new_distance;

    For each u with distance update:
        Send &lt;u, distance[u]&gt; to host_GPU(u);</code></pre>
<p>Assuming on average, each vertex has its distance updated <code>a</code> times, and the average degree of vertices is <code>d</code>, the computation and the communication costs are:</p>
<table style="width:100%;">
<colgroup>
<col width="22%" />
<col width="12%" />
<col width="29%" />
<col width="21%" />
<col width="13%" />
</colgroup>
<thead>
<tr class="header">
<th>Parts</th>
<th>Comp. cost</th>
<th>Comm. cost</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Vertex nomination</td>
<td>$aE/p$</td>
<td>$aV/p * min(d, p) * 8$ bytes</td>
<td>$E : 8V * min(d, p)$</td>
<td>Okay</td>
</tr>
</tbody>
</table>
<p>The min(d, p) part in the communication cost comes from update aggregation on each GPU: when a vertex has more than one distance update, only the smallest is sent out; a vertex that has a lot of neighbors and is connected to all GPUs has its communication cost capped by p x 8 bytes.</p>
<h3 id="scan-statistics">Scan Statistics</h3>
<p>Scan statistics is essentially triangle counting (TC) for each vertex plus a simple post-processing step. The current Gunrock TC implementation is intersection-based: for an edge <code>&lt;v, u&gt;</code>, intersecting <code>neighbors[u]</code> and <code>neighbors[v]</code> gives the number of triangles including <code>edge &lt;v, u&gt;</code>. This neighborhood-intersection-based algorithm only works if the neighborhood of end points of all edges for which we need to count triangles can reside in the memory of a single GPU. For graphs with low connectivities, such as road networks and meshes, it is still possible to partition the graph; for graphs with high connectivity, such as social networks or some web graphs, it's almost impossible to partition the graph, and any sizable partition of the graph may touch a large portion of vertices of the graph. As a result, for general graphs, the intersection-based algorithm requires the graph can be duplicated on each GPU. Under this condition, the multi-GPU implementation is trivial: only count triangles for a subset of edges on each GPU, and no communication is involved.</p>
<p>A more distributed-friendly TC algorithm is wedge-checking-based (<a href="https://e-reports-ext.llnl.gov/pdf/890544.pdf" class="uri">https://e-reports-ext.llnl.gov/pdf/890544.pdf</a>). The main idea is this: for each triangle A-B-C, where <code>degree(A) &gt;= degree(B) &gt;= degree(C)</code>, both A and B are in C's neighborhood, and A is in B's neighborhood; when testing for possible triangle D-E-F, with <code>degree(D) &gt;= degree(E) &gt;= degree(F)</code>, the wedge (two edges that share the same end point) that needs to be checked is D-E, and the checking can be simply done by verifying whether D is in E's neighborhood. As this algorithm is designed for distributed systems, it should be well-suited for multi-GPU system. The ordering requirements are imposed to reduce the number of wedge checks and to balance the workload. The multi-GPU pseudo code is:</p>
<pre><code>For each local edge &lt; v, u &gt;:
    If (degree(v) &gt; degree(u)) continue;
    For each neighbor w of v:
        If (degree(v) &gt; degree(w)) continue;
        If (degree(u) &gt; degree(w)) continue;
        Send tuple &lt;u, w, v&gt; to host_GPU(u) for checking;

For each received tuple &lt; u, w, v &gt;:
    If (w in u&#39;s neighbor list):
        triangles[u] ++;
        triangles[w] ++;
        triangles[v] ++;

AllReduce(triangles, sum);

// For Scan statistics only
For each vertex v in the graph:
    scan_stat[v] := triangles[v] + degree(v);
    if (scan_stat[v] &gt; max_scan_stat):
        max_scan_stat := scan_stat[v];
        max_ss_node := v;</code></pre>
<p>Using T as the number of triangles in the graph, the number of wedge checks is normally a few times <code>T</code>, noted as <code>aT</code>. For the three graphs tested by the LLNL paper---Twitter, WDC 2012, and Rmat-Scale 34---<code>a</code> ranges from 1.5 to 5. The large number of wedges can use up the GPU memory, if they are stored and communicated all at once. The solution is to generate a batch of wedges and check them, then generate another batch and check them, loop until all wedges are checked.</p>
<p>Assuming the neighbor lists of every vertex are sorted, the membership checking can be done in log(#neighbors). As a result, using <code>d</code> as the average outdegree of vertices, the cost analysis is:</p>
<table style="width:100%;">
<colgroup>
<col width="26%" />
<col width="14%" />
<col width="17%" />
<col width="25%" />
<col width="15%" />
</colgroup>
<thead>
<tr class="header">
<th>Parts</th>
<th>Comp. cost</th>
<th>Comm. cost (B)</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Wedge generation</td>
<td>$dE/p$</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>Wedge communication</td>
<td>$0$</td>
<td>$aE/p * 12$</td>
<td></td>
<td></td>
</tr>
<tr class="odd">
<td>Wedge checking</td>
<td>$aE/p * log(d)$</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>AllReduce</td>
<td>$2V$</td>
<td>$2V * 4$</td>
<td></td>
<td></td>
</tr>
<tr class="odd">
<td>Triangle Counting</td>
<td>$(d * a * log(d))E/p + 2V$</td>
<td>$aE/p * 12 + 8V$</td>
<td>$~(d + a * log(d)) : 12a$</td>
<td>Okay</td>
</tr>
<tr class="even">
<td>Scan Statistics</td>
<td>$(d * a * log(d))E/p$</td>
<td>$12aE/p + 8V$</td>
<td>$~(d + a * log(d)) : 12a$</td>
<td>Okay</td>
</tr>
<tr class="odd">
<td>(with wedge checks)</td>
<td>$+ 2V + V/p$</td>
<td></td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>Scan Statistics</td>
<td>$Vdd + V/p$</td>
<td>$8V$</td>
<td>$dd : 8$</td>
<td>Perfect</td>
</tr>
<tr class="odd">
<td>(with intersection)</td>
<td></td>
<td></td>
<td></td>
<td></td>
</tr>
</tbody>
</table>
<h3 id="sparse-fused-lasso-gtf">Sparse Fused Lasso (GTF)</h3>
<p>The sparse fused lasso iteration is mainly a max-flow (MF), plus some per-vertex calculation to update the capacities in the graph. The reference and most non-parallel implementations of MF are augmenting-path-based; but finding the argumenting path and subsequent residual updates are both serial. The push-relabel algorithm is more parallelizable, and used by Gunrock's MF implementation. Each time the push operation updates the flow on an edge, it also needs to update the flow on the reverse edge; but the reverse edge may be hosted by another GPU, and that creates a large amount of inter-GPU traffic. The pseudocode for one iteration of MF with inter-GPU communication is:</p>
<pre><code>// Push phase
For each local vertex v:
    If (excess[v] &lt;= 0) continue;
    If (v == source || v == sink) continue;
    For each edge e&lt;v, u&gt; of v:
        If (capacity[e] &lt;= flow[e]) continue;
        If (height[v] &lt;= height[u]) continue;
        move := min(capacity[e] - flow[e], excess[v]);
        excess[v] -= move;
        flow[e] += move;
        Send &lt;reverse[e], move&gt; to host_GPU(u);
        If (excess[v] &lt;= 0)
            break for each e loop;

For each received &lt;e, move&gt; pair:
    flow[e] -= move;
    excess[Dest(e)] += move;

// Relabel phase
For each local vertex v:
    If (excess[v] &lt;= 0) continue;
    min_height := infinity;
    For each e&lt;v, u&gt; of v:
        If (capacity[e] &lt;= flow[e]) continue;
        If (min_height &gt; height[u])
            min_height = height[u];
    If (height[v] &lt;= min_height)
        height[v] := min_height + 1;

Broadcast height[v] for all local vertex;</code></pre>
<p>The cost analysis will not be on one single iteration, but on a full run of the push-relabel algorithm, as the bounds of the push and the relabel operations are known.</p>
<table>
<colgroup>
<col width="10%" />
<col width="17%" />
<col width="21%" />
<col width="31%" />
<col width="18%" />
</colgroup>
<thead>
<tr class="header">
<th>Parts</th>
<th>Comp. cost</th>
<th>Comm. cost (Bytes)</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Push</td>
<td>$a(V + 1)VE/p$</td>
<td>$(V+1)VE/p * 8$</td>
<td>$a:8$</td>
<td>Less than okay</td>
</tr>
<tr class="even">
<td>Relabel</td>
<td>$VE/p$</td>
<td>$V^2 * 8$</td>
<td>$d/p : 8$</td>
<td>Okay</td>
</tr>
<tr class="odd">
<td>MF (Push-Relabel)</td>
<td>$(aV + a + 1)VE/p$</td>
<td>$V^2((V+1)d/p + 1) * 8$</td>
<td>$~ a:8$</td>
<td>Less than okay</td>
</tr>
</tbody>
</table>
<p>The GTF-specific parts are more complicated than MF in terms of communication: the implementation must keep some data, such as weights and sizes, for each community of vertices, and multiple GPUs could be updating such data simultaneously. It's almost impossible to do explicit data movement for this part, and the best option is to use direct access or UVM; each vertex may update its community once, so the communication cost is still manageable. One iteration of GTF is:</p>
<pre><code>MF;
BFS to find the min-cut;
Vertex-Community updates;
Updates source-vertex and vertex-destination capacities;</code></pre>
<p>with scaling characteristics:</p>
<table>
<colgroup>
<col width="10%" />
<col width="17%" />
<col width="21%" />
<col width="31%" />
<col width="18%" />
</colgroup>
<thead>
<tr class="header">
<th>Parts</th>
<th>Comp. cost</th>
<th>Comm. cost (Bytes)</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>MF (Push-Relabel)</td>
<td>$(aV + a + 1)VE/p$</td>
<td>$V^2((V+1)d/p + 1) * 8$</td>
<td>$~ a:8$</td>
<td>Less than okay</td>
</tr>
<tr class="even">
<td>BFS</td>
<td>$E/p$</td>
<td>$2V * 4$</td>
<td>$d/p : 8$</td>
<td>Okay</td>
</tr>
<tr class="odd">
<td>V-C updates</td>
<td>$E/p$</td>
<td>$V/p * 8$</td>
<td>$d : 8$</td>
<td>Okay</td>
</tr>
<tr class="even">
<td>Capacity updates</td>
<td>$V/p$</td>
<td>$V/p * 4$</td>
<td>$1 : 4$</td>
<td>Less than okay</td>
</tr>
<tr class="odd">
<td>GTF</td>
<td>$(aV + a + 1)VE/p$</td>
<td>$V^2((V+1)d/p + 1) * 8$</td>
<td>$~ a:8$</td>
<td>Less than okay</td>
</tr>
<tr class="even">
<td></td>
<td>$+ 2E/p + V/p$</td>
<td>$+ 2V x 4 + V/p * 4$</td>
<td></td>
<td></td>
</tr>
</tbody>
</table>
<p>It's unsurprising that GTF may not scale: the compute- and communicate-heavy part of GTF is the MF, and in MF, each push needs communication to update its reverse edge. A more distributed-friendly MF algorithm is needed to overcome this problem.</p>
<h3 id="graph-projection">Graph Projection</h3>
<p>Graph projection is very similar to triangle counting by wedge checking; but instead of counting the triangles, it actually records the wedges. The problem here is not computation or communication, but rather the memory requirement of the result: projecting all vertices may create a very dense graph, which may be much larger than the original graph. One possible solution is to process the results in batches:</p>
<pre><code>vertex_start := 0;
While (vertex_start &lt; num_vertices)
    markers := {0};
    current_range := [vertex_start, vertex_start + batch_size);
    For each local edge e&lt;v, u&gt; with u in current_range:
        For each neighbor t of v:
            If (u == t) continue;
            markers[(u - vertex_start) * ceil(num_vertices / 32) + t / 32] |=
                1 &lt;&lt; (t % 32);

    For each vertex u in current_range:
        Form the neighbor list of u in the new graph by markers;

    For each local edge e&lt;v, u&gt; with u in current_range:
        For each neighbor t of v:
            If (u == t) continue;
            e&#39; := edge_id of &lt;u, t&gt; in the new graph,
                by searching u&#39;s neighbor list;
            edge_values[e&#39;] += 1;

    For each edge e&#39;&lt;u, t, w&gt; in the new graph:
        send &lt;u, t, w&gt; to host_GPU(u);

    Merge all received &lt;u, t, w&gt; to form projection
        for local vertices u in current_range;
    Move the result from GPU to CPU;

    vertex_start += batch_size;</code></pre>
<p>Using <code>E'</code> to denote the number of edges in the projected graph, and <code>d</code> to denote the average degree of vertices, the costs are:</p>
<table>
<thead>
<tr class="header">
<th>Parts</th>
<th>Comp. cost</th>
<th>Comm. cost</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Marking</td>
<td>$dE/p$</td>
<td>$0$ byte</td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>Forming edge lists</td>
<td>$E'$</td>
<td>$0$ byte</td>
<td></td>
<td></td>
</tr>
<tr class="odd">
<td>Counting</td>
<td>$dE/p$</td>
<td>$0$ byte</td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>Merging</td>
<td>$E'$</td>
<td>$E' * 12$ bytes</td>
<td></td>
<td></td>
</tr>
<tr class="odd">
<td>Graph Projection</td>
<td>$2dE/p + 2E'$</td>
<td>$12E'$ bytes</td>
<td>$dE/p + E' : 6E'$</td>
<td>Okay</td>
</tr>
</tbody>
</table>
<p>If the graph can be duplicated on each GPU, instead of processing distributed edges, each GPU can process only <code>u</code> vertices that are hosted on that GPU. This eliminates the merging step; as a result, there is no communication needed, and the computation cost reduces to 2dE/p + E'.</p>
<h3 id="local-graph-clustering">Local Graph Clustering</h3>
<p>The Gunrock implementation of Local Graph Clustering (LGC) uses PageRank-Nibble, a variant of the PageRank algorithm. PR-Nibble's communication pattern is the same as standard PR: accumulate changes for each vertex to its host GPU. As a result, PR-Nibble should be scalable, just as standard PR. PR-Nibble with communication can be done as:</p>
<pre><code>// Per-vertex updates
For each active local vertex v:
    If (iteration == 0 &amp;&amp; v == src\_neighbor) continue;
    If (iteration &gt; 0 &amp;&amp; v == src)
        gradient[v] -= alpha / #reference_vertices / sqrt(degree(v));
    z[v] := y[v] - gradient[v];
    If (z[v] == 0) continue;

    q_old := q[v];
    threshold := rho * alpha * sqrt(degree(v));
    If (z[v] &gt;= threshold)
        q[v] := z[v] - threshold;
    Else if (z[v] &lt;= -threshold)
        q[v] := z[v] + threshold;
    Else
        q[v] := 0;

    If (iteration == 0)
        y[v] := q[v];
    Else
        y[v] := q[v] + (1 - sqrt(alpha)) / (1 + sqrt(alpha)) * (q[v] - old_q);

    gradient[v] := y[v] * (1 + alpha) / 2;

// Ranking propagation
For each edge e&lt;v, u&gt; of active local vertex v:
    change := y[v] * (1 - alpha) / 2 / sqrt(degree(v)) / sqrt(degree(u));
    gradient_update[u] -= change;

For each u that has gradient updates:
    send &lt; u, gradient_update[u]&gt; to host_GPU(u);

For each received gradient update &lt; u, gradient_update&gt;:
    gradient[u] += gradient_update;

// Gradient updates
For each local vertex u with gradient updated:
    If (gradient[u] == 0) continue;
    Set u as active for next iteration;

    val := gradient[u];
    If (u == src)
        val -= (alpha / #reference_vertices) / sqrt(degree(u));
    val := abs(val / sqrt(degree(u)));
    if (gradient_scale_value &lt; val)
        gradient_scale_value = val;
    if (val &gt; gradient_threshold)
        gradient_scale := 1;</code></pre>
<p>The cost analysis is:</p>
<table>
<thead>
<tr class="header">
<th>Parts</th>
<th>Comp. cost</th>
<th>Comm. cost</th>
<th>Comp/comm ratio</th>
<th>Scalability</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Per-vertex updates</td>
<td>$~10 V/p$</td>
<td>$0$ bytes</td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>Ranking propagation</td>
<td>$2E/p$</td>
<td>$V * 8$ bytes</td>
<td>$d/p : 4$</td>
<td></td>
</tr>
<tr class="odd">
<td>Gradient updates</td>
<td>$V/p$</td>
<td>$0$ bytes</td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td>Local graph clustering</td>
<td>$(12V + 2E)/p$</td>
<td>$8V$ bytes</td>
<td>$(6 + d)/p : 4$</td>
<td>good</td>
</tr>
</tbody>
</table>
<h3 id="seeded-graph-matching-and-application-classification">Seeded Graph Matching and Application Classification</h3>
<p>The implementations of these two applications are linear-algebra-based, as opposed to other applications where we used Gunrock and its native graph (vertex-edge) data structures. The linear-algebra-based (BLAS-based) formulations, especially the ones that require matrix-matrix multiplications, may impose a large communication requirement. Advance matrix-matrix and vector-matrix multiplication kernels use optimizations that build on top of a specific layout of the data, which may be not distribution-friendly. A different method of analyzing the computation and the communication costs---the computation vs. communication ratio---is needed for these applications.</p>
<h2 id="summary-of-results">Summary of Results</h2>
<table>
<colgroup>
<col width="26%" />
<col width="38%" />
<col width="13%" />
<col width="21%" />
</colgroup>
<thead>
<tr class="header">
<th>Application</th>
<th>Computation to communication ratio</th>
<th>Scalability</th>
<th>Implementation difficulty</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><p>Louvain</p></td>
<td><p>$E/p : 2V$</p></td>
<td><p>Okay</p></td>
<td><p>Hard</p></td>
</tr>
<tr class="even">
<td><p>Graph SAGE</p></td>
<td><p>$CF : (C, 2p) 4$</p></td>
<td><p>Good</p></td>
<td><p>Easy</p></td>
</tr>
<tr class="odd">
<td><p>Random walk</p></td>
<td><p>Duplicated graph: infinity<br />
Distributed graph: 1 : 24</p></td>
<td><p>Perfect<br />
Very poor</p></td>
<td><p>Trivial<br />
Easy</p></td>
</tr>
<tr class="even">
<td><p>Graph search: Uniform</p></td>
<td><p>1 : 24</p></td>
<td><p>Very poor</p></td>
<td><p>Easy</p></td>
</tr>
<tr class="odd">
<td><p>Graph search: Greedy</p></td>
<td><p>Straightforward: d : 24<br />
Pre-visit: 1:24</p></td>
<td><p>Poor<br />
Very poor</p></td>
<td><p>Easy<br />
Easy</p></td>
</tr>
<tr class="even">
<td><p>Graph search: Stochastic greedy</p></td>
<td><p>Straightforward: d : 24<br />
Pre-visit: $(d) : 24$</p></td>
<td><p>Poor<br />
Very poor</p></td>
<td><p>Easy<br />
Easy</p></td>
</tr>
<tr class="odd">
<td><p>Geolocation</p></td>
<td><p>Explicit movement: $25E/p : 4V$<br />
UVM or peer access: 25 : 1</p></td>
<td><p>Okay<br />
Good</p></td>
<td><p>Easy<br />
Easy</p></td>
</tr>
<tr class="even">
<td><p>Vertex nomination</p></td>
<td><p>$E : 8V (d, p)$</p></td>
<td><p>Okay</p></td>
<td><p>Easy</p></td>
</tr>
<tr class="odd">
<td><p>Scan statistics</p></td>
<td><p>Duplicated graph: infinity<br />
Distributed graph: $(d+a (d)):12$</p></td>
<td><p>Perfect<br />
Okay</p></td>
<td><p>Trivial<br />
Easy</p></td>
</tr>
<tr class="even">
<td><p>Sparse fused lasso</p></td>
<td><p>$a:8$</p></td>
<td><p>Less than okay</p></td>
<td><p>Hard</p></td>
</tr>
<tr class="odd">
<td><p>Graph projection</p></td>
<td><p>Duplicated graph : infinity<br />
Distributed graph : $dE/p + E' : 6E'$</p></td>
<td><p>Perfect<br />
Okay</p></td>
<td><p>Easy<br />
Easy</p></td>
</tr>
<tr class="even">
<td><p>Local graph clustering</p></td>
<td><p>$(6 + d)/p : 4$</p></td>
<td><p>Good</p></td>
<td><p>Easy</p></td>
</tr>
<tr class="odd">
<td><p>Seeded graph matching</p></td>
<td></td>
<td></td>
<td></td>
</tr>
<tr class="even">
<td><p>Application classification</p></td>
<td></td>
<td></td>
<td></td>
</tr>
</tbody>
</table>
<p>Seeded graph matching and application classification are matrix-operation-based and not covered in this table.</p>
<p>From the scaling analysis, we can see these workflows can be roughly grouped into three categories, by their scalabilities:</p>
<p><em>Good scalability</em> GraphSAGE, geolocation using UVM or peer accesses, and local graph clustering belong to this group. They share some algorithmic signatures: the whole graph needs to be visited at least once in every iteration, and visiting each edge involves nontrivial computation. The communication costs are roughly at the level of V. As a result, the computation vs. communication ratio is larger than E : V. PageRank is a standard graph algorithm that falls in this group.</p>
<p><em>Moderate scalability</em> This group includes Louvain, geolocation using explicit movement, vertex nomination, scan statistics, and graph projection. They either only visit part of the graph in an iteration, have only trivial computation during an edge visit, or communicate a little more data than V. The computation vs. communication is less than E : V, but still larger than 1 (or 1 operation : 4 bytes). They are still scalable on the DGX-1 system, but not as well as the previous group. Single source shortest path (SSSP) is an typical example for this group.</p>
<p><em>Poor scalability</em> Random walk, graph search, and sparse fused lasso belong to this group. They need to send out some data for each vertex or edge visit. As a result, the computation vs communication ratio is less than 1 (or 1 operation : 4 bytes). They are very hard to scale across multiple GPUs. Random walk is an typical example.</p>
<h6 id="end-of-report">End of report</h6>
