# Unit Testing & Code Coverage

```c
/*
 * @brief PageRank test for shared library advanced interface
 * @file test_lib_pr.h
 */

TEST(sharedlibrary, pagerank) {

  int num_nodes = 7, num_edges = 26;
  int row_offsets[8]  = {0, 3, 6, 11, 15, 19, 23, 26};
  int col_indices[26] = {1, 2, 3, 0, 2, 4, 0, 1, 3, 4, 5, 0, 2,
                         5, 6, 1, 2, 5, 6, 2, 3, 4, 6, 3, 4, 5};

  int 	*top_nodes = new int  [num_nodes];
  float	*top_ranks = new float[num_nodes];

  double elapsed =  pagerank(num_nodes, num_edges, row_offsets, 
		  	     col_indices, 1, top_nodes, top_ranks); 

  double nodes[7] = {2, 3, 4, 5, 0, 1, 6};
  double scores[7] = {0.186179, 0.152261, 0.152261, 0.151711,
    0.119455, 0.119455, 0.118680};

  for (int node = 0; node < num_nodes; ++node) {
    EXPECT_EQ(top_nodes[node], nodes[node])
      << "Node indices differ at node index " << node;
    EXPECT_NEAR(top_ranks[node], scores[node], 0.0000005)
      << "Scores differ at node index " << node;
  }

  delete[] top_nodes; top_nodes = NULL;
  delete[] top_ranks; top_ranks = NULL;

}
```

**Recommended Read:** [Introduction: Why Google C++ Testing Framework?](https://github.com/google/googletest/blob/master/googletest/docs/Primer.md)

When writing a good test, we would like to cover all possible functions (or execute all code lines),
what I will recommend to do is write a simple test, run code coverage on it, and
use codecov.io to determine what lines are not executed. This gives you a good
idea of what needs to be in the test and what you are missing.

**What is code coverage?**


> Code coverage is a measurement used to express which lines of code were executed by a test suite. We use three primary terms to describe each lines executed.
>
>  * hit indicates that the source code was executed by the test suite.
>  * partial indicates that the source code was not fully executed by the test suite; there are remaining branches that were not executed.
>  * miss indicates that the source code was not executed by the test suite.
>
> Coverage is the ratio of hits / (hit + partial + miss). A code base that has 5 lines executed by tests out of 12 total lines will receive a coverage ratio of 41% (rounding down).


Below is an example of what lines are a hit and a miss; you can target the lines missed in the tests to improve coverage.

![Example CodeCov Stats](https://i.imgur.com/5QwKjcB.png)

## Example Test Using GoogleTest

1. Create a `test_<test-name>.h` file and place it in the appropriate directory inside `/path/to/gunrock/unittests/`. I will be using `test_pr_lib.h` as an example.

2. In the `tests/test_unittests.cu` file, add your test file as an include: `#include "test_lib_pr.h"`.

3. In your `test_<test-name>.h` file, create a `TEST()` function, which takes two parameters: `TEST(<nameofthesuite>, <nameofthetest>)`.

4. Use `EXPECT` and `ASSERT` to write the actual test itself. I have provided a commented example below:

5. Now when you run the binary called `unit_test`, it will automatically run your test suite along with all other google tests as well.
This binary it automatically compiled when gunrock is built, and is found in `/path/to/builddir/bin/unit_test`.

**Final Remarks:**

* I highly recommend reading the Primer document mentioned at the start of this tutorial. It explains in detail how to write a unit test using google test. My tutorial has more been about how to incorporate it into Gunrock.
* Another interesting read is [Measuring Coverage at Google](https://testing.googleblog.com/2014/07/measuring-coverage-at-google.html).
