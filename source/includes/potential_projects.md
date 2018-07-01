# Possible Gunrock projects

Possible projects are in two categories: infrastructure projects that make Gunrock better but have minimal research value, and research projects that are longer-term and hopefully have research implications of use to the community.

For any discussion on these, please use the existing Github issue (or make one).

## Infrastructure projects

- Containerize Gunrock (a Docker container) [[issue](https://github.com/gunrock/gunrock/issues/349)]
- Support a Windows build [[issue](https://github.com/gunrock/gunrock/issues/213)]

## Research projects

- Better defaults and/or decision procedures for setting Gunrock parameters (possibly a machine-learning approach for this)
- How can we preprocess Gunrock input to increase performance? This could be either reordering CSR for better performance (e.g., reverse Cuthill-McKee) or a new format.
- If we had a larger number of X in the hardware&mdash;e.g., more registers, more SMs, more threads/SM, more shared memory, bigger cache---how would it help performance? (Where would we want NVIDIA to spend more transistors to best help our performance?)
