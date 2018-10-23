---
title: Scaling analysis for Hive applications

toc_footers:
  - <a href='https://github.com/gunrock/gunrock'>Gunrock&colon; GPU Graph Analytics</a>
  - Gunrock &copy; 2018 The Regents of the University of California.

search: true

full_length: true
---

The purpose of this document is to understand how the Hive applications would
scale out on multiple GPUs, with the focus on tarting the DGX-1 platform.
Before diving into per application analysis, a brief summary of the potential
hardware platforms, the communication methods and models, and graph
partitioning schemes will be given.

# Hardware platforms

There are at least three kinds of potential multi-GPU platforms the Hive apps
can run on. They have different GPU-communication properties, and that may
affect the choice of communication models and / or graph partitioning schemes,
thus may have different scaling results.

## DGX-1

## DGX-2

## GPU clusters

# Communication methods / models

## Explicit data movement

### Peers to host GPU

### Host GPU to peers

### All reduce

### Mix all reduce with peers to host GPU or host GPU to peers

# Graph partitioning scheme

## 1D partitioning

## 2D partitioning

## High / low degree partitioning

# Scaling of the Hive applications

## How scalings are considered

## Louvain

### Graph and data partitioning

### Communication model

### Summary of the app

| Computation workload | Communication cost | Memory usage |
|----------------------|--------------------|--------------|

## Graph SAGE
