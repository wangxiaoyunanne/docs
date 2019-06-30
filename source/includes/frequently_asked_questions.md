# Frequently Asked Questions

Some of the most common questions we have come across during the life of Gunrock project. If your question isn't already answered below, feel free to create an [issue](https://github.com/gunrock/gunrock/issues) on GitHub.

## What does it do?

Gunrock is a fast and efficient graph processing library on the GPU that provides a set of graph algorithms used in big data analytics and visualization with high performance.  It also provides a set of operators which abstract the general operations in graph processing for other developers to build high-performance graph algorithm prototypes with minimum programming effort.

## How does it do it?

Gunrock takes advantage of the immense computational power available in commodity-level, off-the-shelf Graphics Processing Units (GPUs), originally designed to handle the parallel computational tasks in computer graphics, to perform graph traversal and computation in parallel on thousands of GPU's computing cores.

## Who should want this?

Gunrock is built with two kinds of users in mind: The first kind of users are programmers who build big graph analytics and visualization projects and need to use existing graph primitives provided by Gunrock.  The second kind of users are programmers who want to use Gunrock's high-level, programmable abstraction to express, develop, and refine their own (and often more complicated) graph primitives.

## When would Gunrock be a bad choice?

If your graph is too *small*, it's a bad fit for Gunrock (and the GPU). For most workloads, a GPU isn't a good fit until the graph reaches at least a few thousand nodes. Conversely, if your graph is too *large* and doesn't fit into GPU memory (or, for single-node multi-GPU configurations, into the aggregate GPU memories of all GPUs on the node), it's also a bad fit for Gunrock. Finally, Gunrock also does not currently support multi-node (distributed) execution, although Gunrock would probably be a good single-node component of a future distributed graph framework. Both the out-of-core (scale-up) and multi-node (scale-out) problems are excellent research programs.

## What is the skill set users need to use it?

For the first kind of users, C/C++ background is sufficient. We are also building Gunrock as a shared library with C interfaces that can be loaded by other languages such as Python and Julia.  For the second kind of users, they need to have the C/C++ background and also an understanding of parallel programming, especially BSP (Bulk-Synchronous Programming) model used by Gunrock.

## What platforms/languages do people need to know in order to modify or integrate it with other tools?

Using the exposed interface, the users do not need to know CUDA to modify or integrate Gunrock to their own tools. However, an essential understanding of parallel programming and BSP model is necessary if one wants to add/modify graph primitives in Gunrock.

## Why would someone want this?

The study of social networks, webgraphs, biological networks, and unstructured meshes in scientific simulation has raised a significant demand for efficient parallel frameworks for processing and analytics on large-scale graphs. Initial research efforts in using GPUs for graph processing and analytics are promising.

## How is it better than the current state of the art?

Gunrock delivers best-in-class performance at a low cost with a high-level, productive, flexible programming model that enables writing a [large number of graph applications](#gunrock-39-s-application-cases). GPUs are becoming ubiquitous not just on the desktop but also in the cloud; Gunrock is competitive with much larger and more expensive distributed graph frameworks at a much lower cost. It generally outperforms the best CPU frameworks across its application suite, and among GPU frameworks, enables both high performance and high productivity.

## How would someone get it?

Gunrock is an open-source library. The code, documentation, and quick start guide are all on its [GitHub page](gunrock.github.io).

## Is a user account required?

No. One can use either git clone or download directly to get the source code and documentation of Gunrock.

## Are all of its components/dependencies easy to find?

Gunrock has two dependencies. Both of them are GPU primitive libraries which also reside on GitHub. All dependencies do not require installation. To use, one only needs to download or git clone them and put them in the according directories. More details in the installation section of this documentation.

## How would someone install it?

For a C/C++ programmer, integrating Gunrock into your projects is easy. Since it is a template based library, just add the include files in your code. The simple example and all the testrigs will provide detailed information on how to do this.

For programmers who use Python, Julia, or other language and want to call Gunrock APIs, we are building a shared library with binary compatible C interfaces. It will be included in the soon-to-arrive next release of Gunrock.

## Can anyone install it? Do they need IT help?

Gunrock is targeted at developers who are familiar with basic software engineering. For non-technical people, IT help might be needed.

## Does this process actually work? All the time? On all systems specified?

Currently, Gunrock has been tested on two Linux distributions: Linux Mint and Ubuntu. But we expect it to run correctly on other Linux distributions too. We expect a Mac build would work (it has in the past), but don't currently have a Mac+NVIDIA machine on which we can test. Windows is not currently supported (we welcome pull requests that would allow us to support Windows).

## How would someone test that it's working with provided sample data?

Testrigs are provided as well as a small simple example for users to test the correctness and performance of every graph primitive.

## Is the "using" of sample data clear?

On Linux, one only needs to go to the dataset directory and run "make"; the script will automatically download all the needed datasets. One can also choose to download a single dataset in its separate directory.

## How would someone use it with their own data?

Gunrock supports Matrix Market (.mtx) file format; users need to pre-process the graph data into this format before running Gunrock.
