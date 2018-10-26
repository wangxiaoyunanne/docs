---
title: HIVE Year 1 Report&colon; Executive Summary

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

# Executive Summary

This report is located online at the following URL: <https://gunrock.github.io/docs/hive_year1_summary.html>.

Herein UC Davis produces the following three deliverables that it promised to deliver in Year 1:

1. **7--9 kernels running on a single GPU on DGX-1**. The PM had indicated that the application targets are the graph-specific kernels of larger applications, and that our effort should target these kernels. These kernels run on one GPU of the DGX-1. These kernels are in Gunrock's GitHub repository as standalone kernels. While we committed to delivering 7--9 kernels, we deliver all 11 v0 kernels.
2. **(High-level) performance analysis of these kernels**. In this report we analyze the performance of these kernels.
3. **Separable communication benchmark predicting latency and throughput for a multi-GPU implementation**. This report (and associated code, also in the Gunrock GitHub repository) analyzes the DGX-1's communication capabilities and projects how single-GPU benchmarks will scale on this machine to 8 GPUs.

Specific notes on applications and scaling follow:


**[Geolocation](hive_geolocation.html.md)** One or two sentences that summarize "if you had one or two sentences to sum up your whole effort, what would you say". I will copy this directly to the high-level executive summary in the first page of the report. Talk to JDO about this. Write it last, probably.

**[Community Detection (Louvain)](hive_louvain.html.md)** One or two sentences that summarize "if you had one or two sentences to sum up
your whole effort, what would you say". I will copy this directly to the high-level
executive summary in the first page of the report. Talk to JDO about this.
Write it last, probably.

